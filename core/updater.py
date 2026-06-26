import requests
import os
import sys
import subprocess
import threading
import tempfile

class AutoUpdater:
    def __init__(self, current_version, repo_owner, repo_name, logger=None):
        self.current_version = current_version.strip().lower().replace('v', '')
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.logger = logger
        self.update_info = None
        self.is_checking = False

    def log(self, msg):
        if self.logger:
            self.logger(f"[UPDATER] {msg}")
        else:
            print(f"[UPDATER] {msg}")

    def check_for_updates(self, callback):
        """
        Runs the update check in a background thread.
        Callback should accept (has_update: bool, release_info: dict)
        """
        if self.is_checking:
            return
            
        def _check():
            self.is_checking = True
            try:
                url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
                headers = {
                    "User-Agent": "PackFlow-App/1.0",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    latest_version = data.get("tag_name", "").strip().lower().replace('v', '')
                    
                    if latest_version and self._is_newer(latest_version, self.current_version):
                        self.log(f"Versi baru ditemukan: {latest_version}")
                        self.update_info = {
                            "version": data.get("tag_name"),
                            "name": data.get("name"),
                            "body": data.get("body"),
                            "download_url": self._get_exe_url(data.get("assets", []))
                        }
                        callback(True, self.update_info)
                    else:
                        self.log(f"Aplikasi sudah versi terbaru ({self.current_version})")
                        callback(False, None)
                elif response.status_code == 403:
                    self.log("Cek update dilewati: GitHub API rate limit tercapai (akan coba lagi nanti)")
                    callback(False, None)
                elif response.status_code == 404:
                    self.log("Cek update gagal: Repository tidak ditemukan atau belum ada release")
                    callback(False, None)
                else:
                    self.log(f"Gagal cek update: Status {response.status_code}")
                    callback(False, None)
            except Exception as e:
                self.log(f"Error cek update: {str(e)}")
                callback(False, None)
            finally:
                self.is_checking = False

        thread = threading.Thread(target=_check)
        thread.daemon = True
        thread.start()

    def _is_newer(self, latest, current):
        try:
            l_parts = [int(p) for p in latest.split('.')]
            c_parts = [int(p) for p in current.split('.')]
            # Padding to same length
            max_len = max(len(l_parts), len(c_parts))
            l_parts += [0] * (max_len - len(l_parts))
            c_parts += [0] * (max_len - len(c_parts))
            return l_parts > c_parts
        except:
            return latest != current

    def _get_exe_url(self, assets):
        for asset in assets:
            if asset.get("name", "").endswith(".exe"):
                return asset.get("browser_download_url")
        return None

    def start_update(self, download_url, progress_callback, finish_callback):
        """
        Downloads and executes the installer.
        """
        def _download():
            try:
                self.log(f"Memulai download dari: {download_url}")
                response = requests.get(download_url, stream=True)
                total_size = int(response.headers.get('content-length', 0))
                
                temp_dir = tempfile.gettempdir()
                installer_path = os.path.join(temp_dir, "PackFlow_Update_Setup.exe")
                
                downloaded = 0
                with open(installer_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_size > 0:
                                progress_callback(downloaded / total_size)
                
                self.log("Download selesai, bersiap menjalankan installer...")
                finish_callback(True, installer_path)
                
                # Gunakan taskkill untuk memastikan proses benar-benar mati, 
                # beri jeda 2 detik, lalu jalankan installer secara VERYSILENT.
                cmd = f'taskkill /F /IM PackFlow.exe /T & timeout /t 2 /nobreak & start "" "{installer_path}" /VERYSILENT /SUPPRESSMSGBOXES'
                
                self.log("Menutup aplikasi dan meluncurkan update otomatis...")
                subprocess.Popen(cmd, shell=True)
                
                os._exit(0)
                
            except Exception as e:
                self.log(f"Gagal update: {str(e)}")
                finish_callback(False, str(e))

        thread = threading.Thread(target=_download)
        thread.daemon = True
        thread.start()
