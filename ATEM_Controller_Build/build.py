# build.py
import PyInstaller.__main__
import shutil
import os

# Clean previous builds
if os.path.exists('dist'):
    shutil.rmtree('dist')
if os.path.exists('build'):
    shutil.rmtree('build')

# Run PyInstaller
PyInstaller.__main__.run([
    'atem_controller.spec',
    '--clean',
])

print("Build complete! Executable is in the 'dist' folder")