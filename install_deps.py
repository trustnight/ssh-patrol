# -*- coding: utf-8 -*-
"""
依赖安装脚本：统一安装后端 + 前端所有依赖
用法：python install_deps.py
"""
import os
import sys
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(SCRIPT_DIR, "frontend")
CONDA_ENV = "py3710"


def check_conda():
    """检查 conda 环境"""
    current_env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if current_env == CONDA_ENV:
        print(f"  ✓ Conda 环境: {CONDA_ENV}")
        return True
    print(f"  ⚠ 当前环境: {current_env or '无'}，需要: {CONDA_ENV}")
    print(f"    请先执行: conda activate {CONDA_ENV}")
    return False


def install_pip():
    """安装后端 Python 依赖"""
    req_file = os.path.join(SCRIPT_DIR, "requirements.txt")
    if not os.path.exists(req_file):
        print("  ⚠ 未找到 requirements.txt，跳过")
        return True

    print("  → pip install -r requirements.txt ...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", req_file],
        shell=True
    )
    if result.returncode != 0:
        print("  ❌ 后端依赖安装失败")
        return False
    print("  ✓ 后端依赖就绪")
    return True


def install_npm():
    """安装前端 npm 依赖"""
    try:
        subprocess.run("npm --version", capture_output=True, check=True, shell=True)
    except Exception:
        print("  ⚠ 未找到 Node.js/npm，跳过前端依赖")
        return False

    package_json = os.path.join(FRONTEND_DIR, "package.json")
    if not os.path.exists(package_json):
        print("  ⚠ 未找到 package.json，跳过")
        return False

    print("  → npm install ...")
    result = subprocess.run("npm install", cwd=FRONTEND_DIR, shell=True)
    if result.returncode != 0:
        print("  ❌ 前端依赖安装失败")
        return False

    # 清理 Vite 预构建缓存，避免旧缓存导致问题
    import shutil
    vite_cache = os.path.join(FRONTEND_DIR, "node_modules", ".vite")
    if os.path.exists(vite_cache):
        try:
            shutil.rmtree(vite_cache)
            print("  ✓ 已清理 Vite 缓存")
        except PermissionError:
            print("  ⚠ Vite 缓存被占用，跳过清理")

    print("  ✓ 前端依赖就绪")
    return True


def main():
    print("=" * 50)
    print("  巡检助手 WEBUI - 依赖安装")
    print("=" * 50)
    print()

    if not check_conda():
        sys.exit(1)

    ok = True

    print("\n[1/2] 后端依赖")
    if not install_pip():
        ok = False

    print("\n[2/2] 前端依赖")
    if not install_npm():
        ok = False

    print()
    if ok:
        print("✅ 所有依赖安装完成")
    else:
        print("❌ 部分依赖安装失败，请检查上方错误信息")
        sys.exit(1)


if __name__ == "__main__":
    main()
