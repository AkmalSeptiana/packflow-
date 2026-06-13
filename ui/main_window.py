import customtkinter as ctk
from tkinter import filedialog, ttk
import os
import threading
import urllib.request
import tempfile
from PIL import Image, ImageTk
from core.pdf_reader import ShopeePDFReader, TikTokPDFReader, LazadaPDFReader
from core.sku_parser import SKUParser
from core.pdf_writer import PDFLabelWriter
import json
import datetime
import sys
import tkinter as tk
from core.updater import AutoUpdater

CURRENT_VERSION = "2.3.0"

INDONESIAN_MONTHS = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

INDONESIAN_DAYS = {
    "Monday": "Senin",
    "Tuesday": "Selasa",
    "Wednesday": "Rabu",
    "Thursday": "Kamis",
    "Friday": "Jumat",
    "Saturday": "Sabtu",
    "Sunday": "Minggu"
}

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PackFlow - Pelabelan Dalam Hitungan Detik")
        # Center the window on the screen
        width = 560
        height = 960
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2)
        y = (screen_height // 2) - (height // 2) - 40
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Set window icon
        icon_path_ico = resource_path("assets/icon.ico")
        icon_path_png = resource_path("assets/icon.png")
        if os.path.exists(icon_path_ico) and sys.platform.startswith("win"):
            try:
                self.iconbitmap(icon_path_ico)
            except Exception:
                pass
        elif os.path.exists(icon_path_png):
            try:
                from PIL import ImageTk
                img = Image.open(icon_path_png)
                self.icon_photo = ImageTk.PhotoImage(img)
                self.iconphoto(False, self.icon_photo)
            except Exception:
                pass
        
        # Load settings
        if getattr(sys, 'frozen', False):
            app_dir = os.path.dirname(sys.executable)
        else:
            app_dir = os.path.abspath(".")
        self.settings_path = os.path.join(app_dir, "config", "settings.json")
        self._load_settings()
        
        # Set appearance mode from settings
        theme = self.settings.get("theme", "light")
        ctk.set_appearance_mode(theme)
        ctk.set_default_color_theme("blue")
        
        # Window main background
        self.configure(fg_color=("#F3F4F6", "#0B0F19"))
        
        # Stats & status variables
        self.total_data_str = ctk.StringVar(value="0")
        self.berhasil_str = ctk.StringVar(value="0")
        self.gagal_str = ctk.StringVar(value="0")
        self.sku_unik_str = ctk.StringVar(value="0")
        self.hasil_scan_title_str = ctk.StringVar(value="HASIL SCAN (0 DATA)")
        self.progress_percent_str = ctk.StringVar(value="0%")
        self.progress_text_str = ctk.StringVar(value="Memproses 0 / 0 data resi...")
        self.status_bar_str = ctk.StringVar(value="Status: Siap memproses PDF resi.")
        self.datetime_str = ctk.StringVar(value=self._get_indonesian_datetime())
        
        self.is_loading = False
        self.current_loading_frame = 0
        self.loading_frames = []
        
        self._load_icons()
        self._setup_ui()
        self._create_loading_animation()
        self._animate_welcome_slide()
        
        # Initialize Auto Updater
        # Menggunakan akun GitHub asli Anda: AkmalSeptiana/packflow-
        self.updater = AutoUpdater(CURRENT_VERSION, "AkmalSeptiana", "packflow-", logger=self._ui_log)
        self.after(3000, self._check_updates) # Cek setelah 3 detik aplikasi terbuka
        
    def _load_settings(self):
        # 1. Try to load external settings (user modified)
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r') as f:
                    self.settings = json.load(f)
                return
            except Exception:
                pass
        
        # 2. Try to load bundled settings (from EXE resources)
        bundled_settings = resource_path("config/settings.json")
        if os.path.exists(bundled_settings):
            try:
                with open(bundled_settings, 'r') as f:
                    self.settings = json.load(f)
                return
            except Exception:
                pass

        # 3. Last fallback: Hardcoded defaults
        self.settings = self._get_default_settings()

    def _get_default_settings(self):
        return {
            "sku_suffix": "ARY",
            "ignored_skus": ["BROSUR", "FREE-PACKING", "BONUS", "SAMPEL", "VOUCHER"],
            "sku_whitelist": [
                "MLS", "HEX", "KAM", "KLRN", "PSM", "AQU", "AMP", "SKP", "SQU", "LMB",
                "CHS", "SKIN", "OIL", "WNT", "IFI", "KGE", "RAD", "GRC", "KLR", "ALB",
                "QNC", "WBW", "KSL"
            ],
            "label_font_family": "Helvetica-Bold",
            "label_font_size": 18,
            "label_color": "Red",
            "label_position": "AUTO",
            "marketplace_mode": "Shopee",
            "split_pdf": True,
            "filename_format_bulk": "{nama}_{hari}{bulan}",
            "filename_format_split": "{kota}_{resi}",
            "theme": "dark"
        }

    def _load_icons(self):
        self.settings_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/settings_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/settings_dark.png")),
            size=(16, 16)
        )
        self.settings_title_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/settings_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/settings_dark.png")),
            size=(24, 24)
        )
        self.file_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/file_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/file_dark.png")),
            size=(14, 14)
        )
        self.folder_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/folder_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/folder_dark.png")),
            size=(14, 14)
        )
        self.play_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/play_white.png")),
            dark_image=Image.open(resource_path("assets/lucide/play_white.png")),
            size=(16, 16)
        )
        self.input_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/download_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/download_blue.png")),
            size=(16, 16)
        )
        self.status_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/activity_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/activity_blue.png")),
            size=(16, 16)
        )
        self.copy_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/copy_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/copy_blue.png")),
            size=(14, 14)
        )
        self.send_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/send_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/send_blue.png")),
            size=(14, 14)
        )
        self.send_filled_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/send_filled.png")),
            dark_image=Image.open(resource_path("assets/lucide/send_filled.png")),
            size=(14, 14)
        )
        self.open_file_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/folder_green.png")),
            dark_image=Image.open(resource_path("assets/lucide/folder_green.png")),
            size=(14, 14)
        )
        self.sun_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/sun_white.png")),
            dark_image=Image.open(resource_path("assets/lucide/sun_white.png")),
            size=(14, 14)
        )
        self.moon_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/moon_dark.png")),
            dark_image=Image.open(resource_path("assets/lucide/moon_dark.png")),
            size=(14, 14)
        )
        self.warning_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/warning_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/warning_dark.png")),
            size=(14, 14)
        )
        self.x_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/x_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/x_dark.png")),
            size=(14, 14)
        )
        self.save_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/save_white.png")),
            dark_image=Image.open(resource_path("assets/lucide/save_white.png")),
            size=(14, 14)
        )
        self.loading_icon_static = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/activity_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/activity_blue.png")),
            size=(24, 24)
        )
        self.arrow_left_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/arrow_left_light.png")),
            dark_image=Image.open(resource_path("assets/lucide/arrow_left_dark.png")),
            size=(14, 14)
        )
        self.tag_blue_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/tag_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/tag_blue.png")),
            size=(16, 16)
        )
        self.palette_blue_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/palette_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/palette_blue.png")),
            size=(16, 16)
        )
        self.shopping_bag_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/shopping_bag_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/shopping_bag_blue.png")),
            size=(20, 20)
        )
        self.info_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/info_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/info_blue.png")),
            size=(16, 16)
        )
        self.files_blue_icon = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lucide/files_blue.png")),
            dark_image=Image.open(resource_path("assets/lucide/files_blue.png")),
            size=(20, 20)
        )
        
        # Marketplace Logos
        self.shopee_logo = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/shopee_logo.png")),
            dark_image=Image.open(resource_path("assets/shopee_logo.png")),
            size=(32, 32)
        )
        self.tiktok_logo = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/tiktok_logo.png")),
            dark_image=Image.open(resource_path("assets/tiktok_logo.png")),
            size=(32, 32)
        )
        self.lazada_logo = ctk.CTkImage(
            light_image=Image.open(resource_path("assets/lazada_logo.png")),
            dark_image=Image.open(resource_path("assets/lazada_logo.png")),
            size=(32, 32)
        )

    def _get_indonesian_datetime(self):
        now = datetime.datetime.now()
        day_name = INDONESIAN_DAYS.get(now.strftime("%A"), now.strftime("%A"))
        day = now.strftime("%d")
        month = INDONESIAN_MONTHS.get(now.month, now.strftime("%B"))
        year = now.strftime("%Y")
        time_str = now.strftime("%H:%M:%S")
        return f"{day_name}, {day} {month} {year} {time_str}"

    def _update_datetime_loop(self):
        current_time = self._get_indonesian_datetime()
        self.datetime_str.set(current_time)
        if hasattr(self, "date_label"):
            self.date_label.configure(text=current_time)
        self.after(1000, self._update_datetime_loop)

    def _hex_to_rgb(self, hex_str):
        hex_str = hex_str.lstrip('#')
        return tuple(int(hex_str[i:i+2], 16) for i in (0, 2, 4))

    def _draw_gradient(self, canvas, width, height, color1, color2, color3=None):
        canvas.delete("gradient")
        r1, g1, b1 = self._hex_to_rgb(color1)
        r2, g2, b2 = self._hex_to_rgb(color2)
        if color3:
            r3, g3, b3 = self._hex_to_rgb(color3)
        
        step = 4
        for y in range(0, height, step):
            ratio = y / float(height) if height > 0 else 0
            if color3:
                if ratio < 0.5:
                    sub_ratio = ratio * 2.0
                    r = int(r1 + (r2 - r1) * sub_ratio)
                    g = int(g1 + (g2 - g1) * sub_ratio)
                    b = int(b1 + (b2 - b1) * sub_ratio)
                else:
                    sub_ratio = (ratio - 0.5) * 2.0
                    r = int(r2 + (r3 - r2) * sub_ratio)
                    g = int(g2 + (g3 - g2) * sub_ratio)
                    b = int(b2 + (b3 - b2) * sub_ratio)
            else:
                r = int(r1 + (r2 - r1) * ratio)
                g = int(g1 + (g2 - g1) * ratio)
                b = int(b1 + (b2 - b1) * ratio)
                
            color = f"#{r:02x}{g:02x}{b:02x}"
            canvas.create_rectangle(0, y, width, y + step, fill=color, outline=color, tags="gradient")
        canvas.tag_lower("gradient")

    def _get_gradient_color(self, y_ratio):
        # Cap y_ratio to [0.0, 1.0]
        y_ratio = max(0.0, min(1.0, y_ratio))
        r1, g1, b1 = self._hex_to_rgb("#080B11")
        r2, g2, b2 = self._hex_to_rgb("#1E1B4B")
        r3, g3, b3 = self._hex_to_rgb("#0F172A")
        
        if y_ratio < 0.5:
            sub_ratio = y_ratio * 2.0
            r = int(r1 + (r2 - r1) * sub_ratio)
            g = int(g1 + (g2 - g1) * sub_ratio)
            b = int(b1 + (b2 - b1) * sub_ratio)
        else:
            sub_ratio = (y_ratio - 0.5) * 2.0
            r = int(r2 + (r3 - r2) * sub_ratio)
            g = int(g2 + (g3 - g2) * sub_ratio)
            b = int(b2 + (b3 - b2) * sub_ratio)
            
        return f"#{r:02x}{g:02x}{b:02x}"

    def _on_canvas_configure(self, event):
        self._draw_gradient(self.splash_canvas, event.width, event.height, "#080B11", "#1E1B4B", "#0F172A")
        
        # Center welcome, loading, and footer items horizontally if window changes size
        center_x = event.width / 2
        
        # Adjust welcome items
        if hasattr(self, "welcome_logo_item"):
            current_coords = self.splash_canvas.coords(self.welcome_logo_item)
            if current_coords:
                self.splash_canvas.coords(self.welcome_logo_item, center_x, current_coords[1])
        if hasattr(self, "welcome_separator"):
            current_coords = self.splash_canvas.coords(self.welcome_separator)
            if current_coords:
                self.splash_canvas.coords(self.welcome_separator, center_x - 40, current_coords[1], center_x + 40, current_coords[3])
        if hasattr(self, "welcome_desc"):
            current_coords = self.splash_canvas.coords(self.welcome_desc)
            if current_coords:
                self.splash_canvas.coords(self.welcome_desc, center_x, current_coords[1])
        if hasattr(self, "welcome_btn_window"):
            current_coords = self.splash_canvas.coords(self.welcome_btn_window)
            if current_coords:
                self.splash_canvas.coords(self.welcome_btn_window, center_x, current_coords[1])
                
        # Adjust loading items
        if hasattr(self, "loading_logo_item"):
            current_coords = self.splash_canvas.coords(self.loading_logo_item)
            if current_coords:
                self.splash_canvas.coords(self.loading_logo_item, center_x, current_coords[1])
        if hasattr(self, "loading_pb_window"):
            current_coords = self.splash_canvas.coords(self.loading_pb_window)
            if current_coords:
                self.splash_canvas.coords(self.loading_pb_window, center_x, current_coords[1])
        if hasattr(self, "loading_status_item"):
            current_coords = self.splash_canvas.coords(self.loading_status_item)
            if current_coords:
                self.splash_canvas.coords(self.loading_status_item, center_x, current_coords[1])

        # Adjust footer item
        if hasattr(self, "splash_footer_item"):
            current_coords = self.splash_canvas.coords(self.splash_footer_item)
            if current_coords:
                self.splash_canvas.coords(self.splash_footer_item, center_x, current_coords[1])

    def _animate_welcome_slide(self, current_offset=500, target_offset=0):
        if not hasattr(self, "splash_canvas") or not self.splash_canvas.winfo_exists():
            return
        if current_offset > target_offset:
            diff = current_offset - target_offset
            step = max(2, int(diff * 0.12))  # Smooth deceleration
            next_offset = current_offset - step
            if next_offset < target_offset:
                step = current_offset - target_offset
                next_offset = target_offset
            
            # Move the canvas items up by 'step'
            self.splash_canvas.move("welcome_items", 0, -step)
            
            # Update the button bg_color based on its new Y position to blend corners
            btn_current_y = 590 + next_offset
            bg_color = self._get_gradient_color(btn_current_y / 960.0)
            self.start_app_btn.configure(bg_color=bg_color)
            
            self.after(14, lambda: self._animate_welcome_slide(next_offset, target_offset))
        else:
            # Final alignment check
            pass

    def _on_start_clicked(self):
        # Destroy the welcome button widget to free resources
        if hasattr(self, "start_app_btn"):
            self.start_app_btn.destroy()
            
        # Clear all welcome canvas items
        self.splash_canvas.delete("welcome_items")
        
        # Create loading screen canvas items
        center_x = self.splash_canvas.winfo_width() / 2
        if center_x <= 1:
            center_x = 370
            
        # Horizontal logo inside the loading screen
        logo_path = resource_path("assets/header_logo.png")
        if os.path.exists(logo_path):
            try:
                img = Image.open(logo_path)
                width, height = img.size
                loading_logo_height = 90
                loading_logo_width = int(loading_logo_height * (width / height))
                img_resized = img.resize((loading_logo_width, loading_logo_height), Image.Resampling.LANCZOS)
                self.loading_photo = ImageTk.PhotoImage(img_resized)
                self.loading_logo_item = self.splash_canvas.create_image(
                    center_x, 390, image=self.loading_photo, anchor="center", tags="loading_items"
                )
            except Exception:
                pass
                
        # Sleek thin progress bar (Y = 480)
        pb_bg_color = self._get_gradient_color(480.0 / 960.0)
        self.splash_progress = ctk.CTkProgressBar(
            self.splash_canvas, width=280, height=4, 
            progress_color="#2563EB", fg_color="#1E293B", 
            corner_radius=2, bg_color=pb_bg_color
        )
        self.loading_pb_window = self.splash_canvas.create_window(
            center_x, 480, window=self.splash_progress, anchor="center", tags="loading_items"
        )
        self.splash_progress.set(0)
        
        # Splash status label (Y = 510)
        self.loading_status_item = self.splash_canvas.create_text(
            center_x, 510, text="Menginisialisasi sistem...", 
            font=("Segoe UI", 11), fill="#8F9CAE", anchor="center", tags="loading_items"
        )
        
        # Start the splash progress animation
        self._animate_splash()

    def _animate_splash(self, step=0):
        # Stages of loading with associated status messages
        loading_stages = [
            (0.15, "Menghubungkan pustaka PDF..."),
            (0.35, "Memuat modul SKU parser..."),
            (0.55, "Membaca konfigurasi settings..."),
            (0.75, "Menyiapkan antarmuka pengguna..."),
            (0.95, "Menyelesaikan pemuatan..."),
            (1.0, "Selesai!")
        ]
        
        if step < 50:
            # Calculate current progress fraction
            progress_val = step / 50.0
            self.splash_progress.set(progress_val)
            
            # Update status text based on progress
            current_stage_text = "Memuat..."
            for threshold, text in loading_stages:
                if progress_val <= threshold:
                    current_stage_text = text
                    break
            self.splash_canvas.itemconfig(self.loading_status_item, text=current_stage_text)
            
            # Call next step after a small randomized delay
            import random
            delay = random.randint(25, 45)
            self.after(delay, lambda: self._animate_splash(step + 1))
        else:
            # Finished loading, show dashboard
            self.splash_progress.set(1.0)
            self.splash_canvas.itemconfig(self.loading_status_item, text="Selesai!")
            self.after(300, self._reveal_main_dashboard)

    def _reveal_main_dashboard(self):
        # Destroy splash screen
        self.splash_container.destroy()
        
        # Grid the main dashboard container frame
        self.main_container.grid(row=0, column=0, sticky="nsew")
        
        # Start date/time ticker loop
        self._update_datetime_loop()

    def _setup_ui(self):
        # Configure root grid configuration for switching splash and main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # ---------------- SPLASH SCREEN CONTAINER ----------------
        self.splash_container = ctk.CTkFrame(self, fg_color="#0B0F19")
        self.splash_container.grid(row=0, column=0, sticky="nsew")
        
        # Canvas for animated gradient background
        self.splash_canvas = tk.Canvas(self.splash_container, highlightthickness=0, bd=0)
        self.splash_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.splash_canvas.bind("<Configure>", self._on_canvas_configure)
        
        # Splash footer at the bottom (layered on top of canvas)
        self.splash_footer_item = self.splash_canvas.create_text(
            370, 920, text=f"Versi {CURRENT_VERSION}  |  Developed by Akmal",
            font=("Segoe UI", 11), fill="#64748B", anchor="center"
        )
        
        # Draw Welcome Screen Canvas Items
        # Target positions centered around target Y = 450, shifted down by 500 initially
        # X = 370 is the horizontal center (for width=740)
        
        # 1. Vertical Logo
        welcome_logo_path = resource_path("assets/welcome_logo.png")
        if os.path.exists(welcome_logo_path):
            try:
                img = Image.open(welcome_logo_path)
                width, height = img.size
                logo_height = 175
                logo_width = int(logo_height * (width / height))
                img_resized = img.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                self.welcome_photo = ImageTk.PhotoImage(img_resized)
                self.welcome_logo_item = self.splash_canvas.create_image(
                    370, 330 + 500, image=self.welcome_photo, anchor="center", tags="welcome_items"
                )
            except Exception:
                self.welcome_logo_item = self.splash_canvas.create_text(
                    370, 330 + 500, text="📦  PackFlow", font=("Segoe UI", 36, "bold"), fill="#FFFFFF", anchor="center", tags="welcome_items"
                )
        else:
            self.welcome_logo_item = self.splash_canvas.create_text(
                370, 330 + 500, text="📦  PackFlow", font=("Segoe UI", 36, "bold"), fill="#FFFFFF", anchor="center", tags="welcome_items"
            )
            
        # 2. Horizontal Separator line (blue line, width=80)
        self.welcome_separator = self.splash_canvas.create_line(
            370 - 40, 465 + 500, 370 + 40, 465 + 500, fill="#2563EB", width=2, tags="welcome_items"
        )
        
        # 3. Detailed description text
        self.welcome_desc = self.splash_canvas.create_text(
            370, 510 + 500, text="Mempercepat proses pelabelan pesanan dengan lebih mudah, cepat, dan akurat",
            font=("Segoe UI", 13), fill="#8F9CAE", justify="center", width=320, anchor="center", tags="welcome_items"
        )
        
        # 4. Start button: "Mulai Sekarang" (placed in canvas window)
        self.start_app_btn = ctk.CTkButton(self.splash_canvas, 
                                           text="▶   Mulai Sekarang", 
                                           font=("Segoe UI", 14, "bold"), 
                                           height=44, 
                                           width=240, 
                                           corner_radius=8, 
                                           fg_color="#2563EB", 
                                           hover_color="#1D4ED8", 
                                           text_color="#FFFFFF", 
                                           command=self._on_start_clicked)
        # Background color at Y = 590 + 500 = 1090 is capped at bottom color (#111C30)
        self.start_app_btn.configure(bg_color=self._get_gradient_color(1.0))
        self.welcome_btn_window = self.splash_canvas.create_window(
            370, 590 + 500, window=self.start_app_btn, anchor="center", tags="welcome_items"
        )

        # ---------------- MAIN DASHBOARD CONTAINER ----------------
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        # Configure main_container grid
        self.main_container.grid_columnconfigure(0, weight=1)
        self.main_container.grid_rowconfigure(0, weight=0) # Header
        self.main_container.grid_rowconfigure(1, weight=0) # Inputs Card
        self.main_container.grid_rowconfigure(2, weight=0) # Process Button
        self.main_container.grid_rowconfigure(3, weight=0) # Status Proses Card
        self.main_container.grid_rowconfigure(4, weight=1) # Hasil Scan Table Card
        self.main_container.grid_rowconfigure(5, weight=0) # Footer
        
        # ---------------- GUIDE CONTAINER (Initially hidden) ----------------
        self.guide_container = ctk.CTkFrame(self, fg_color="transparent")
        self.guide_container.grid_columnconfigure(0, weight=1)
        self.guide_container.grid_rowconfigure(1, weight=1)
        
        self._setup_guide_view()
        
        # ---------------- HEADER SECTION ----------------
        header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
        
        # Configure columns: Column 1 is a spacer with weight=1, pushing Column 2 to the right
        header_frame.grid_columnconfigure(0, weight=0)
        header_frame.grid_columnconfigure(1, weight=1)
        header_frame.grid_columnconfigure(2, weight=0)
        
        # Logo & Name (Using the horizontal branding logo supporting dynamic Light/Dark mode)
        logo_path_dark = resource_path("assets/header_logo.png")
        logo_path_light = resource_path("assets/header_logo_light.png")
        has_logo = False
        if os.path.exists(logo_path_dark):
            try:
                img_dark = Image.open(logo_path_dark)
                if os.path.exists(logo_path_light):
                    img_light = Image.open(logo_path_light)
                    if img_light.size != img_dark.size:
                        img_light = img_light.resize(img_dark.size, Image.Resampling.LANCZOS)
                else:
                    img_light = img_dark
                width, height = img_dark.size
                logo_height = 60
                logo_width = int(logo_height * (width / height))
                self.logo_img = ctk.CTkImage(light_image=img_light, dark_image=img_dark, size=(logo_width, logo_height))
                logo_label = ctk.CTkLabel(header_frame, image=self.logo_img, text="")
                logo_label.grid(row=0, column=0, sticky="w")
                has_logo = True
            except Exception:
                pass
        
        if not has_logo:
            # Fallback to text + emoji if image not found
            logo_label = ctk.CTkLabel(header_frame, text="📦  PackFlow", font=("Segoe UI", 26, "bold"), text_color=("#1F2937", "#FFFFFF"))
            logo_label.grid(row=0, column=0, sticky="w")
            
            subtitle_label = ctk.CTkLabel(header_frame, text="Otomatisasi Pelabelan Resi Pesanan", font=("Segoe UI", 12), text_color=("#4B5563", "#8F9CAE"))
            subtitle_label.grid(row=1, column=0, sticky="w", pady=(4, 0))
        
        # Right aligned buttons (Version badge and Settings gear ⚙️)
        right_header_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_header_frame.grid(row=0, column=2, rowspan=2, sticky="ne")
        
        version_badge = ctk.CTkLabel(right_header_frame, text=f"v{CURRENT_VERSION}", font=("Segoe UI", 11, "bold"), 
                                     fg_color=("#E5E7EB", "#1E293B"), text_color="#3B82F6", corner_radius=6, width=60, height=24,
                                     cursor="hand2")
        version_badge.pack(side="left", padx=(0, 10), pady=4)
        version_badge.bind("<Button-1>", lambda e: self._show_about_dialog())
        
        # Theme switcher (Solo icon button in the middle)
        self._create_theme_toggle(right_header_frame)
        
        # Settings button (on the far right)
        settings_btn = ctk.CTkButton(right_header_frame, text="", image=self.settings_icon, width=32, height=28,
                                     fg_color=("#E5E7EB", "#1E293B"), hover_color=("#D1D5DB", "#334155"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6,
                                     command=self._open_settings)
        settings_btn.pack(side="left", pady=2)
        
        # ---------------- INPUT CARD ----------------
        input_card = ctk.CTkFrame(self.main_container, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=10)
        input_card.grid(row=1, column=0, padx=24, pady=10, sticky="ew")
        input_card.grid_columnconfigure(1, weight=1)
        
        # Section Header
        ctk.CTkLabel(input_card, text="  INPUT", image=self.input_icon, compound="left", font=("Segoe UI", 13, "bold"), text_color="#3B82F6").grid(row=0, column=0, columnspan=3, padx=16, pady=(12, 6), sticky="w")
        
        # PDF/URL field
        ctk.CTkLabel(input_card, text="File PDF / URL:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.file_entry = ctk.CTkEntry(input_card, placeholder_text="Pilih file .pdf atau paste link URL di sini...", font=("Segoe UI", 12),
                                       fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.file_entry.grid(row=1, column=1, padx=10, pady=6, sticky="ew")
        self.browse_file_btn = ctk.CTkButton(input_card, text="  Browse", image=self.file_icon, compound="left", font=("Segoe UI", 12), width=95, height=30,
                                             fg_color=("#E5E7EB", "#1E293B"), hover_color=("#D1D5DB", "#334155"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6,
                                             command=self._browse_file)
        self.browse_file_btn.grid(row=1, column=2, padx=16, pady=6)
        
        # Folder Output field
        ctk.CTkLabel(input_card, text="Folder Output:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=2, column=0, padx=16, pady=6, sticky="w")
        self.folder_entry = ctk.CTkEntry(input_card, placeholder_text="Folder penyimpanan...", font=("Segoe UI", 12),
                                         fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.folder_entry.grid(row=2, column=1, padx=10, pady=6, sticky="ew")
        
        # Pre-fill last saved output folder from settings
        saved_folder = self.settings.get("last_output_folder", "")
        if saved_folder:
            self.folder_entry.insert(0, saved_folder)
        self.browse_folder_btn = ctk.CTkButton(input_card, text="  Browse", image=self.folder_icon, compound="left", font=("Segoe UI", 12), width=95, height=30,
                                               fg_color=("#E5E7EB", "#1E293B"), hover_color=("#D1D5DB", "#334155"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6,
                                               command=self._browse_folder)
        self.browse_folder_btn.grid(row=2, column=2, padx=16, pady=6)
        
        # Thin separator
        sep = ctk.CTkFrame(input_card, height=1, fg_color=("#E5E7EB", "#1F2937"))
        sep.grid(row=3, column=0, columnspan=3, padx=16, pady=(6, 0), sticky="ew")
        
        # Options row: Marketplace + Split PDF (symmetrical mini-cards)
        options_frame = ctk.CTkFrame(input_card, fg_color="transparent")
        options_frame.grid(row=4, column=0, columnspan=3, padx=16, pady=(8, 12), sticky="ew")
        options_frame.grid_columnconfigure(0, weight=1)
        options_frame.grid_columnconfigure(1, weight=1)
        
        # --- LEFT: MARKETPLACE CARD ---
        market_card = ctk.CTkFrame(options_frame, fg_color=("#F9FAFB", "#0F1629"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=8)
        market_card.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        market_inner = ctk.CTkFrame(market_card, fg_color="transparent")
        market_inner.pack(fill="both", expand=True, padx=14, pady=12)
        
        # Header (Icon + Text side-by-side)
        market_header = ctk.CTkFrame(market_inner, fg_color="transparent")
        market_header.pack(fill="x", anchor="w")

        self.market_logo_label = ctk.CTkLabel(market_header, text="")
        self.market_logo_label.pack(side="left", padx=(0, 10))
        
        market_text_frame = ctk.CTkFrame(market_header, fg_color="transparent")
        market_text_frame.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(market_text_frame, text="Marketplace", font=("Segoe UI", 13, "bold"), text_color=("#1F2937", "#FFFFFF"), pady=0).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(market_text_frame, text="Sumber data resi", font=("Segoe UI", 11), text_color=("#6B7280", "#9CA3AF"), pady=0).grid(row=1, column=0, sticky="w")
        
        # Dropdown
        self.market_option = ctk.CTkOptionMenu(
            market_inner, 
            values=["Shopee", "TikTok", "Lazada"], 
            font=("Segoe UI", 12),
            height=36, 
            corner_radius=6, 
            fg_color=("#FFFFFF", "#1E293B"),
            button_color=("#E5E7EB", "#374151"),
            button_hover_color=("#D1D5DB", "#475569"),
            text_color=("#1F2937", "#FFFFFF"),
            dropdown_fg_color=("#FFFFFF", "#1E293B"),
            dropdown_hover_color=("#F3F4F6", "#334155"),
            dropdown_text_color=("#1F2937", "#FFFFFF"),
            dropdown_font=("Segoe UI", 12),
            command=self._on_option_changed
        )
        self.market_option.pack(fill="x", pady=(12, 0))
        self.market_option.set(self.settings.get("marketplace_mode", "Shopee"))
        
        # --- RIGHT: SPLIT PDF CARD ---
        split_card = ctk.CTkFrame(options_frame, fg_color=("#F9FAFB", "#0F1629"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=8)
        split_card.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        split_inner = ctk.CTkFrame(split_card, fg_color="transparent")
        split_inner.pack(fill="both", expand=True, padx=14, pady=12)
        
        # Header (Icon + Text side-by-side)
        split_header = ctk.CTkFrame(split_inner, fg_color="transparent")
        split_header.pack(fill="x", anchor="w")
        
        ctk.CTkLabel(split_header, text="", image=self.files_blue_icon).pack(side="left", padx=(0, 10))
        
        split_text_frame = ctk.CTkFrame(split_header, fg_color="transparent")
        split_text_frame.pack(side="left", fill="both", expand=True)
        
        ctk.CTkLabel(split_text_frame, text="Simpan Per Gudang", font=("Segoe UI", 13, "bold"), text_color=("#1F2937", "#FFFFFF")).pack(anchor="w")
        ctk.CTkLabel(split_text_frame, text="Pisahkan file per Gudang", font=("Segoe UI", 11), text_color=("#6B7280", "#9CA3AF")).pack(anchor="w")
        
        # Toggle Switch
        self.split_pdf_var = ctk.BooleanVar(value=self.settings.get("split_pdf", False))
        self.split_pdf_switch = ctk.CTkSwitch(
            split_inner, 
            text="Aktifkan Pemisahan", 
            variable=self.split_pdf_var, 
            font=("Segoe UI", 12),
            height=36,
            progress_color="#3B82F6",
            fg_color=("#D1D5DB", "#374151"),
            button_color=("#FFFFFF", "#9CA3AF"),

            button_hover_color=("#E5E7EB", "#D1D5DB"),
            text_color=("#1F2937", "#FFFFFF"),
            command=self._on_option_changed
        )
        self.split_pdf_switch.pack(anchor="w", pady=(12, 0))
        
        # ---------------- START PROCESS BUTTON ----------------
        self.start_btn = ctk.CTkButton(self.main_container, text="  START PROCESS", image=self.play_icon, compound="left", font=("Segoe UI", 14, "bold"), height=42, corner_radius=8,
                                       fg_color="#2563EB", hover_color="#1D4ED8", text_color="#FFFFFF",
                                       command=self._start_process)
        self.start_btn.grid(row=2, column=0, padx=24, pady=10, sticky="ew")
        
        # ---------------- LOADING INDICATOR (REPLACES STATUS CARD) ----------------
        self.loading_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.loading_container.grid(row=3, column=0, padx=24, pady=5, sticky="ew")
        
        self.main_spinner_label = ctk.CTkLabel(self.loading_container, text="", image=self.loading_icon_static)
        self.main_spinner_label.pack(side="left", padx=(10, 15))
        
        status_text_frame = ctk.CTkFrame(self.loading_container, fg_color="transparent")
        status_text_frame.pack(side="left", fill="both", expand=True)
        
        self.status_label = ctk.CTkLabel(status_text_frame, textvariable=self.status_bar_str, font=("Segoe UI", 12, "bold"), text_color=("#1F2937", "#3B82F6"))
        self.status_label.pack(anchor="w")
        
        # Sleek thin progress bar
        self.smooth_progress_bar = ctk.CTkProgressBar(status_text_frame, height=4, width=350, corner_radius=2,
                                                       fg_color=("#E5E7EB", "#1F2937"), progress_color="#3B82F6")
        self.smooth_progress_bar.pack(anchor="w", pady=(2, 2))
        self.smooth_progress_bar.set(0)
        
        self.progress_detail_label = ctk.CTkLabel(status_text_frame, textvariable=self.progress_text_str, font=("Segoe UI", 11), text_color=("#4B5563", "#8F9CAE"))
        self.progress_detail_label.pack(anchor="w")
        
        # Hide loading indicator initially
        self.loading_container.grid_remove()
        
        # ---------------- HASIL SCAN TABLE CARD ----------------
        results_card = ctk.CTkFrame(self.main_container, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=10)
        results_card.grid(row=4, column=0, padx=24, pady=(10, 15), sticky="nsew")
        results_card.grid_columnconfigure(0, weight=1)
        results_card.grid_rowconfigure(2, weight=1)
        
        # Header title
        self.table_title_label = ctk.CTkLabel(results_card, textvariable=self.hasil_scan_title_str, font=("Segoe UI", 13, "bold"), text_color="#3B82F6")
        self.table_title_label.grid(row=0, column=0, padx=16, pady=(12, 8), sticky="w")
        
        # Restore "Salin Semua" button in the table card header
        self.copy_all_btn = ctk.CTkButton(results_card, text="  Salin Semua", image=self.copy_icon, compound="left", font=("Segoe UI", 11, "bold"), width=120, height=26,
                                          fg_color=("#E5E7EB", "#1E293B"), border_width=1, border_color=("#D1D5DB", "#374151"), hover_color=("#D1D5DB", "#334155"), text_color="#3B82F6", corner_radius=6,
                                          command=self._copy_all_resi)
        self.copy_all_btn.grid(row=0, column=0, padx=16, pady=(12, 8), sticky="e")
        
        # Table Header Row
        header_table_frame = ctk.CTkFrame(results_card, fg_color=("#F3F4F6", "#1E293B"), height=32, corner_radius=4)
        header_table_frame.grid(row=1, column=0, padx=16, pady=(0, 5), sticky="ew")
        header_table_frame.grid_columnconfigure(0, weight=0, minsize=40)  # No.
        header_table_frame.grid_columnconfigure(1, weight=1)              # Data Hasil Scan
        header_table_frame.grid_columnconfigure(2, weight=0, minsize=150) # Action
        
        ctk.CTkLabel(header_table_frame, text="No.", font=("Segoe UI", 11, "bold"), text_color=("#4B5563", "#8F9CAE")).grid(row=0, column=0, sticky="w", padx=10)
        ctk.CTkLabel(header_table_frame, text="Data Hasil Scan (Format: Nomor, Qty, SKU)", font=("Segoe UI", 11, "bold"), text_color=("#4B5563", "#8F9CAE")).grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(header_table_frame, text="Action", font=("Segoe UI", 11, "bold"), text_color=("#4B5563", "#8F9CAE")).grid(row=0, column=2, sticky="w", padx=10)
        
        # Scrollable rows frame (transparent background to match card)
        self.results_frame = ctk.CTkScrollableFrame(results_card, fg_color="transparent", corner_radius=0)
        self.results_frame.grid(row=2, column=0, padx=16, pady=(0, 10), sticky="nsew")
        self.results_frame.grid_columnconfigure(0, weight=1)
        
        # ---------------- FOOTER SECTION ----------------
        footer_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        footer_frame.grid(row=5, column=0, padx=24, pady=(0, 12), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)
        
        # Right credit & date
        credit_label = ctk.CTkLabel(footer_frame, text="developed by Akmal", font=("Segoe UI", 11, "italic"), text_color=("#4B5563", "#8F9CAE"))
        credit_label.pack(side="right", padx=(10, 5))
        
        sep_label = ctk.CTkLabel(footer_frame, text="|", font=("Segoe UI", 11), text_color=("#D1D5DB", "#1F2937"))
        sep_label.pack(side="right", padx=10)
        
        self.date_label = ctk.CTkLabel(footer_frame, textvariable=self.datetime_str, font=("Segoe UI", 11), text_color=("#4B5563", "#8F9CAE"))
        self.date_label.pack(side="right", padx=5)
        
        # Storage
        self.result_rows = []
        self.all_resi = []
        
        # Initialize marketplace status
        self._update_marketplace_status()

    def _browse_file(self):
        file = filedialog.askopenfilename(filetypes=[("PDF files", "*.pdf")])
        if file:
            self.file_entry.delete(0, "end")
            self.file_entry.insert(0, file)

    def _browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder_entry.delete(0, "end")
            self.folder_entry.insert(0, folder)
            # Persist last output folder in settings
            self.settings["last_output_folder"] = folder
            self._save_settings()
            
    def _open_settings(self):
        from ui.settings_window import SettingsFrame
        self.main_container.grid_forget()
        self.settings_frame = SettingsFrame(self, self.settings_path, self._update_settings, self._close_settings, current_settings=self.settings)
        self.settings_frame.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
    def _close_settings(self):
        if hasattr(self, "settings_frame") and self.settings_frame:
            self.settings_frame.destroy()
            self.settings_frame = None
        self.main_container.grid(row=0, column=0, sticky="nsew")
        
    def _update_settings(self, new_settings):
        self.settings = new_settings

    def _save_settings(self):
        config_dir = os.path.dirname(self.settings_path)
        if config_dir and not os.path.exists(config_dir):
            os.makedirs(config_dir)
        with open(self.settings_path, 'w') as f:
            json.dump(self.settings, f, indent=4)

    def _on_option_changed(self, *args):
        """Auto-save marketplace and split_pdf when changed from the dashboard."""
        raw_val = self.market_option.get()
        selected_market = raw_val.split()[-1] if " " in raw_val else raw_val
        self.settings["marketplace_mode"] = selected_market
        self.settings["split_pdf"] = self.split_pdf_var.get()
        self._save_settings()
        self._update_marketplace_status()

    def _update_marketplace_status(self):
        raw_val = self.market_option.get()
        selected_market = raw_val.split()[-1] if " " in raw_val else raw_val
        
        # Clear any existing placeholder
        if hasattr(self, "_coming_soon_label") and self._coming_soon_label:
            try:
                self._coming_soon_label.destroy()
            except Exception:
                pass
            self._coming_soon_label = None
            
        # Update Marketplace Logo
        if selected_market == "Shopee":
            self.market_logo_label.configure(image=self.shopee_logo)
        elif selected_market == "TikTok":
            self.market_logo_label.configure(image=self.tiktok_logo)
        elif selected_market == "Lazada":
            self.market_logo_label.configure(image=self.lazada_logo)
            
        # Enable Start Button
        self.start_btn.configure(state="normal", text="  START PROCESS")

    def _create_theme_toggle(self, parent_frame):
        # Solo theme button matching the settings button style/size (packed with right padding)
        self.theme_btn = ctk.CTkButton(parent_frame, text="", width=32, height=28, corner_radius=6,
                                       command=self._toggle_theme_click)
        self.theme_btn.pack(side="left", padx=(0, 10), pady=2)
        
        # Initial draw based on current settings
        current_theme = self.settings.get("theme", "dark")
        self._update_theme_toggle_ui(current_theme)

    def _update_theme_toggle_ui(self, theme_name):
        if theme_name == "light":
            self.theme_btn.configure(
                fg_color="#1E293B",
                hover_color="#0F172A",
                image=self.sun_icon
            )
        else:
            self.theme_btn.configure(
                fg_color="#F8FAFC",
                hover_color="#E2E8F0",
                image=self.moon_icon
            )

    def _toggle_theme_click(self):
        # Prevent concurrent transitions
        if getattr(self, "_theme_transitioning", False):
            return
        self._theme_transitioning = True
        
        current_theme = self.settings.get("theme", "dark")
        new_theme = "light" if current_theme == "dark" else "dark"
        
        steps = 8
        delay = 12  # ms (total fade time ~100ms each way)
        
        def fade_out(step=0):
            if step < steps:
                # Interpolate alpha from 1.0 down to 0.3
                alpha = 1.0 - (0.7 * (step / steps))
                self.attributes("-alpha", alpha)
                self.after(delay, lambda: fade_out(step + 1))
            else:
                # Apply theme change at the lowest opacity
                ctk.set_appearance_mode(new_theme)
                self.settings["theme"] = new_theme
                self._save_settings()
                self._update_theme_toggle_ui(new_theme)
                
                # Start fade in
                fade_in(0)
                
        def fade_in(step=0):
            if step <= steps:
                # Interpolate alpha from 0.3 up to 1.0
                alpha = 0.3 + (0.7 * (step / steps))
                self.attributes("-alpha", alpha)
                self.after(delay, lambda: fade_in(step + 1))
            else:
                self.attributes("-alpha", 1.0)
                self._theme_transitioning = False
                
        fade_out(0)

    def _add_result_row(self, text, resi=None, folder=None, has_kendala=False, kendala_reason="", file_path=None, idx=1, sku="", qty="-"):
        # Set colors based on kendala
        if has_kendala:
            bg_color = ("#FEE2E2", "#2D1518")      # Crimson dark red / light red
            border_color = ("#FCA5A5", "#7F1D1D")  # Dark red border / light red border
            text_color = ("#991B1B", "#FCA5A5")    # Pinkish red text / dark red text
            idx_icon = None  # Will use warning_icon image
        else:
            # Alternating striped row colors
            bg_color = (("#E5E7EB", "#16223F") if idx % 2 == 0 else ("#F9FAFB", "#111C33"))
            border_color = ("#E5E7EB", "#1F2937")
            text_color = ("#1F2937", "#FFFFFF")
            idx_icon = str(idx)

        row_container = ctk.CTkFrame(self.results_frame, fg_color=bg_color, border_width=1, border_color=border_color, height=44, corner_radius=6)
        row_container.pack(fill="x", pady=3)
        row_container.pack_propagate(False) # Keep fixed row height
        
        # Grid columns
        row_container.grid_columnconfigure(0, weight=0, minsize=40)  # No.
        row_container.grid_columnconfigure(1, weight=1)              # Selectable text entry
        row_container.grid_columnconfigure(2, weight=0, minsize=150) # Action

        # Column 0: Index / Icon
        if has_kendala:
            ctk.CTkLabel(row_container, text="", image=self.warning_icon, font=("Segoe UI", 11, "bold"), text_color=text_color).grid(row=0, column=0, padx=10, pady=8)
        else:
            ctk.CTkLabel(row_container, text=idx_icon, font=("Segoe UI", 11, "bold"), text_color=text_color).grid(row=0, column=0, padx=10, pady=8)
        
        # Column 1: Selectable text entry (flat/borderless style)
        text_entry = ctk.CTkEntry(row_container, height=30, font=("Consolas", 11),
                                  fg_color=bg_color, border_width=0, text_color=text_color)
        text_entry.insert(0, text)
        text_entry.configure(state="readonly")
        text_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=6)
        
        # Column 2: Buttons (Empty if Simpan Per Gudang is active)
        btn_frame = ctk.CTkFrame(row_container, fg_color="transparent")
        btn_frame.grid(row=0, column=2, sticky="e", padx=10, pady=4)
        
        is_per_gudang = self.settings.get("split_pdf")
        
        if not is_per_gudang:
            # Only Copy button when bulk mode
            copy_btn = ctk.CTkButton(btn_frame, text="", image=self.copy_icon, width=34, height=30,
                                     fg_color=("#F3F4F6", "#1E293B"), border_width=1, border_color=("#D1D5DB", "#374151"), hover_color=("#E5E7EB", "#334155"), corner_radius=6,
                                     command=lambda: self._copy_to_clipboard(text))
            copy_btn.pack(side="left", padx=2)
        else:
            # Only Copy button when split_pdf is not active
            copy_btn = ctk.CTkButton(btn_frame, text="", image=self.copy_icon, width=34, height=30,
                                     fg_color=("#F3F4F6", "#1E293B"), border_width=1, border_color=("#D1D5DB", "#374151"), hover_color=("#E5E7EB", "#334155"), corner_radius=6,
                                     command=lambda: self._copy_to_clipboard(text))
            copy_btn.pack(side="left", padx=2)
            
        self.result_rows.append(row_container)

    def _add_city_header(self, city_name, resi_list, file_path=None):
        """Add a header row for a city with Telegram, Copy, and Open buttons."""
        header_container = ctk.CTkFrame(self.results_frame, fg_color=("#F1F5F9", "#1E293B"), height=36, corner_radius=6)
        header_container.pack(fill="x", pady=(12, 4))
        header_container.pack_propagate(False)
        
        city_label = ctk.CTkLabel(header_container, text=city_name.upper(), font=("Segoe UI", 12, "bold"), text_color="#3B82F6")
        city_label.pack(side="left", padx=15)
        
        # Action Button Container
        btn_frame = ctk.CTkFrame(header_container, fg_color="transparent")
        btn_frame.pack(side="right", padx=10)
        
        if file_path:
            # 1. Telegram Button
            tg_btn = ctk.CTkButton(btn_frame, text="", image=self.send_icon, width=32, height=28,
                                   fg_color=("#EFF6FF", "#1E293B"), border_width=1, border_color=("#BFDBFE", "#1D4ED8"), hover_color=("#DBEAFE", "#1E40AF"), corner_radius=5)
            # Patch command to pass button reference
            tg_btn.configure(command=lambda b=tg_btn, fp=file_path: self._copy_file_to_clipboard_with_feedback(b, fp))
            tg_btn.pack(side="left", padx=2)
            
        # 2. Copy All in City Button
        copy_text = "\n".join(resi_list)
        copy_btn = ctk.CTkButton(btn_frame, text="", image=self.copy_icon, width=32, height=28,
                                 fg_color=("#F3F4F6", "#1E293B"), border_width=1, border_color=("#D1D5DB", "#374151"), hover_color=("#E5E7EB", "#334155"), corner_radius=5,
                                 command=lambda: self._copy_to_clipboard(copy_text))
        copy_btn.pack(side="left", padx=2)
        
        if file_path:
            # 3. Open PDF Button
            open_btn = ctk.CTkButton(btn_frame, text="", image=self.open_file_icon, width=32, height=28,
                                     fg_color=("#ECFDF5", "#1E293B"), border_width=1, border_color=("#A7F3D0", "#065F46"), hover_color=("#D1FAE5", "#064E3B"), corner_radius=5,
                                     command=lambda: self._open_specific_file(file_path))
            open_btn.pack(side="left", padx=2)
        
        self.result_rows.append(header_container)

    def _open_specific_file(self, path):
        if os.path.exists(path):
            os.startfile(path)
        else:
            self.status_bar_str.set("Status: File belum ada / proses belum selesai")
            self.status_label.configure(text_color="#EF4444")

    def _copy_file_to_clipboard(self, path):
        if os.path.exists(path):
            try:
                # Use PowerShell to copy the actual file object to clipboard
                # This allows Ctrl+V in Telegram/WhatsApp/Explorer
                cmd = f'powershell -command "Set-Clipboard -Path \'{os.path.abspath(path)}\'"'
                os.system(cmd)
                self.status_bar_str.set("Status: File disalin! Paste (Ctrl+V) di Telegram.")
                self.status_label.configure(text_color="#10B981")
            except Exception as e:
                self.status_bar_str.set(f"Status: Gagal menyalin file - {str(e)}")
                self.status_label.configure(text_color="#EF4444")
        else:
            self.status_bar_str.set("Status: File tidak ditemukan")
            self.status_label.configure(text_color="#EF4444")

    def _copy_file_to_clipboard_with_feedback(self, btn, path):
        """Copy file to clipboard and swap button icon to filled version permanently."""
        self._copy_file_to_clipboard(path)
        if btn and os.path.exists(path):
            try:
                btn.configure(image=self.send_filled_icon)
            except Exception:
                pass

    def _show_about_dialog(self):
        """Show About dialog when version badge is clicked."""
        about_window = ctk.CTkToplevel(self)
        about_window.title("Tentang PackFlow")
        about_window.geometry("400x320")
        about_window.resizable(False, False)
        about_window.transient(self)
        about_window.grab_set()
        
        # Center on parent window
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 160
        about_window.geometry(f"+{x}+{y}")
        
        # Set window icon
        icon_path_ico = resource_path("assets/icon.ico")
        if os.path.exists(icon_path_ico) and sys.platform.startswith("win"):
            try:
                about_window.after(200, lambda: about_window.iconbitmap(icon_path_ico))
            except Exception:
                pass
        
        # Content frame
        content = ctk.CTkFrame(about_window, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=20)
        
        # App Logo
        logo_path = resource_path("assets/icon.png")
        if os.path.exists(logo_path):
            try:
                logo_img = ctk.CTkImage(
                    light_image=Image.open(logo_path),
                    dark_image=Image.open(logo_path),
                    size=(64, 64)
                )
                ctk.CTkLabel(content, text="", image=logo_img).pack(pady=(10, 8))
            except Exception:
                pass
        
        # App Name
        ctk.CTkLabel(content, text="PackFlow", font=("Segoe UI", 22, "bold"), text_color=("#1F2937", "#FFFFFF")).pack()
        
        # Version
        ctk.CTkLabel(content, text=f"Versi {CURRENT_VERSION}", font=("Segoe UI", 13), text_color="#3B82F6").pack(pady=(2, 8))
        
        # Description
        ctk.CTkLabel(content, text="Otomatisasi Pelabelan Resi Pesanan\nuntuk Marketplace Shopee, Tiktok & Lazada", 
                     font=("Segoe UI", 12), text_color=("#4B5563", "#9CA3AF"), justify="center").pack(pady=(0, 6))
        
        # Guide Button
        ctk.CTkButton(content, text="  Panduan Penggunaan", image=self.info_icon, compound="left", font=("Segoe UI", 12, "bold"), height=36,
                      fg_color=("#E5E7EB", "#1F2937"), border_width=1, border_color=("#D1D5DB", "#374151"), 
                      hover_color=("#D1D5DB", "#334155"), text_color="#3B82F6", corner_radius=8,
                      command=lambda: [about_window.destroy(), self._show_guide_view()]).pack(pady=(8, 12))
        
        # Separator
        ctk.CTkFrame(content, height=1, fg_color=("#E5E7EB", "#1F2937")).pack(fill="x", padx=20, pady=4)
        
        # Credits
        ctk.CTkLabel(content, text="Developed by Akmal", font=("Segoe UI", 11, "italic"), text_color=("#6B7280", "#8F9CAE")).pack(pady=(8, 2))
        ctk.CTkLabel(content, text="© 2026 All rights reserved", font=("Segoe UI", 10), text_color=("#9CA3AF", "#6B7280")).pack()
        
        # Close button
        ctk.CTkButton(content, text="Tutup", font=("Segoe UI", 12, "bold"), width=100, height=32,
                      fg_color="#2563EB", hover_color="#1D4ED8", text_color="#FFFFFF", corner_radius=6,
                      command=about_window.destroy).pack(pady=(12, 0))

    def _setup_guide_view(self):
        """Build the internal guide view content."""
        # --- Header with Back Button ---
        guide_header = ctk.CTkFrame(self.guide_container, fg_color="transparent")
        guide_header.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
        
        back_btn = ctk.CTkButton(guide_header, text="", image=self.arrow_left_icon, width=32, height=32,
                                 fg_color=("#E5E7EB", "#1E293B"), hover_color=("#D1D5DB", "#334155"), corner_radius=8,
                                 command=self._hide_guide_view)
        back_btn.pack(side="left")
        
        ctk.CTkLabel(guide_header, text="Panduan Aplikasi", font=("Segoe UI", 20, "bold"), text_color=("#111827", "#FFFFFF")).pack(side="left", padx=15)

        # --- Content Scrollable ---
        scroll = ctk.CTkScrollableFrame(self.guide_container, fg_color="transparent")
        scroll.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 10))

        def add_section(title, content_list):
            s_frame = ctk.CTkFrame(scroll, fg_color=("#FFFFFF", "#1E293B"), corner_radius=12, border_width=1, border_color=("#E5E7EB", "#334155"))
            s_frame.pack(fill="x", pady=10, padx=5)
            
            ctk.CTkLabel(s_frame, text=title, font=("Segoe UI", 16, "bold"), text_color="#3B82F6").pack(anchor="w", padx=20, pady=(15, 8))
            
            for item in content_list:
                item_frame = ctk.CTkFrame(s_frame, fg_color="transparent")
                item_frame.pack(fill="x", padx=20, pady=4)
                
                if ":" in item:
                    bold_part, reg_part = item.split(":", 1)
                    ctk.CTkLabel(item_frame, text="• ", font=("Segoe UI", 13, "bold"), text_color="#3B82F6").pack(side="left")
                    ctk.CTkLabel(item_frame, text=bold_part + ":", font=("Segoe UI", 12, "bold"), text_color=("#1F2937", "#FFFFFF")).pack(side="left")
                    ctk.CTkLabel(item_frame, text=reg_part, font=("Segoe UI", 12), text_color=("#4B5563", "#8F9CAE"), wraplength=480, justify="left").pack(side="left", padx=2)
                else:
                    ctk.CTkLabel(item_frame, text="• " + item, font=("Segoe UI", 12), text_color=("#4B5563", "#8F9CAE"), wraplength=500, justify="left").pack(anchor="w")

        add_section("🚀 Alur Kerja Utama", [
            "Marketplace: Pilih Shopee, TikTok, atau Lazada sesuai sumber file PDF Anda.",
            "Input: Klik tombol folder untuk memilih file PDF atau tempelkan URL Marketplace.",
            "Output: Tentukan folder penyimpanan hasil label.",
            "Start: Klik tombol biru untuk memulai otomatisasi ekstraksi SKU."
        ])

        add_section("💎 Fitur Unggulan", [
            "Simpan Per Gudang: Memisahkan label menjadi PDF berbeda berdasarkan Kota pengirim.",
            "Smart SKU Extraction: Mendeteksi SKU, Qty, dan Variasi secara otomatis.",
            "Whitelist SKU: Memfilter SKU sampah dan hanya memproses yang Anda daftarkan.",
            "Auto-Naming: Penamaan file otomatis berdasarkan Kota, Tanggal, atau Resi."
        ])

        add_section("📑 Fungsi Tombol Hasil", [
            "Icon Telegram: Salin file PDF ke clipboard untuk langsung di-Paste ke WA/Telegram.",
            "Icon Salin (Header): Menyalin semua daftar Nomor Resi dalam satu grup kota.",
            "Icon Salin (Baris): Menyalin detail nomor resi dan SKU untuk pesanan tersebut.",
            "Icon Buka: Membuka berkas PDF hasil olahan di aplikasi PDF viewer Anda."
        ])

        add_section("💡 Tips & Troubleshooting", [
            "Gagal Baca PDF: Pastikan PDF asli dari Seller Center (Bukan hasil scan).",
            "Matahari/Bulan: Klik icon di pojok atas untuk mengganti tema Gelap/Terang."
        ])

    def _show_guide_view(self):
        """Switch from dashboard to guide view."""
        self.main_container.grid_remove()
        self.guide_container.grid(row=0, column=0, sticky="nsew")

    def _hide_guide_view(self):
        """Switch from guide view back to dashboard."""
        self.guide_container.grid_remove()
        self.main_container.grid(row=0, column=0, sticky="nsew")


    def _copy_to_clipboard(self, text):
        self.status_bar_str.set(f"Status: Berhasil disalin! ({text[:15]}...)")
        self.status_label.configure(text_color="#10B981")
        self.clipboard_clear()
        self.clipboard_append(text)
        self.update() # Ensure clipboard updates correctly in Windows

    def _copy_all_resi(self):
        if not self.all_resi:
            self.status_bar_str.set("Status: Tidak ada resi untuk disalin.")
            self.status_label.configure(text_color="#EF4444")
            return
        
        joined_resi = "\n".join(self.all_resi)
        self.clipboard_clear()
        self.clipboard_append(joined_resi)
        self.update()
        self.status_bar_str.set(f"Status: {len(self.all_resi)} Resi berhasil disalin!")
        self.status_label.configure(text_color="#10B981")

    def _update_progress(self, value, percent_str, text_str):
        # Update the new sleek progress bar
        if hasattr(self, "smooth_progress_bar"):
            self.smooth_progress_bar.set(value)
        
        self.progress_percent_str.set(percent_str)
        self.progress_text_str.set(text_str)
        # Append percent to status bar for more visibility
        self.status_bar_str.set(f"Status: {text_str} ({percent_str})")

    def _create_loading_animation(self):
        """Create frames for the rotating loading spinner."""
        try:
            # Try to load custom loader, fallback to download if corrupt or missing
            base_path = resource_path("assets/loader.png")
            try:
                if os.path.exists(base_path):
                    img = Image.open(base_path)
                else:
                    raise FileNotFoundError
            except Exception:
                # Fallback: Try to download a professional circular spinner if allowed/possible
                try:
                    import urllib.request
                    spinner_url = "https://img.icons8.com/?size=64&id=11326&format=png&color=228BE6"
                    os.makedirs(os.path.dirname(base_path), exist_ok=True)
                    urllib.request.urlretrieve(spinner_url, base_path)
                    img = Image.open(base_path)
                except Exception:
                    # Final fallback to existing activity icon
                    base_path = resource_path("assets/lucide/download_blue.png")
                    img = Image.open(base_path)
            
            self.loading_frames = []
            for i in range(0, 360, 45): # 8 frames (45 deg apart)
                rotated = img.rotate(-i)
                self.loading_frames.append(ctk.CTkImage(light_image=rotated, dark_image=rotated, size=(24, 24)))
        except Exception as e:
            print(f"Error loading animation: {e}")

    def _animate_loading_loop(self):
        """Main animation loop for the spinner."""
        if not self.is_loading:
            # Restore start button icon
            self.start_btn.configure(image=self.play_icon)
            return
            
        if self.loading_frames:
            frame = self.loading_frames[self.current_loading_frame]
            self.current_loading_frame = (self.current_loading_frame + 1) % len(self.loading_frames)
            
            # Update the spinner in the main body
            if hasattr(self, "main_spinner_label"):
                self.main_spinner_label.configure(image=frame)
                
            # Update the start button icon
            self.start_btn.configure(image=frame)
        
        self.after(100, self._animate_loading_loop)

    def _ui_log(self, msg):
        print(f"[LOG] {msg}")

    def _start_process(self):
        pdf_input = self.file_entry.get().strip()
        out_path = self.folder_entry.get().strip()
        
        if not pdf_input or not out_path:
            self.status_bar_str.set("Status: Pilih file/URL dan folder output!")
            self.status_label.configure(text_color="#EF4444")
            return
            
        self.start_btn.configure(state="disabled", text="  PROSESSING...")
        self.is_loading = True
        self.loading_container.grid()
        self._animate_loading_loop()
        
        self.status_bar_str.set("Status: Memulai proses...")
        self.status_label.configure(text_color="#3B82F6")
        
        # Clear previous results & reset stats
        for row in self.result_rows:
            row.destroy()
        self.result_rows = []
        self.all_resi = []
        if hasattr(self, "smooth_progress_bar"):
            self.smooth_progress_bar.set(0)
        self.progress_percent_str.set("0%")
        self.progress_text_str.set("Memproses 0 / 0 data resi...")
        self.total_data_str.set("0")
        self.berhasil_str.set("0")
        self.gagal_str.set("0")
        self.sku_unik_str.set("0")
        self.hasil_scan_title_str.set("HASIL SCAN (0 DATA)")

        # Run in thread
        thread = threading.Thread(target=self._process_logic, args=(pdf_input, out_path))
        thread.start()

    def _process_logic(self, pdf_input, out_path):
        temp_pdf = None
        try:
            # Detect if it's a URL
            if pdf_input.startswith(("http://", "https://")):
                self.after(0, self._update_progress, 0.05, "5%", "Mendownload PDF resi...")
                self._ui_log(f">>> MENDOWNLOAD: {pdf_input[:50]}...")
                
                temp_dir = tempfile.gettempdir()
                temp_filename = f"packflow_download_{datetime.datetime.now().strftime('%H%M%S')}.pdf"
                temp_pdf = os.path.join(temp_dir, temp_filename)
                
                urllib.request.urlretrieve(pdf_input, temp_pdf)
                pdf_path = temp_pdf
                self._ui_log(">>> DOWNLOAD SELESAI")
            else:
                pdf_path = pdf_input

            # 1. Read PDF (10% - 35%)
            self.after(0, self._update_progress, 0.1, "10%", "Membaca berkas PDF...")
            mode = self.settings.get("marketplace_mode", "Shopee")
            if mode == "TikTok":
                reader = TikTokPDFReader(logger=self._ui_log)
            elif mode == "Lazada":
                reader = LazadaPDFReader(logger=self._ui_log)
            else:
                reader = ShopeePDFReader(logger=self._ui_log)
            pages_data = reader.extract_data(pdf_path)
            self.after(0, self._update_progress, 0.35, "35%", "PDF berhasil dibaca.")
            
            # 2. Parse SKU and Build Labels (35% - 55%)
            self.after(0, self._update_progress, 0.35, "35%", "Menghitung SKU & Whitelist...")
            parser = SKUParser(ignored_skus=self.settings.get("ignored_skus", []), 
                               default_suffix=self.settings.get("sku_suffix", "ARY"),
                               sku_whitelist=self.settings.get("sku_whitelist", []))
            
            page_label_data = [] # For writer
            
            total_pages = len(pages_data)
            for i, page in enumerate(pages_data):
                # Update Progress (Parsing phase: 35% to 55%)
                progress_step = 0.35 + ((i + 1) / total_pages) * 0.2
                percent = f"{int(progress_step * 100)}%"
                text = f"Memproses data {i+1} / {total_pages}..."
                self.after(0, self._update_progress, progress_step, percent, text)
                self.update_idletasks()
                
                # ... [SKU Parsing Logic] ...

                parsed_items = []
                for sku, qty in page["items"]:
                    p_list = parser.parse_line(sku, qty)
                    if p_list:
                        parsed_items.extend(p_list)
                    else:
                        if not any(ignored in sku.upper() for ignored in parser.ignored_skus):
                            self._ui_log(f"Halaman {page['page_number']}: '{sku}' tidak terdaftar di Whitelist (Skip).")
                
                # Determine Display String and Kendala
                has_kendala = False
                kendala_reasons = []
                
                # A. SKU Kosong / Whitelist mismatch
                if not parsed_items:
                    has_kendala = True
                    kendala_reasons.append("SKU Kosong/Tidak Cocok Whitelist")
                
                # B. Resi Tidak Terdeteksi
                resi_val = page.get("resi")
                if not resi_val or resi_val == "UNKNOWN":
                    has_kendala = True
                    kendala_reasons.append("Resi Tidak Terdeteksi")
                    
                # C. Koordinat SKU/Label Tidak Ditemukan
                if not page.get("sku_header_coords") and not page.get("penerima_coords") and not page.get("unboxing_coords"):
                    has_kendala = True
                    kendala_reasons.append("Posisi Tabel SKU Tidak Ditemukan")
                
                num = page.get("nomor_pengiriman") or resi_val or "N/A"
                items_formatted = ",".join([f"{item['total_qty']},{item['name']}" for item in parsed_items]) if parsed_items else "Tanpa SKU"
                
                if has_kendala:
                    combine_text = f"[KENDALA: {', '.join(kendala_reasons)}] Halaman {page['page_number']} (Resi: {resi_val or 'N/A'}, SKU: {items_formatted})"
                else:
                    combine_text = f"{num},{items_formatted}"
                
                label_text = parser.build_label(parsed_items) if parsed_items else ""
                
                page_label_data.append({
                    "page_num": page["page_number"],
                    "label_text": label_text,
                    "kota": page.get("kota", "UNKNOWN"),
                    "penerima": page.get("penerima", "UNKNOWN"),
                    "coords": page["unboxing_coords"],
                    "penerima_coords": page.get("penerima_coords"),
                    "sku_header_coords": page.get("sku_header_coords"),
                    "cod_coords": page.get("cod_coords"),
                    "crop_y": page.get("crop_y"),
                    "item_count": len(parsed_items),
                    "resi": resi_val,
                    "has_kendala": has_kendala,
                    "kendala_reasons": kendala_reasons,
                    "combine_text": combine_text,
                    "parsed_items": parsed_items
                })
            
            # 3. Write PDF
            if not page_label_data:
                self.status_bar_str.set("Status: Gagal - Tidak ada halaman terbaca.")
                self.status_label.configure(text_color="#EF4444")
                self._ui_log("!!! GAGAL: Tidak ada halaman terbaca dari PDF.")
                return

            self.status_bar_str.set("Status: Menempelkan Label...")
            self.status_label.configure(text_color="#3B82F6")
            self._ui_log(">>> MENEMPELKAN LABEL KE PDF")
            writer = PDFLabelWriter(self.settings, logger=self._ui_log)
            
            is_split = self.settings.get("split_pdf", False)
            bulk_final_path = None

            # 4. Proactive Check & Rename for Bulk Mode
            if not is_split:
                self.status_bar_str.set("Status: Memeriksa folder tujuan...")
                self.status_label.configure(text_color="#3B82F6")
                template_bulk = self.settings.get("filename_format_bulk", "{kota}_{hari}{bulan}")
                ref_data = page_label_data[0] if page_label_data else {}
                raw_name = writer._get_formatted_filename(template_bulk, ref_data, pdf_path)
                suggested_name = writer._get_unique_path(out_path, raw_name)
                
                self.status_bar_str.set("Status: Menunggu konfirmasi nama file...")
                self.status_label.configure(text_color="#3B82F6")
                bulk_final_path = filedialog.asksaveasfilename(
                    initialdir=out_path,
                    initialfile=os.path.basename(suggested_name),
                    defaultextension=".pdf",
                    filetypes=[
                        ("PDF files", "*.pdf"),
                        ("Gambar PNG", "*.png"),
                        ("Gambar JPG", "*.jpg;*.jpeg"),
                        ("All files", "*.*")
                    ],
                    title="Simpan Hasil Sebagai..."
                )
                
                if not bulk_final_path:
                    self._ui_log(">>> PROSES DIBATALKAN OLEH USER")
                    self.status_bar_str.set("Status: Dibatalkan oleh pengguna.")
                    self.status_label.configure(text_color="#EF4444")
                    return
                
                bulk_final_path = os.path.abspath(bulk_final_path)

            # 5. Execute Writing (60% - 98%)
            def writer_progress(p):
                # Progress during writing: 60% to 98%
                step = 0.6 + p * 0.38
                percent = f"{int(step * 100)}%"
                text = f"Menempelkan label ke PDF... ({int(p * 100)}%)"
                self.after(0, self._update_progress, step, percent, text)

            result_path = writer.add_labels(pdf_path, out_path, page_label_data, 
                                          split_pages=is_split, 
                                          bulk_output_path=bulk_final_path,
                                          progress_callback=writer_progress,
                                          marketplace_mode=mode)
            
            # 6. Populate stats
            total_data = len(page_label_data)
            gagal_data = sum(1 for item in page_label_data if item.get("has_kendala", False))
            berhasil_data = total_data - gagal_data
            
            unique_skus = set()
            for item in page_label_data:
                for p in item.get("parsed_items", []):
                    unique_skus.add(p["name"].upper())
            sku_unik_data = len(unique_skus)
            
            self.total_data_str.set(str(total_data))
            self.berhasil_str.set(str(berhasil_data))
            self.gagal_str.set(str(gagal_data))
            self.sku_unik_str.set(str(sku_unik_data))
            self.hasil_scan_title_str.set(f"HASIL SCAN ({total_data} DATA)")
            
            # 7. Populate UI Results Grouped by City
            # Group data by city
            city_groups = {}
            for item in page_label_data:
                city = item.get("kota", "UNKNOWN").upper()
                if city not in city_groups:
                    city_groups[city] = []
                city_groups[city].append(item)
            
            # Sort cities alphabetically (optional, but good for UX)
            sorted_cities = sorted(city_groups.keys())
            
            row_idx = 1
            for city in sorted_cities:
                items = city_groups[city]
                # Sort items within city: Kendala first
                items.sort(key=lambda x: x.get("has_kendala", False), reverse=True)
                
                # Add City Header
                city_resi_texts = [it["combine_text"] for it in items]
                city_file_path = items[0].get("output_path") if self.settings.get("split_pdf") else None
                self._add_city_header(city, city_resi_texts, city_file_path)
                
                # Add Rows for this city
                for item in items:
                    self._add_result_row(
                        text=item["combine_text"],
                        resi=item.get("resi") or "NO_RESI",
                        folder=out_path,
                        has_kendala=item.get("has_kendala", False),
                        kendala_reason=", ".join(item.get("kendala_reasons", [])),
                        file_path=item.get("output_path"),
                        idx=row_idx
                    )
                    if item["combine_text"] not in self.all_resi:
                        self.all_resi.append(item["combine_text"])
                    row_idx += 1
            
            self.progress_bar.set(1.0)
            self.progress_percent_str.set("100%")
            self.progress_text_str.set(f"Selesai memproses {total_data} data resi.")
            self._ui_log(f">>> SELESAI! Hasil di: {result_path}")
            
            self._write_log(pdf_path, pages_data, page_label_data, "SUCCESS")
            self.status_bar_str.set(f"Status: Selesai! Simpan di {os.path.basename(result_path)}")
            self.status_label.configure(text_color="#10B981")
            
            # Open folder automatically
            os.startfile(out_path)
        except Exception as e:
            self._write_log(pdf_path, [], [], f"FAILED: {str(e)}")
            self.status_bar_str.set(f"Status: Error - {str(e)}")
            self.status_label.configure(text_color="#EF4444")
        finally:
            self.is_loading = False
            self.loading_container.grid_remove()
            self.start_btn.configure(state="normal", text="  START PROCESS", image=self.play_icon)
            if temp_pdf and os.path.exists(temp_pdf):
                try:
                    os.remove(temp_pdf)
                except:
                    pass

    def _write_log(self, input_file, pages_data, label_data, status):
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        log_file = os.path.join(log_dir, f"log_{datetime.date.today()}.txt")
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        with open(log_file, "a") as f:
            f.write(f"[{timestamp}] File: {os.path.basename(input_file)} | Status: {status}\n")
            if status == "SUCCESS":
                f.write(f"  - Halaman: {len(pages_data)}\n")
                f.write(f"  - Label Berhasil: {len([l for l in label_data if l['label_text']])}\n")
            f.write("-" * 50 + "\n")



    def _check_updates(self):
        self._ui_log("Mengecek pembaruan aplikasi...")
        self.updater.check_for_updates(self._on_update_found)

    def _on_update_found(self, has_update, info):
        if has_update and info:
            self.after(0, self._show_update_dialog, info)

    def _show_update_dialog(self, info):
        """Show a small elegant popup for update notification."""
        update_window = ctk.CTkToplevel(self)
        update_window.title("Update Tersedia!")
        update_window.geometry("400x250")
        update_window.resizable(False, False)
        update_window.attributes("-topmost", True)
        
        # Center popup
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 125
        update_window.geometry(f"+{x}+{y}")
        
        content = ctk.CTkFrame(update_window, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(content, text=f"Versi {info['version']} Tersedia!", font=("Segoe UI", 18, "bold"), text_color="#3B82F6").pack(pady=(0, 5))
        ctk.CTkLabel(content, text="Pembaruan baru telah dirilis dengan perbaikan dan fitur baru.", font=("Segoe UI", 12), text_color=("#4B5563", "#9CA3AF"), wraplength=350).pack(pady=5)
        
        # Progress bar for download (hidden initially)
        self.update_progress = ctk.CTkProgressBar(content, width=300)
        self.update_status_label = ctk.CTkLabel(content, text="", font=("Segoe UI", 11))
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(side="bottom", fill="x", pady=(10, 0))
        
        def start_download():
            btn_frame.pack_forget()
            self.update_progress.pack(pady=10)
            self.update_progress.set(0)
            self.update_status_label.pack()
            self.update_status_label.configure(text="Mengunduh pembaruan... 0%")
            
            self.updater.start_update(
                info["download_url"],
                self._on_update_progress,
                self._on_update_finished
            )

        ctk.CTkButton(btn_frame, text="Nanti Saja", width=120, fg_color=("#E5E7EB", "#1E293B"), text_color=("#1F2937", "#FFFFFF"), command=update_window.destroy).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Update Sekarang", width=180, fg_color="#2563EB", hover_color="#1D4ED8", command=start_download).pack(side="right", padx=5)

    def _on_update_progress(self, progress):
        self.after(0, lambda: [
            self.update_progress.set(progress),
            self.update_status_label.configure(text=f"Mengunduh pembaruan... {int(progress*100)}%")
        ])

    def _on_update_finished(self, success, result):
        if not success:
            self.after(0, lambda: self.update_status_label.configure(text=f"Gagal: {result}", text_color="#EF4444"))
        # If success, the app will exit anyway via sys.exit in core/updater.py
