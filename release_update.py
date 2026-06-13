import os
import re
import subprocess
import sys

# --- KONFIGURASI ---
FILE_MAIN_WINDOW = "ui/main_window.py"
FILE_INSTALLER = "installer.iss"

def update_version_in_file(file_path, pattern, new_version):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} tidak ditemukan!")
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = re.sub(pattern, rf'\g<1>"{new_version}"', content)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def run_command(command):
    print(f"\n> Running: {command}")
    process = subprocess.Popen(command, shell=True)
    process.wait()
    return process.returncode == 0

def main():
    print("=== PACKFLOW AUTO-RELEASE TOOL ===")
    
    # 1. Input Versi Baru
    new_version = input("\nMasukkan nomor versi baru (misal: 2.4.0): ").strip()
    if not new_version:
        print("Versi tidak boleh kosong!")
        return

    # 2. Update Versi di File
    print(f"\n[1/4] Mengupdate nomor versi ke {new_version}...")
    
    # Update ui/main_window.py (CURRENT_VERSION = "x.x.x")
    update_version_in_file(FILE_MAIN_WINDOW, r'(CURRENT_VERSION\s*=\s*)".*?"', new_version)
    
    # Update ui/main_window.py (Teks Versi di About)
    with open(FILE_MAIN_WINDOW, 'r', encoding='utf-8') as f:
        content = f.read()
    content = re.sub(r'(text="Versi\s+).*?(")', rf'\g<1>{new_version}\g<2>', content)
    with open(FILE_MAIN_WINDOW, 'w', encoding='utf-8') as f:
        f.write(content)

    # Update installer.iss (#define MyAppVersion "x.x.x")
    update_version_in_file(FILE_INSTALLER, r'(#define MyAppVersion\s*)".*?"', new_version)
    
    print("✔ Nomor versi berhasil diperbarui di semua file.")

    # 3. Jalankan Build (Opsional)
    do_build = input("\n[2/4] Jalankan build EXE sekarang? (y/n): ").lower()
    if do_build == 'y':
        print("Menjalankan build_exe.py...")
        run_command("python build_exe.py")
        print("\n✔ Pastikan Anda menjalankan Inno Setup setelah ini untuk membuat Installer.")

    # 4. Git Push
    do_push = input("\n[3/4] Kirim perubahan kode ke GitHub sekarang? (y/n): ").lower()
    if do_push == 'y':
        commit_msg = input("Masukkan pesan update: ").strip()
        if not commit_msg:
            commit_msg = f"Update to version {new_version}"
        
        run_command("git add .")
        run_command(f'git commit -m "{commit_msg}"')
        run_command("git push origin main")
        print("\n✔ Kode berhasil dikirim ke GitHub.")

    # 5. Selesai
    print(f"\n[4/4] PROSES SELESAI!")
    print(f"--------------------------------------------------")
    print(f"LANGKAH TERAKHIR:")
    print(f"1. Buka GitHub Browser.")
    print(f"2. Buat Release baru dengan Tag: v{new_version}")
    print(f"3. Upload file 'PackFlow_Setup.exe' ke Release tersebut.")
    print(f"--------------------------------------------------")

if __name__ == "__main__":
    main()
