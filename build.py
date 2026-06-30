# -*- coding: utf-8 -*-
"""
打包脚本：构建前端 + PyInstaller 打包
用法：python build.py
"""
import os
import sys
import subprocess
import time
import shutil

# 项目根目录
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# 后端目录
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
# 前端目录
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
# spec 文件
SPEC_FILE = os.path.join(PROJECT_DIR, "patrol_web.spec")
# 版本信息文件
VERSION_FILE = os.path.join(PROJECT_DIR, "version_info.py")


def get_version():
    """从 config.py 读取版本号"""
    sys.path.insert(0, BACKEND_DIR)
    try:
        from app.config import settings
        return settings.APP_VERSION
    except Exception:
        return "1.0.0"

# exe 名称（带版本号）
APP_VERSION = get_version()
EXE_NAME = f"巡检助手WEBUI_v{APP_VERSION}.exe"


def generate_version_info():
    """生成 version_info.py"""
    print("\n[1/6] 生成版本信息...")
    ver = APP_VERSION
    ver_parts = ver.split(".")
    while len(ver_parts) < 4:
        ver_parts.append("0")

    content = f'''VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=({ver_parts[0]}, {ver_parts[1]}, {ver_parts[2]}, {ver_parts[3]}),
    prodvers=({ver_parts[0]}, {ver_parts[1]}, {ver_parts[2]}, {ver_parts[3]}),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo(
      [
        StringTable(
          u'080404b0',
          [
            StringStruct(u'CompanyName', u'巡检助手'),
            StringStruct(u'FileDescription', u'设备巡检助手 WEBUI'),
            StringStruct(u'FileVersion', u'{ver}.0'),
            StringStruct(u'InternalName', u'巡检助手WEBUI'),
            StringStruct(u'OriginalFilename', u'{EXE_NAME}'),
            StringStruct(u'ProductName', u'巡检助手 WEBUI'),
            StringStruct(u'ProductVersion', u'{ver}.0')
          ]
        )
      ]
    ),
    VarFileInfo([VarStruct(u'Translation', [2052, 1200])])
  ]
)
'''
    with open(VERSION_FILE, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ 版本号: {ver}")
    return ver


def check_node_and_build_frontend():
    """构建前端"""
    print("\n[2/6] 构建前端...")
    frontend_dist = os.path.join(FRONTEND_DIR, "dist")

    # 检查 node 和 npm
    try:
        subprocess.run("npm --version", capture_output=True, check=True, shell=True)
    except Exception:
        print("  ⚠ 未找到 Node.js/npm，跳过前端构建")
        if not os.path.exists(frontend_dist):
            print("\n❌ 前端未构建，无法打包完整的WEB应用！")
            print("请先安装 Node.js 并执行:")
            print(f"  cd {FRONTEND_DIR}")
            print("  npm install && npm run build")
            sys.exit(1)
        print(f"  ⚠ 使用已有前端文件: {frontend_dist}")
        return

    # 清理 Vite 构建缓存，确保全新构建
    print("  → 清理前端构建缓存...")
    vite_cache = os.path.join(FRONTEND_DIR, "node_modules", ".vite")
    frontend_dist = os.path.join(FRONTEND_DIR, "dist")
    for d in [vite_cache, frontend_dist]:
        if os.path.exists(d):
            try:
                shutil.rmtree(d)
                print(f"    ✓ 已清理: {os.path.basename(d)}")
            except PermissionError:
                print(f"    ⚠ 跳过被占用目录: {os.path.basename(d)}")

    # 构建前端
    print("  → 执行 npm run build...")
    result = subprocess.run("npm run build", cwd=FRONTEND_DIR, shell=True)
    if result.returncode != 0:
        print("  ❌ 前端构建失败")
        sys.exit(1)
    print("  ✓ 前端构建完成")


def kill_occupying():
    """关闭可能占用 dist/exe 的进程"""
    print("\n[3/6] 检查并关闭占用进程...")
    try:
        subprocess.run(
            ['taskkill', '/f', '/im', EXE_NAME],
            capture_output=True, timeout=5
        )
        print(f"  ✓ 已终止 {EXE_NAME} 进程")
    except Exception:
        pass
    time.sleep(1)


def clean_build():
    """清理旧的 build 和 dist 目录"""
    print("\n[4/6] 清理旧构建文件...")
    build_dir = os.path.join(PROJECT_DIR, "build")
    dist_dir = os.path.join(PROJECT_DIR, "dist")

    if os.path.exists(build_dir):
        shutil.rmtree(build_dir)
        print("  ✓ 已删除 build/ 目录")
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
        print("  ✓ 已删除 dist/ 目录")


def run_pyinstaller():
    """执行 PyInstaller 打包"""
    print("\n[5/6] 开始 PyInstaller 打包...")
    print(f"  Spec 文件: {SPEC_FILE}")
    print(f"  输出文件: {EXE_NAME}")
    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller",
         SPEC_FILE, "--noconfirm", "--clean"],
        cwd=PROJECT_DIR,
    )
    if result.returncode != 0:
        print("\n❌ 打包失败！")
        sys.exit(1)
    print("  ✓ PyInstaller 打包完成")


def verify_output():
    """验证输出"""
    print("\n[6/6] 验证输出...")
    exe_path = os.path.join(PROJECT_DIR, "dist", EXE_NAME)
    if os.path.exists(exe_path):
        size_mb = os.path.getsize(exe_path) / (1024 * 1024)
        print(f"  ✓ {EXE_NAME} → {size_mb:.1f} MB")
        print(f"\n✅ 打包成功！")
        print(f"   输出目录: {os.path.join(PROJECT_DIR, 'dist')}")
        print(f"   文件路径: {exe_path}")
        print(f"\n   使用说明:")
        print(f"   1. 双击 {EXE_NAME} 启动")
        print(f"   2. 会自动打开浏览器访问 http://127.0.0.1:8000")
        print(f"   3. 关闭窗口即可停止服务")
    else:
        print(f"\n❌ 未找到输出文件: {exe_path}")
        sys.exit(1)


if __name__ == "__main__":
    print("=" * 60)
    print("  巡检助手 WEBUI - 打包脚本")
    print("=" * 60)
    print(f"  项目目录: {PROJECT_DIR}")
    print(f"  后端目录: {BACKEND_DIR}")
    print(f"  前端目录: {FRONTEND_DIR}")
    print("=" * 60 + "\n")

    try:
        generate_version_info()
        check_node_and_build_frontend()
        kill_occupying()
        clean_build()
        run_pyinstaller()
        verify_output()
    except KeyboardInterrupt:
        print("\n\n⏹  用户中断")
        sys.exit(1)
