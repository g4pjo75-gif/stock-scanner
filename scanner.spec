# -*- mode: python ; coding: utf-8 -*-
"""
이평선 대순환 스캐너 - PyInstaller 빌드 설정
"""

import os
import sys

block_cipher = None

# 프로젝트 경로
PROJECT_DIR = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['launcher.py'],
    pathex=[PROJECT_DIR, os.path.join(PROJECT_DIR, 'backend')],
    binaries=[],
    datas=[
        ('frontend', 'frontend'),
        ('backend', 'backend'),
    ],
    hiddenimports=[
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'fastapi',
        'starlette',
        'starlette.routing',
        'starlette.responses',
        'starlette.staticfiles',
        'starlette.middleware',
        'starlette.middleware.cors',
        'yfinance',
        'pandas',
        'numpy',
        'apscheduler',
        'apscheduler.schedulers.background',
        'apscheduler.triggers.cron',
        'aiofiles',
        'sqlite3',
        'json',
        'anyio._backends._asyncio',
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
    name='StockScanner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 콘솔 창 표시 (로그 확인용)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
