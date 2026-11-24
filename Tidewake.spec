# PyInstaller spec for Tidewake (Windows, onedir)
from PyInstaller.utils.hooks import collect_submodules
hidden = ['glcontext', 'glcontext.wgl', 'glcontext.empty', 'tidewake.workers'] + collect_submodules('pyglet')
a = Analysis(['main.py'], pathex=['.'], hiddenimports=hidden,
             datas=[('assets/fonts/*.ttf', 'assets/fonts'), ('assets/fonts/OFL.txt', 'assets/fonts')],
             excludes=['PIL', 'panda3d', 'ursina', 'direct', 'tkinter', 'setuptools', 'pydoc', 'test', 'unittest',
                       'fontTools'],
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Tidewake', console=False, icon='assets/icon.ico', upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='Tidewake', upx=False)
