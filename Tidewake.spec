# PyInstaller spec for Tidewake (Windows, onedir)
from PyInstaller.utils.hooks import collect_submodules
hidden = ['glcontext', 'glcontext.wgl', 'glcontext.empty', 'tidewake.workers', 'tidewake.fast', 'tidewake.music'] + collect_submodules('pyglet') + \
    collect_submodules('numba', filter=lambda n: '.tests' not in n) + collect_submodules('llvmlite', filter=lambda n: '.tests' not in n)
a = Analysis(['main.py'], pathex=['.'], hiddenimports=hidden,
             datas=[('assets/fonts/*.ttf', 'assets/fonts'), ('assets/showcase/*.json', 'assets/showcase'), ('assets/fonts/OFL.txt', 'assets/fonts')],
             excludes=['PIL', 'panda3d', 'ursina', 'direct', 'tkinter', 'setuptools', 'pydoc', 'test', 'numba.tests', 'llvmlite.tests',
                       'fontTools'],
             module_collection_mode={'tidewake.fast': 'py'},   # numba's cache needs the real source file
             noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Tidewake', console=False, icon='assets/icon.ico', upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name='Tidewake', upx=False)
