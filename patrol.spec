# -*- mode: python ; coding: utf-8 -*-

import os
import customtkinter

block_cipher = None

# 获取 customtkinter 资源目录
ctk_path = os.path.dirname(customtkinter.__file__)
added_files = [
    (os.path.join(ctk_path, "assets"), "customtkinter/assets"),
]

a = Analysis(['main.py'],
             pathex=['.', 'models'],
             binaries=[],
             datas=added_files,
             hiddenimports=[
                 'paramiko',
                 'asyncssh',
                 'asyncio',
                 'cryptography',
                 'cryptography.hazmat',
                 'cryptography.hazmat.primitives',
                 'cryptography.hazmat.primitives.ciphers',
                 'cryptography.hazmat.backends',
                 'six',
                 'concurrent.futures',
                 'multiprocessing',
                 'multiprocessing.managers',
                 'multiprocessing.pool',
                 'multiprocessing.sharedctypes',
                 'idna',
                 'encodings',
                 'encodings.idna',
                 'customtkinter',
                 'customtkinter.windows',
                 'customtkinter.windows.widgets',
                 'customtkinter.windows.widgets.core_widget_classes',
                 'customtkinter.windows.widgets.utility',
             ],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             cipher=block_cipher,
             noarchive=False)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(pyz,
              a.scripts,
              a.binaries,
              a.zipfiles,
              a.datas,
              [],
              name='巡检助手',
              debug=False,
              bootloader_ignore_signals=False,
              strip=False,
              upx=False,
              upx_exclude=[],
              runtime_tmpdir=None,
              console=False,
              disable_windowed_traceback=False,
              target_arch=None,
              codesign_identity=None,
              entitlements_file=None)
