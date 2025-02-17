# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['dist/wuneng.py'],  # 使用加密后的主程序
    pathex=[],
    binaries=[],
    datas=[
        ('dist/pyarmor_runtime_000000', 'pyarmor_runtime_000000'),  # 包含PyArmor运行时
        ('logo.py', '.'),  # 添加 logo.py
        ('cursor_auth_manager.py', '.'),  # 添加 cursor_auth_manager.py
        ('logger.py', '.'),  # 添加 logger.py
        ('exit_cursor.py', '.'),  # 添加 exit_cursor.py
    ],
    hiddenimports=[
        'requests',
        'psutil',
        'colorama',
        'uuid',
        'json',
        'platform',
        'hashlib',
        'logging',
        'logo',
        'cursor_auth_manager',
        'logger',
        'exit_cursor',
        'sqlite3',
        'sys',
        'os',
        'time',
        'datetime',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='wuneng',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
) 