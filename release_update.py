import os
import re
import subprocess
import sys

# --- KONFIGURASI ---
FILE_MAIN_WINDOW = "ui/main_window.py"
FILE_INSTALLER = "installer.iss"
PATH_ISCC = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

def get_current_version_from_code():
    if not os.path.exists(FILE_MAIN_WINDOW):
        return None
    with open(FILE_MAIN_WINDOW, 'r', encoding='utf-8') as f:
        content = f.read()
    match = re.search(r'CURRENT_VERSION\s*=\s*"(.*?)"', content)
    return match.group(1) if match else None

def update_release_notes_in_code(notes):
    """Menulis catatan rilis ke dalam variabel RELEASE_NOTES di main_window.py"""
    if not os.path.exists(FILE_MAIN_WINDOW):
        return False
    with open(FILE_MAIN_WINDOW, 'r', encoding='utf-8') as f:
        content = f.read()
    # Update RELEASE_NOTES = "..."
    new_content = re.sub(r'(RELEASE_NOTES\s*=\s*)".*?"', rf'\g<1>"{notes}"', content)
    with open(FILE_MAIN_WINDOW, 'w', encoding='utf-8') as f:
        f.write(new_content)
    return True

def sync_version_to_installer(new_version):
    if not os.path.exists(FILE_INSTALLER):
        return False
    with open(FILE_INSTALLER, 'r', encoding='utf-8') as f:
        content = f.read()
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
    print("=== PACKFLOW AUTO-SYNC & RELEASE TOOL (V2) ===")
    
    # 1. Deteksi Versi
    current_version = get_current_version_from_code()
    if not current_version:
        print("❌ GAGAL: Tidak bisa menemukan CURRENT_VERSION.")
        return
    print(f"\n[1/4] Versi terdeteksi: {current_version}")

    # 2. Input Pesan Update (DI AWAL)
    update_msg = input("Masukkan pesan update/fitur baru: ").strip()
    if not update_msg:
        update_msg = "Pembaruan rutin dan perbaikan bug."
    
    # Simpan pesan ke kode agar build EXE mengandung pesan ini
    print("Menanamkan pesan update ke dalam kode...")
    update_release_notes_in_code(update_msg)
    
    # 3. Sinkronkan ke Installer.iss
    print(f"Menyinkronkan versi ke {FILE_INSTALLER}...")
    sync_version_to_installer(current_version)
    print("✔ Persiapan rilis selesai.")

    # 4. Jalankan Build & Installer
    do_build = input("\n[2/4] Jalankan Build EXE & Installer Full? (y/n): ").lower()
    if do_build == 'y':
        # Pastikan tidak ada installer lama yang sedang terbuka/mengunci file
        print("Membersihkan sisa proses dan file installer lama...")
        run_command('taskkill /F /IM PackFlow_Setup.exe /T 2>$null')
        
        # Coba hapus file secara manual lewat python agar lebih pasti
        old_installer = os.path.join("installer_dist", "PackFlow_Setup.exe")
        if os.path.exists(old_installer):
            try:
                os.remove(old_installer)
                print("✔ File installer lama berhasil dihapus.")
            except Exception as e:
                print(f"⚠️ PERINGATAN: Tidak bisa menghapus {old_installer}. Silakan tutup installer atau restart PC. Error: {e}")
                return # Stop jika file masih terkunci
        
        print("\n--- Memulai Build EXE ---")
        if run_command("python build_exe.py"):
            print("\n--- Memulai Kompilasi Inno Setup ---")
            iscc_cmd = f'& "{PATH_ISCC}" {FILE_INSTALLER}'
            if run_command(iscc_cmd):
                print(f"\n✔ SUCCESS: Installer v{current_version} siap di folder 'installer_dist'!")
            else:
                print("\n❌ GAGAL: Kompilasi Inno Setup error.")
        else:
            print("\n❌ GAGAL: Build EXE error.")

    # 5. Git Push
    do_push = input("\n[3/4] Kirim kode ke GitHub sekarang? (y/n): ").lower()
    if do_push == 'y':
        run_command("git add .")
        run_command(f'git commit -m "Release v{current_version}: {update_msg}"')
        run_command("git push origin main")
        print("\n✔ Kode dan pesan berhasil dikirim ke GitHub.")

    print(f"\nSelesai! Catatan: Gunakan pesan yang sama saat membuat Release di GitHub.")

if __name__ == "__main__":
    main()
