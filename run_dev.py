# -*- coding: utf-8 -*-
"""
巡检助手 WEBUI - 开发模式启动
同时启动后端服务 + 前端开发服务器

用法：python run_dev.py
"""
import os
import sys
import subprocess
import signal
import time

# 获取脚本所在目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(SCRIPT_DIR, "backend")
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")
CONDA_ENV = "py3710"

# 子进程列表
child_processes = []


def get_python():
    """获取当前 Python 解释器路径"""
    return sys.executable


def kill_all_children():
    """终止所有子进程"""
    global child_processes
    for proc in child_processes:
        if proc and proc.poll() is None:
            try:
                # Windows 下用 taskkill 强制终止进程树
                if sys.platform == 'win32':
                    subprocess.run(
                        ['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                        capture_output=True, timeout=5
                    )
                else:
                    proc.terminate()
                    proc.wait(timeout=5)
            except Exception:
                pass
    child_processes = []


def signal_handler(signum, frame):
    """信号处理函数"""
    print("\n\n👋 正在停止所有服务...")
    kill_all_children()
    sys.exit(0)


def ensure_conda_env():
    """检查并确保在正确的 conda 环境中"""
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")

    if current_env == CONDA_ENV:
        return True

    print(f"⚠️  当前环境: {current_env or '无'}，需要: {CONDA_ENV}")
    print(f"   请先执行: conda activate {CONDA_ENV}")
    print(f"   然后再运行: python {os.path.basename(__file__)}")
    return False


def check_backend_deps():
    """检查并安装后端依赖"""
    python = get_python()
    req_file = os.path.join(SCRIPT_DIR, "requirements.txt")

    if not os.path.exists(req_file):
        print("  ⚠ 未找到 requirements.txt，跳过依赖检查")
        return True

    # 直接 pip install（幂等，已装的秒过，缺的自动装）
    print("  → 检查后端依赖...")
    result = subprocess.run(
        [python, "-m", "pip", "install", "-r", req_file],
        shell=True
    )
    if result.returncode != 0:
        print("  ❌ 后端依赖安装失败")
        return False
    print("  ✓ 后端依赖就绪")

    return True


def start_backend():
    """启动后端 FastAPI 服务"""
    print("\n" + "=" * 50)
    print("  [后端] 启动 FastAPI 服务...")
    print("=" * 50)

    python = get_python()
    backend_script = os.path.join(BACKEND_DIR, "run.py")
    print(f"   后端地址: http://127.0.0.1:8000")
    print(f"   API文档:  http://127.0.0.1:8000/docs")
    print()

    # 清理旧缓存
    import shutil
    pycache = os.path.join(BACKEND_DIR, "app", "__pycache__")
    if os.path.exists(pycache):
        shutil.rmtree(pycache)
        print("  ✓ 已清理 Python 缓存")

    env = os.environ.copy()
    env["DISABLE_AUTO_OPEN"] = "1"
    
    # 使用 Popen 启动，以便能控制子进程
    proc = subprocess.Popen(
        [python, backend_script],
        cwd=BACKEND_DIR,
        env=env,
        # Windows 下创建新进程组，便于终止
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    child_processes.append(proc)
    return proc


def check_frontend_deps():
    """检查并安装前端依赖"""
    # 检查 npm
    try:
        subprocess.run("npm --version", capture_output=True, check=True, shell=True)
    except Exception:
        print("  ⚠ 未找到 npm，跳过前端依赖检查")
        return False

    package_json = os.path.join(FRONTEND_DIR, "package.json")
    if not os.path.exists(package_json):
        print("  ⚠ 未找到 package.json，跳过")
        return False

    # 直接 npm install（幂等，已安装的包秒过，缺的自动装）
    print("  → 检查前端依赖...")
    result = subprocess.run("npm install", cwd=FRONTEND_DIR, shell=True)
    if result.returncode != 0:
        print("  ❌ 前端依赖安装失败")
        return False
    print("  ✓ 前端依赖就绪")

    return True


def clean_frontend_cache():
    """清理 Vite 预构建缓存，防止旧缓存导致模块加载失败"""
    import shutil
    cache_dirs = [
        os.path.join(FRONTEND_DIR, "node_modules", ".vite"),
        os.path.join(FRONTEND_DIR, "dist"),
    ]
    for d in cache_dirs:
        if os.path.exists(d):
            shutil.rmtree(d)
            print(f"  ✓ 已清理缓存: {os.path.basename(d)}")


def start_frontend():
    """启动前端开发服务器"""
    print("\n" + "=" * 50)
    print("  [前端] 启动 Vite 开发服务器...")
    clean_frontend_cache()
    print("=" * 50)

    print(f"   前端地址: http://localhost:5173")
    print(f"   按 Ctrl+C 停止所有服务")
    print()

    # 使用 Popen 启动，以便能控制子进程
    proc = subprocess.Popen(
        "npm run dev",
        cwd=FRONTEND_DIR,
        shell=True,
        creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
    )
    child_processes.append(proc)
    return proc


def main():
    """主函数"""
    # 注册信号处理，确保 Ctrl+C 能终止所有子进程
    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform != 'win32':
        signal.signal(signal.SIGTERM, signal_handler)

    print("=" * 50)
    print("  巡检助手 WEBUI - 开发模式")
    print("=" * 50)
    print(f"  项目目录: {SCRIPT_DIR}")
    print(f"  Conda 环境: {CONDA_ENV}")
    print("=" * 50)

    # 检查 conda 环境
    if not ensure_conda_env():
        sys.exit(1)
    if not os.path.exists(FRONTEND_DIR):
        print(f"❌ 前端目录不存在: {FRONTEND_DIR}")
        sys.exit(1)

    if not os.path.exists(BACKEND_DIR):
        print(f"❌ 后端目录不存在: {BACKEND_DIR}")
        sys.exit(1)

    print("\n📌 启动顺序：")
    print("   1. 后端 FastAPI 服务 (端口 8000)")
    print("   2. 前端 Vite 开发服务器 (端口 5173)")
    print("\n🌐 访问地址: http://localhost:5173")
    print("   API文档:    http://localhost:8000/docs")
    print()

    # 检查后端依赖
    print("🔍 检查后端依赖...")
    if not check_backend_deps():
        sys.exit(1)

    # 检查前端依赖
    print("🔍 检查前端依赖...")
    if not check_frontend_deps():
        sys.exit(1)
    print()

    # 启动后端
    print("▶️  启动后端...")
    backend_proc = start_backend()

    # 等待后端启动
    time.sleep(2)

    # 启动前端（Vite 会自动打开浏览器）
    print("▶️  启动前端...")
    frontend_proc = start_frontend()

    # 等待子进程，任一退出则终止所有
    try:
        while True:
            # 检查子进程状态
            if backend_proc.poll() is not None:
                print("\n⚠️ 后端进程已退出")
                break
            if frontend_proc.poll() is not None:
                print("\n⚠️ 前端进程已退出")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    # 清理所有子进程
    print("\n\n👋 正在停止所有服务...")
    kill_all_children()
    print("👋 已停止所有服务")


if __name__ == "__main__":
    main()
