# -*- mode: python ; coding: utf-8 -*-
"""
巡检助手 WEBUI - PyInstaller 打包配置
单文件 exe，包含后端 FastAPI 服务 + 前端静态文件
"""
import os
import sys

block_cipher = None

# 项目根目录
project_dir = os.path.dirname(os.path.abspath(SPEC))

# 版本信息文件
version_file = os.path.join(project_dir, "version_info.py")

# 后端入口脚本
run_script = os.path.join(project_dir, "backend", "run.py")

# 读取版本号
sys.path.insert(0, os.path.join(project_dir, "backend"))
try:
    from app.config import settings
    app_version = settings.APP_VERSION
except Exception:
    app_version = "1.0.0"

# 前端静态文件目录
web_dist_dir = os.path.join(project_dir, "frontend", "dist")

# 收集需要打包的数据文件
datas = []

# 如果前端已构建，添加到打包文件中
if os.path.exists(web_dist_dir):
    datas.append((web_dist_dir, "web/dist"))
    print(f"[SPEC] 包含前端静态文件: {web_dist_dir}")
else:
    print(f"[SPEC] 警告: 前端静态文件不存在: {web_dist_dir}")
    print("[SPEC] 请先执行 npm run build 构建前端")

# 隐式导入（PyInstaller 可能检测不到的模块）
hiddenimports = [
    # FastAPI / Starlette
    "fastapi",
    "starlette",
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    # Pydantic
    "pydantic",
    "pydantic.deprecated",
    "pydantic.deprecated.class_validators",
    "pydantic.deprecated.decorator",
    "pydantic.deprecated.parse",
    "pydantic.deprecated.tools",
    "pydantic.deprecated.types",
    "pydantic.deprecated.validators",
    # SSH 相关
    "paramiko",
    "asyncssh",
    "asyncio",
    "concurrent.futures",
    "multiprocessing",
    "multiprocessing.managers",
    "multiprocessing.pool",
    "multiprocessing.sharedctypes",
    # 加密相关
    "cryptography",
    "cryptography.hazmat",
    "cryptography.hazmat.primitives",
    "cryptography.hazmat.primitives.ciphers",
    "cryptography.hazmat.primitives.ciphers.modes",
    "cryptography.hazmat.backends",
    "cryptography.hazmat.backends.openssl",
    "bcrypt",
    # 数据库
    "sqlite3",
    # 网络
    "websockets",
    "anyio",
    "anyio._backends._asyncio",
    "sniffio",
    "idna",
    "encodings",
    "encodings.idna",
    "encodings.gbk",
    "encodings.gb2312",
    "encodings.gb18030",
    # 其他
    "six",
    "cffi",
    "pycparser",
    "pynacl",
]

a = Analysis(
    [run_script],
    pathex=[project_dir],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'PyQt5',
        'PyQt4',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name=f'巡检助手WEBUI_v{app_version}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version=version_file,
)
