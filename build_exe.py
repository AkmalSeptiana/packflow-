import PyInstaller.__main__
import os
import customtkinter
import shutil

# 1. Clean previous builds
for folder in ['build', 'dist']:
    if os.path.exists(folder):
        shutil.rmtree(folder)

# 2. Get customtkinter path for data files
ctk_path = os.path.dirname(customtkinter.__file__)

# 3. Build Command
print(">>> MEMULAI PROSES BUILD EXE...")
PyInstaller.__main__.run([
    'main.py',
    '--noconfirm',
    '--onefile',
    '--windowed',
    '--name=PackFlow',
    '--icon=assets/icon.ico',
    '--add-data=assets;assets',
    '--add-data=config;config',
    '--add-data=logs;logs',
    f'--add-data={ctk_path};customtkinter',
    '--clean'
])

print("\n>>> BERHASIL! File EXE ada di folder 'dist/PackFlow.exe'")
