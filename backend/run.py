# -*- coding: utf-8 -*-
"""
巡检助手 WEBUI - 启动入口
启动 FastAPI 服务并自动打开浏览器
"""
import os
import sys
import threading
import time
import webbrowser
import uvicorn


def get_resource_path(relative_path):
    """获取资源文件路径（兼容 PyInstaller 打包后的单文件模式）

    Args:
        relative_path: 相对路径

    Returns:
        绝对路径
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后运行时，临时解压目录
        base_path = sys._MEIPASS
    else:
        # 正常运行时，当前脚本所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def open_browser(host, port):
    """延迟打开浏览器"""
    time.sleep(1.5)
    url = f"http://{host}:{port}"
    try:
        webbrowser.open(url)
        print(f"[启动] 已自动打开浏览器: {url}")
    except Exception as e:
        print(f"[启动] 自动打开浏览器失败: {e}")
        print(f"[启动] 请手动访问: {url}")


def main():
    """主函数"""
    from app.config import settings
    from app.main import app

    print("=" * 50)
    print("  巡检助手 WEBUI")
    print(f"  版本: {settings.APP_VERSION}")
    print("=" * 50)
    print(f"[启动] 服务地址: http://{settings.HOST}:{settings.PORT}")
    print(f"[启动] API文档: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 50)
    print()

    # 自动打开浏览器（可通过环境变量禁用，用于开发模式）
    auto_open = settings.AUTO_OPEN_BROWSER and os.environ.get("DISABLE_AUTO_OPEN") != "1"
    if auto_open:
        t = threading.Thread(target=open_browser, args=(settings.HOST, settings.PORT))
        t.daemon = True
        t.start()

    # 启动 uvicorn
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level="info"
    )


if __name__ == "__main__":
    main()
