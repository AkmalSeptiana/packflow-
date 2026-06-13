import os
import re
import subprocess
import sys

# --- KONFIGURASI ---
FILE_MAIN_WINDOW = "ui/main_window.py"
FILE_INSTALLER = "installer.iss"
PATH_ISCC = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

def get_current_version_from_code():
    """Membaca nomor versi langsung dari ui/main_window.py"""
    if not os.path.exists(FILE_MAIN_WINDOW):
        return None
    
    with open(FILE_MAIN_WINDOW, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Cari baris CURRENT_VERSION = "x.x.x"
    match = re.search(r'CURRENT_VERSION\s*=\s*"(.*?)"', content)
    if match:
        return match.group(1)
    return None

def sync_version_to_installer(new_version):
    """Menyinkronkan nomor versi ke installer.iss"""
    if not os.path.exists(FILE_INSTALLER):
        print(f"Error: File {FILE_INSTALLER} tidak ditemukan!")
        return False
    
    with open(FILE_INSTALLER, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Update #define MyAppVersion "x.x.x"
    new_content = re.sub(r'(#define MyAppVersion\s*)".*?"', rf'\g<1>"{new_version}"', content)
    
    with open(FILE_INSTALLER, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def run_command(command):
    print(f"\n> Running: {command}")
    process = subprocess.Popen(["powershell", "-Command", command])
    process.wait()
    return process.returncode == 0

def main():
    print("=== PACKFLOW AUTO-SYNC & RELEASE TOOL ===")
    
    # 1. Baca Versi dari Main Window
    current_version = get_current_version_from_code()
    if not current_version:
        print("❌ GAGAL: Tidak bisa menemukan CURRENT_VERSION di ui/main_window.py")
        return

    print(f"\n[1/3] Versi terdeteksi di kode: {current_version}")
    
    # 2. Sinkronkan ke Installer.iss
    print(f"Menyinkronkan ke {FILE_INSTALLER}...")
    if sync_version_to_installer(current_version):
        print("✔ Sinkronisasi Versi Berhasil.")
    else:
        return

    # 3. Jalankan Build & Installer
    do_build = input("\n[2/3] Jalankan Build EXE & Installer Full? (y/n): ").lower()
    if do_build == 'y':
        print("\n--- Memulai Build EXE ---")
        if run_command("python build_exe.py"):
            print("\n--- Memulai Kompilasi Inno Setup ---")
            iscc_cmd = f'& "{PATH_ISCC}" {FILE_INSTALLER}'
            if run_command(iscc_cmd):
                print("\n✔ SUCCESS: Installer v{current_version} siap di 'installer_dist'!")
            else:
                print("\n❌ GAGAL: Terjadi kesalahan saat kompilasi Inno Setup.")
        else:
            print("\n❌ GAGAL: Terjadi kesalahan saat build EXE.")

    # 4. Git Push
    do_push = input("\n[3/3] Kirim kode ke GitHub sekarang? (y/n): ").lower()
    if do_push == 'y':
        commit_msg = input(f"Masukkan pesan update (Default: Update to v{current_version}): ").strip()
        if not commit_msg:
            commit_msg = f"Update to version {current_version}"
        
        run_command("git add .")
        run_command(f'git commit -m "{commit_msg}"')
        run_command("git push origin main")
        print("\n✔ Kode berhasil dikirim ke GitHub.")

    print(f"\nSelesai! Sekarang tinggal upload installer ke GitHub Release.")

if __name__ == "__main__":
    main()
