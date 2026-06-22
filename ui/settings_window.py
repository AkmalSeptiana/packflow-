import customtkinter as ctk
import json
import os

class SettingsFrame(ctk.CTkFrame):
    def __init__(self, parent, settings_path, on_save_callback, on_close_callback, current_settings=None):
        # Initialize as a transparent frame to inherit window styling
        super().__init__(parent, fg_color="transparent")
        self.settings_path = settings_path
        self.on_save_callback = on_save_callback
        self.on_close_callback = on_close_callback
        self.settings = current_settings if current_settings is not None else {}
            
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        # Configure layout: Header (row 0), Body (row 1), Footer (row 2)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=0) # Header
        self.grid_rowconfigure(1, weight=1) # Scrollable Content
        self.grid_rowconfigure(2, weight=0) # Footer
        
        # 1. Header Frame
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=24, pady=(20, 10), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        header_frame.grid_columnconfigure(1, weight=0)
        
        header_title = ctk.CTkLabel(header_frame, text="  PENGATURAN", image=self.master.settings_title_icon, compound="left", font=("Segoe UI", 24, "bold"), text_color=("#1F2937", "#FFFFFF"))
        header_title.grid(row=0, column=0, sticky="w")
        
        subtitle = ctk.CTkLabel(header_frame, text="Konfigurasi parameter pelabelan & proses PDF", font=("Segoe UI", 12), text_color=("#4B5563", "#8F9CAE"))
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))
        
        back_btn_top = ctk.CTkButton(header_frame, text="  Kembali", image=self.master.arrow_left_icon, compound="left", font=("Segoe UI", 11, "bold"), width=90, height=26,
                                     fg_color=("#E5E7EB", "#1E293B"), border_width=1, border_color=("#D1D5DB", "#374151"), hover_color=("#D1D5DB", "#334155"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6,
                                     command=self.on_close_callback)
        back_btn_top.grid(row=0, column=1, rowspan=2, sticky="e", pady=4)
        
        # 2. Scrollable Content Body
        scroll_body = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll_body.grid(row=1, column=0, padx=24, pady=10, sticky="nsew")
        scroll_body.grid_columnconfigure(0, weight=1)
        
        # Card 1: PENGATURAN SKU
        sku_card = ctk.CTkFrame(scroll_body, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=10)
        sku_card.pack(fill="x", pady=10)
        sku_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(sku_card, text="  PENGATURAN SKU", image=self.master.tag_blue_icon, compound="left", font=("Segoe UI", 13, "bold"), text_color="#3B82F6").grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 6), sticky="w")
        
        ctk.CTkLabel(sku_card, text="Kode Member:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.suffix_entry = ctk.CTkEntry(sku_card, font=("Segoe UI", 12), fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.suffix_entry.grid(row=1, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(sku_card, text="Pengecualian SKU (koma):", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=2, column=0, padx=16, pady=6, sticky="w")
        self.ignored_entry = ctk.CTkEntry(sku_card, font=("Segoe UI", 12), fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.ignored_entry.grid(row=2, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(sku_card, text="Daftar Whitelist SKU\n(Pisahkan dengan koma):", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF"), justify="left").grid(row=3, column=0, padx=16, pady=6, sticky="nw")
        self.whitelist_text = ctk.CTkTextbox(sku_card, height=100, font=("Consolas", 11), fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), border_width=1, corner_radius=6)
        self.whitelist_text.grid(row=3, column=1, padx=16, pady=6, sticky="nsew")
        
        # Card 2: FORMAT & DESAIN LABEL
        label_card = ctk.CTkFrame(scroll_body, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=10)
        label_card.pack(fill="x", pady=10)
        label_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(label_card, text="  FORMAT & DESAIN LABEL", image=self.master.palette_blue_icon, compound="left", font=("Segoe UI", 13, "bold"), text_color="#3B82F6").grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 6), sticky="w")
        
        ctk.CTkLabel(label_card, text="Jenis Font:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.font_family_option = ctk.CTkOptionMenu(label_card, values=["Helvetica-Bold", "Helvetica", "Courier-Bold", "Courier", "Times-Bold"], font=("Segoe UI", 12), corner_radius=6)
        self.font_family_option.grid(row=1, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(label_card, text="Ukuran Font:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=2, column=0, padx=16, pady=6, sticky="w")
        self.font_size_entry = ctk.CTkEntry(label_card, font=("Segoe UI", 12), fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.font_size_entry.grid(row=2, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(label_card, text="Warna Label:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=3, column=0, padx=16, pady=6, sticky="w")
        self.color_option = ctk.CTkOptionMenu(label_card, values=["Red", "Black", "Blue", "Green"], font=("Segoe UI", 12), corner_radius=6)
        self.color_option.grid(row=3, column=1, padx=16, pady=6, sticky="ew")
        
        # Card 3: INTEGRASI TELEGRAM
        tg_card = ctk.CTkFrame(scroll_body, fg_color=("#FFFFFF", "#111827"), border_width=1, border_color=("#E5E7EB", "#1F2937"), corner_radius=10)
        tg_card.pack(fill="x", pady=10)
        tg_card.grid_columnconfigure(1, weight=1)
        
        ctk.CTkLabel(tg_card, text="  INTEGRASI TELEGRAM BOT", image=self.master.send_icon, compound="left", font=("Segoe UI", 13, "bold"), text_color="#3B82F6").grid(row=0, column=0, columnspan=2, padx=16, pady=(12, 6), sticky="w")
        
        ctk.CTkLabel(tg_card, text="Bot Token:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=1, column=0, padx=16, pady=6, sticky="w")
        self.tg_token_entry = ctk.CTkEntry(tg_card, font=("Segoe UI", 12), fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.tg_token_entry.grid(row=1, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(tg_card, text="Chat ID:", font=("Segoe UI", 12), text_color=("#1F2937", "#FFFFFF")).grid(row=2, column=0, padx=16, pady=6, sticky="w")
        self.tg_chat_id_entry = ctk.CTkEntry(tg_card, font=("Segoe UI", 12), fg_color=("#F9FAFB", "#1F2937"), border_color=("#D1D5DB", "#374151"), text_color=("#1F2937", "#FFFFFF"), corner_radius=6)
        self.tg_chat_id_entry.grid(row=2, column=1, padx=16, pady=6, sticky="ew")
        
        ctk.CTkLabel(tg_card, text="Tips: Gunakan @userinfobot untuk mengetahui Chat ID Anda.", font=("Segoe UI", 11, "italic"), text_color="#8F9CAE").grid(row=3, column=0, columnspan=2, padx=16, pady=(0, 12), sticky="w")
        
        
        # 3. Footer Frame (Buttons)
        footer_frame = ctk.CTkFrame(self, fg_color="transparent")
        footer_frame.grid(row=2, column=0, padx=24, pady=(10, 20), sticky="ew")
        footer_frame.grid_columnconfigure(0, weight=1)
        footer_frame.grid_columnconfigure(1, weight=1)
        
        self.cancel_btn = ctk.CTkButton(footer_frame, text="  Batal", image=self.master.x_icon, compound="left", font=("Segoe UI", 13, "bold"), height=40,
                                         fg_color=("#E5E7EB", "#1E293B"), hover_color=("#D1D5DB", "#334155"), text_color=("#1F2937", "#FFFFFF"), corner_radius=8,
                                         command=self.on_close_callback)
        self.cancel_btn.grid(row=0, column=0, padx=(0, 6), sticky="ew")
        
        self.save_btn = ctk.CTkButton(footer_frame, text="  Simpan Pengaturan", image=self.master.save_icon, compound="left", font=("Segoe UI", 13, "bold"), height=40,
                                       fg_color="#2563EB", hover_color="#1D4ED8", text_color="#FFFFFF", corner_radius=8,
                                       command=self._save_settings)
        self.save_btn.grid(row=0, column=1, padx=(6, 0), sticky="ew")

    def _load_values(self):
        self.suffix_entry.insert(0, self.settings.get("sku_suffix", ""))
        self.ignored_entry.insert(0, ", ".join(self.settings.get("ignored_skus", [])))
        self.font_family_option.set(self.settings.get("label_font_family", "Arial-Bold"))
        self.font_size_entry.insert(0, str(self.settings.get("label_font_size", 18)))
        self.color_option.set(self.settings.get("label_color", "Red"))
        
        self.tg_token_entry.insert(0, self.settings.get("telegram_bot_token", ""))
        self.tg_chat_id_entry.insert(0, self.settings.get("telegram_chat_id", ""))

        whitelist = self.settings.get("sku_whitelist", [])
        self.whitelist_text.insert("0.0", ", ".join(whitelist))

    def _save_settings(self):
        try:
            self.settings["sku_suffix"] = self.suffix_entry.get()
            self.settings["ignored_skus"] = [s.strip().upper() for s in self.ignored_entry.get().split(",") if s.strip()]
            self.settings["label_font_family"] = self.font_family_option.get()
            
            try:
                self.settings["label_font_size"] = int(self.font_size_entry.get())
            except ValueError:
                self.settings["label_font_size"] = 18
                
            self.settings["label_color"] = self.color_option.get()
            self.settings["telegram_bot_token"] = self.tg_token_entry.get().strip()
            self.settings["telegram_chat_id"] = self.tg_chat_id_entry.get().strip()
            
            config_dir = os.path.dirname(self.settings_path)
            if config_dir and not os.path.exists(config_dir):
                os.makedirs(config_dir)
                
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=2)
                
            self.on_save_callback(self.settings)
            self.on_close_callback()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"Gagal menyimpan pengaturan: {str(e)}")
