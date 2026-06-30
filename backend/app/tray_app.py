# -*- coding: utf-8 -*-
"""
巡检助手 WEBUI - 系统托盘模块
用 pystray 在状态栏显示图标，不弹 CMD 窗口
"""
import os
import sys
import time
import atexit
import shutil
import threading
import logging
import io
from pathlib import Path

# 延迟导入，避免 pystray 未安装时整个模块无法加载
try:
    import pystray
    from PIL import Image, ImageDraw
    _PYSTRAY_AVAILABLE = True
except ImportError:
    _PYSTRAY_AVAILABLE = False

# ===== 日志管理 =====
# 使用统一的 get_data_dir() — EXE模式=exe所在目录, 开发模式=环境变量或项目根目录
from app.config import get_data_dir

log_dir = Path(get_data_dir()) / "log"
log_dir.mkdir(parents=True, exist_ok=True)
log_file = log_dir / "patrol.log"

# 日志格式
_log_format = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)

# 文件日志处理器
_file_handler = None


def setup_logging():
    """设置日志：同时输出到文件和控制台（控制台在打包后被重定向到日志缓冲区）"""
    global _file_handler
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # 文件处理器
    _file_handler = logging.FileHandler(log_file, encoding="utf-8")
    _file_handler.setFormatter(_log_format)
    root_logger.addHandler(_file_handler)

    # 控制台处理器（开发模式有 CMD，打包后 noconsole 输出到 StringIO）
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(_log_format)
    root_logger.addHandler(console_handler)

    # 捕获 uncaught 异常
    def _excepthook(exc_type, exc_value, exc_tb):
        logging.getLogger().critical(
            "未捕获的异常", exc_info=(exc_type, exc_value, exc_tb)
        )
    sys.excepthook = _excepthook

    return root_logger


# 日志内容缓冲区（供"查看日志"窗口使用）
class LogBuffer(io.StringIO):
    """可同时写入文件和内存缓冲区的日志流"""
    def __init__(self):
        super().__init__()
        self._file = None

    def set_file(self, path):
        self._file = path

    def write(self, msg):
        super().write(msg)
        if self._file:
            try:
                with open(self._file, 'a', encoding='utf-8') as f:
                    f.write(msg)
            except Exception:
                pass
        return len(msg)


# ===== 托盘图标生成 =====
def create_tray_icon():
    """生成简单的托盘图标（用 Pillow 画一个巡逻图标）

    仅在 _PYSTRAY_AVAILABLE 为 True 时调用
    """
    if not _PYSTRAY_AVAILABLE:
        return None
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 画一个圆形背景
    margin = 4
    draw.ellipse(
        [margin, margin, size - margin, size - margin],
        fill=(64, 158, 255, 255)
    )

    # 画一个对勾
    line_width = size // 8
    center_x, center_y = size // 2, size // 2
    # 对勾的两条线
    check_color = (255, 255, 255, 255)
    # 左下到中心上方
    draw.line([
        (center_x - size // 5, center_y + 2),
        (center_x - 2, center_y + size // 4),
    ], fill=check_color, width=line_width)
    # 中心上方到右下
    draw.line([
        (center_x - 2, center_y + size // 4),
        (center_x + size // 3, center_y - size // 5),
    ], fill=check_color, width=line_width)

    return img


# ===== 托盘菜单 =====
_tray_icon = None
_server_running = True
_logger = None


# ===== PyInstaller 临时文件清理 =====
def _cleanup_orphan_pyinstaller_temp():
    """
    清理之前非正常退出残留的 PyInstaller 临时文件。
    PyInstaller 单文件 exe 启动时解压到 %TEMP%/_MEIxxxxx/，
    正常退出时会自动清理；崩溃或被 kill 时则残留。
    """
    if not getattr(sys, 'frozen', False):
        return  # 非打包模式，跳过

    temp_root = Path(os.environ.get("TEMP", os.environ.get("TMP", ".")))
    current_meipass = Path(sys._MEIPASS).resolve() if hasattr(sys, '_MEIPASS') else None

    cleaned = 0
    freed_bytes = 0

    for entry in temp_root.iterdir():
        # 只匹配 PyInstaller 的 _MEI 开头的文件夹
        if not entry.is_dir():
            continue
        if not entry.name.startswith("_MEI"):
            continue

        # 跳过当前运行使用的目录（不能删自己）
        if current_meipass and entry.resolve() == current_meipass:
            continue

        # 尝试删除
        try:
            dir_size = sum(f.stat().st_size for f in entry.rglob("*") if f.is_file())
            shutil.rmtree(entry, ignore_errors=True)
            if not entry.exists():
                cleaned += 1
                freed_bytes += dir_size
        except Exception:
            pass

    if cleaned > 0 and _logger:
        _logger.info(f"清理 PyInstaller 残留临时文件: {cleaned} 个目录, 释放 {freed_bytes / 1024 / 1024:.1f} MB")


def _cleanup_on_exit():
    """退出时额外触发一次临时文件清理（兜底 PyInstaller bootloader 的 atexit）"""
    # 不操作 _MEIPASS 本身，bootloader 会处理
    # 这里确保日志刷新
    if _logger:
        for handler in _logger.handlers:
            handler.flush()
    _cleanup_orphan_pyinstaller_temp()


def _open_web(icon, item):
    """打开浏览器访问巡检助手"""
    import webbrowser
    from app.config import settings
    webbrowser.open(f"http://{settings.HOST}:{settings.PORT}")


def _view_logs(icon, item):
    """显示运行日志窗口 - 在新的CMD窗口实时tail日志"""
    import subprocess
    # 写临时批处理文件，避免复杂命令行的引号嵌套问题
    bat_path = log_dir / "_open_logs.bat"
    bat_content = (
        f'@echo off\r\n'
        f'chcp 65001 >nul 2>&1\r\n'
        f'title 巡检助手-运行日志\r\n'
        f'echo ====== 历史日志 ======\r\n'
        f'type "{log_file}"\r\n'
        f'echo.\r\n'
        f'echo ====== 实时日志 (Ctrl+C 停止) ======\r\n'
        f'powershell -NoProfile -Command "Get-Content \'{log_file}\' -Wait -Tail 10"\r\n'
    )
    try:
        bat_path.write_text(bat_content, encoding='utf-8')
        subprocess.Popen(['cmd', '/k', str(bat_path)], creationflags=subprocess.CREATE_NEW_CONSOLE)
    except Exception as e:
        _logger.warning(f"打开日志窗口失败: {e}")


def _quit_app(icon, item):
    """退出应用"""
    global _server_running
    _server_running = False
    _cleanup_on_exit()
    icon.stop()


def start_tray(app, host, port):
    """创建系统托盘（阻塞主线程）

    如果 pystray 不可用，回退到直接运行 uvicorn（有 CMD 窗口）
    """
    global _logger
    _logger = logging.getLogger()

    if not _PYSTRAY_AVAILABLE:
        # pystray 未安装 → 回退到直接运行 uvicorn
        _logger.warning("pystray 不可用，回退到直接运行模式（将显示 CMD 窗口）")
        print("[托盘] pystray 不可用，使用 CMD 模式运行")
        _fallback_run_server(app, host, port)
        return

    # 启动时清理之前非正常退出残留的临时文件
    _cleanup_orphan_pyinstaller_temp()

    # 注册退出时的兜底清理
    atexit.register(_cleanup_on_exit)

    # 设置托盘菜单
    menu = pystray.Menu(
        pystray.MenuItem("打开巡检助手", _open_web, default=True),
        pystray.MenuItem("查看运行日志", _view_logs),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("退出", _quit_app),
    )

    icon = pystray.Icon(
        "patrol_assistant",
        create_tray_icon(),
        "巡检助手 WEBUI",
        menu,
    )

    # 启动后端在后台线程
    server_thread = threading.Thread(
        target=_run_server, args=(app, host, port), daemon=True
    )
    server_thread.start()

    # 轮询等待服务器就绪后再打开浏览器
    def _delayed_open_browser():
        import webbrowser
        import urllib.request
        url = f"http://{host}:{port}"
        # 轮询 /api/health，最多等 30 秒
        for i in range(60):
            try:
                resp = urllib.request.urlopen(f"{url}/api/health", timeout=1)
                if resp.status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        try:
            webbrowser.open(url)
            _logger.info(f"自动打开浏览器: {url}")
        except Exception as e:
            _logger.warning(f"自动打开浏览器失败: {e}")
    t_browser = threading.Thread(target=_delayed_open_browser, daemon=True)
    t_browser.start()

    # 启动托盘（阻塞直到 stop）
    icon.run()


def _fallback_run_server(app, host, port):
    """回退模式：直接运行 uvicorn（当 pystray 不可用时）"""
    import uvicorn
    import webbrowser

    # 轮询等待服务器就绪后再打开浏览器
    def _open():
        import urllib.request
        url = f"http://{host}:{port}"
        for _ in range(60):
            try:
                resp = urllib.request.urlopen(f"{url}/api/health", timeout=1)
                if resp.status == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        try:
            webbrowser.open(url)
        except Exception:
            pass
    threading.Thread(target=_open, daemon=True).start()

    uvicorn.run(app, host=host, port=port, log_level="info")


def _run_server(app, host, port):
    """后台线程：启动 FastAPI 服务"""
    import uvicorn
    import asyncio

    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "file": {
                "class": "logging.FileHandler",
                "filename": str(log_file),
                "formatter": "default",
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "uvicorn": {"handlers": ["file"], "level": "INFO"},
            "uvicorn.error": {"handlers": ["file"], "level": "INFO"},
            "app": {"handlers": ["file"], "level": "INFO"},
        },
    }

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_config=log_config,
            log_level="info",
        )
    except Exception as e:
        logging.getLogger().error(f"服务启动失败: {e}")
