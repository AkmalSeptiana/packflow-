import fitz  # PyMuPDF
import os

class PDFLabelWriter:
    def __init__(self, settings, logger=None):
        self.settings = settings
        self.font_mapping = {
            "Helvetica-Bold": "hebo",
            "Helvetica": "helv",
            "Courier-Bold": "cobo",
            "Courier": "cour",
            "Times-Bold": "tibo"
        }
        self.font_name = self.font_mapping.get(settings.get("label_font_family"), "hebo")
        self.font_size = settings.get("label_font_size", 22)
        self.color = self._parse_color(settings.get("label_color", "Red"))
        self.logger = logger

    def log(self, msg):
        if self.logger:
            self.logger(msg)

    def _parse_color(self, color_name):
        colors = {
            "Red": (1, 0, 0),
            "Black": (0, 0, 0),
            "Blue": (0, 0, 1),
            "Green": (0, 0.5, 0)
        }
        return colors.get(color_name, (1, 0, 0))

    def _get_formatted_filename(self, template, data, original_filename=""):
        from datetime import datetime
        now = datetime.now()
        
        tokens = {
            "{resi}": data.get("resi", "NO_RESI"),
            "{penerima}": data.get("penerima", "UNKNOWN"),
            "{nama}": data.get("penerima", "UNKNOWN"),
            "{kota}": data.get("kota", "UNKNOWN"),
            "{hari}": now.strftime("%d"),
            "{bulan}": now.strftime("%m"),
            "{tahun}": now.strftime("%Y"),
            "{file}": os.path.splitext(os.path.basename(original_filename))[0] if original_filename else "LABEL"
        }
        
        result = template
        for token, val in tokens.items():
            result = result.replace(token, str(val))
        
        for char in '<>:"/\\|?*':
            result = result.replace(char, "_")
        return result

    def _get_unique_path(self, folder, filename, ext=".pdf"):
        # Avoid misidentifying dots in city names (e.g. 'KAB. BANDUNG') as extensions
        known_exts = [".pdf", ".png", ".jpg", ".jpeg"]
        base_name, existing_ext = os.path.splitext(filename)
        
        if existing_ext.lower() in known_exts:
            final_ext = existing_ext
        else:
            final_ext = ext
            base_name = filename # Use the full filename as base if it's not a known extension
        
        target_path = os.path.join(folder, f"{base_name}{final_ext}")
        if not os.path.exists(target_path):
            return target_path
        
        counter = 1
        while True:
            new_filename = f"{base_name} ({counter}){final_ext}"
            new_path = os.path.join(folder, new_filename)
            if not os.path.exists(new_path):
                return new_path
            counter += 1
            
    def _find_empty_space(self, page, rect_width, rect_height, data=None):
        """
        Finds a clear rectangular area of (rect_width x rect_height) on the page.
        Prioritizes the vertical middle and right side.
        """
        occupied = []
        text_dict = page.get_text("dict")
        for block in text_dict["blocks"]:
            if "lines" in block:
                for line in block["lines"]:
                    for span in line["spans"]:
                        occupied.append(fitz.Rect(span["bbox"]))
        for d in page.get_drawings():
            occupied.append(d["rect"])
        
        occupied = [r + (-1, -1, 1, 1) for r in occupied]
        
        page_width = page.rect.width
        y_start = 80
        y_end = int(data.get("crop_y", 400)) if data and data.get("crop_y") else 450
        
        step_y = 5
        step_x = 10
        
        y_mid = (y_start + y_end) / 2
        y_positions = sorted(range(y_start, int(y_end - rect_height), step_y), key=lambda y: abs(y - y_mid))
        
        for y in y_positions:
            for x in range(int(page_width - rect_width - 15), 30, -step_x):
                candidate = fitz.Rect(x, y, x + rect_width, y + rect_height)
                if not any(candidate.intersects(r) for r in occupied):
                    return x, y + (rect_height * 0.8)
                    
        return None

    def add_labels(self, input_pdf, output_folder, page_label_data, split_pages=False, bulk_output_path=None, progress_callback=None, marketplace_mode="Shopee"):
        doc = fitz.open(input_pdf)
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        results = []
        
        template_bulk = self.settings.get("filename_format_bulk", "{kota}_{hari}{bulan}")
        template_split = self.settings.get("filename_format_split", "{kota}_{resi}")

        total_pages = len(page_label_data)
        for idx, data in enumerate(page_label_data):
            if progress_callback and total_pages > 0:
                try: progress_callback(idx / total_pages)
                except: pass
                
            page_idx = data["page_num"] - 1
            if page_idx >= len(doc): continue
                
            page = doc[page_idx]
            page_width = page.rect.width
            
            # --- Draw Warning Banner if page has kendala ---
            if data.get("has_kendala"):
                reasons_str = ", ".join(data.get("kendala_reasons", ["Kendala"]))
                warning_text = f"[KENDALA: {reasons_str.upper()}]"
                banner_height = 20
                banner_rect = fitz.Rect(10, 10, page_width - 10, 10 + banner_height)
                page.draw_rect(banner_rect, color=(1, 0, 0), fill=(1, 0.9, 0.9), width=1.5, overlay=True)
                warning_font_size = 11
                text_w = fitz.get_text_length(warning_text, fontname="hebo", fontsize=warning_font_size)
                x_text = (page_width - text_w) / 2
                y_text = 10 + (banner_height + warning_font_size * 0.8) / 2
                page.insert_text((x_text, y_text), warning_text, fontsize=warning_font_size, fontname="hebo", color=(1, 0, 0))
                self.log(f"Halaman {data['page_num']}: Menggambar banner kendala ({reasons_str})")
            
            # --- TikTok: Cover bottom area with solid white rectangle FIRST ---
            if marketplace_mode == "TikTok":
                crop_y = data.get("crop_y")
                if crop_y and crop_y > 0:
                    cover_rect = fitz.Rect(0, crop_y, page.rect.width, page.rect.height)
                    page.draw_rect(cover_rect, color=(1, 1, 1), fill=(1, 1, 1), width=0, overlay=True)
                    self.log(f"Halaman {data['page_num']}: Tutup kotak putih di Y={crop_y:.1f}")

            label_text = data.get("label_text", "")
            if label_text:
                # --- Position logic ---
                cod_coords = data.get("cod_coords")
                sku_header = data.get("sku_header_coords")
                penerima_coords = data.get("penerima_coords")
                unboxing_coords = data.get("coords")
                
                if marketplace_mode == "TikTok":
                    approx_text_width = fitz.get_text_length(label_text, fontname=self.font_name, fontsize=self.font_size)
                    rect_w = min(approx_text_width + 10, page_width - 40)
                    rect_h = self.font_size + 8
                    
                    # Selalu utamakan ruang kosong di atas terlebih dahulu
                    found_spot = self._find_empty_space(page, rect_w, rect_h, data)
                    bottom_y_start = int(data.get("crop_y", page.rect.height - 70))
                    
                    if found_spot:
                        x_pos, target_y = found_spot
                        self.log(f"Halaman {data['page_num']}: Menempelkan Label di ruang kosong atas (Y={target_y:.1f})")
                    elif cod_coords:
                        x_pos = cod_coords['x1'] + 5
                        target_y = cod_coords['bottom'] - 5
                        self.log(f"Halaman {data['page_num']}: Menempelkan Label di samping COD")
                    else:
                        # Fallback terakhir: area putih di bawah
                        x_pos = 15
                        target_y = bottom_y_start + 18
                        self.log(f"Halaman {data['page_num']}: Fallback ke area putih bawah (Y={target_y:.1f}).")
                elif sku_header:
                    item_count = data.get("item_count", 1)
                    x_pos = sku_header['x1'] - 60 if item_count > 1 else sku_header['x1'] + 3
                    target_y = sku_header['bottom'] + 2
                    self.log(f"Halaman {data['page_num']}: Menempelkan Label SKU")
                elif unboxing_coords:
                    x_pos = page_width * 0.38 
                    target_y = unboxing_coords['bottom'] + 2
                    self.log(f"Halaman {data['page_num']}: Menempelkan Label (fallback Unboxing)")
                elif penerima_coords:
                    x_pos = page_width * 0.38 
                    target_y = penerima_coords['bottom'] 
                    self.log(f"Halaman {data['page_num']}: Menempelkan Label (fallback Buyer)")
                else:
                    text_width = fitz.get_text_length(label_text, fontname=self.font_name, fontsize=self.font_size)
                    x_pos = (page_width - text_width) / 2
                    target_y = 200
                
                # --- Text Drawing logic ---
                max_avail_width = (page_width - x_pos) - 10
                def get_text_width(text):
                    return fitz.get_text_length(text, fontname=self.font_name, fontsize=self.font_size)
                
                full_width = get_text_width(label_text)
                lines = []
                if full_width > max_avail_width and " + " in label_text:
                    parts = label_text.split(" + ")
                    current_line = parts[0]
                    for p in parts[1:]:
                        test_line = current_line + " + " + p
                        if get_text_width(test_line) < max_avail_width:
                            current_line = test_line
                        else:
                            lines.append(current_line); current_line = "+ " + p
                    lines.append(current_line)
                else:
                    lines = [label_text]
      
                current_y = target_y
                for line in lines:
                    this_w = get_text_width(line)
                    bg_rect = fitz.Rect(x_pos - 3, current_y - self.font_size * 0.8, x_pos + this_w + 3, current_y + 2)
                    page.draw_rect(bg_rect, color=(1, 1, 1), fill=(1, 1, 1), overlay=True)
                    page.insert_text((x_pos, current_y), line, fontsize=self.font_size, fontname=self.font_name, color=self.color)
                    if "bold" in self.font_name.lower():
                        page.insert_text((x_pos, current_y), line, fontsize=self.font_size, fontname=self.font_name, color=self.color)
                    current_y += self.font_size + 2

        if split_pages:
            # Group by City (Gudang) logic
            city_groups = {}
            for data in page_label_data:
                city = data.get("kota", "UNKNOWN").upper()
                if city not in city_groups:
                    city_groups[city] = []
                city_groups[city].append(data)

            for city, items in city_groups.items():
                # Sort items within city to match UI: Kendala first, then original order
                items.sort(key=lambda x: x.get("has_kendala", False), reverse=True)
                
                # Use the template for split (now per city)
                # We use the first item in the group to provide data for the filename
                raw_filename = self._get_formatted_filename(template_split, items[0], input_pdf)
                
                # If any item in the group has a kendala, mark the file
                has_any_kendala = any(item.get("has_kendala") for item in items)
                if has_any_kendala:
                    raw_filename = f"_KENDALA_{raw_filename}"
                
                out_path = self._get_unique_path(output_folder, raw_filename, ".pdf")
                
                new_doc = fitz.open()
                for item in items:
                    page_idx = item["page_num"] - 1
                    new_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
                
                new_doc.save(out_path)
                new_doc.close()
                
                results.append(out_path)
                # Update all items in this group with the final output path for the UI
                for item in items:
                    item["output_path"] = out_path
                self.log(f"Berhasil menyimpan {len(items)} resi ke grup Gudang: {city} -> {os.path.basename(out_path)}")
  
        if marketplace_mode == "TikTok" and not split_pages:
            pages_to_keep = set(data["page_num"] - 1 for data in page_label_data)
            pages_to_remove = sorted([i for i in range(len(doc)) if i not in pages_to_keep], reverse=True)
            if pages_to_remove:
                self.log(f"TikTok: Menghapus {len(pages_to_remove)} halaman lanjutan dari PDF.")
                for pi in pages_to_remove: doc.delete_page(pi)

        if not split_pages:
            # Reorder pages to match UI (City grouping + Kendala first)
            city_groups = {}
            for data in page_label_data:
                city = data.get("kota", "UNKNOWN").upper()
                if city not in city_groups:
                    city_groups[city] = []
                city_groups[city].append(data)
            
            sorted_cities = sorted(city_groups.keys())
            final_reordered_doc = fitz.open()
            
            for city in sorted_cities:
                items = city_groups[city]
                # Sort items within city to match UI: Kendala first, then original order
                items.sort(key=lambda x: x.get("has_kendala", False), reverse=True)
                for item in items:
                    page_idx = item["page_num"] - 1
                    if page_idx < len(doc):
                        final_reordered_doc.insert_pdf(doc, from_page=page_idx, to_page=page_idx)
            
            if bulk_output_path:
                output_path = bulk_output_path
            else:
                raw_filename = self._get_formatted_filename(template_bulk, page_label_data[0] if page_label_data else {}, input_pdf)
                output_path = self._get_unique_path(output_folder, raw_filename)
            
            _, ext = os.path.splitext(output_path)
            ext = ext.lower()
            if ext in [".png", ".jpg", ".jpeg"]:
                base_path, _ = os.path.splitext(output_path)
                if len(final_reordered_doc) == 1:
                    page = final_reordered_doc[0]
                    pix = page.get_pixmap(dpi=200)
                    pix.save(output_path)
                    # Note: mapping output path to original data order is tricky if we reordered, 
                    # but for now we update based on reordered index
                    # [Optional: update item["output_path"] here if needed]
                else:
                    for i, page in enumerate(final_reordered_doc):
                        pix = page.get_pixmap(dpi=200)
                        page_path = f"{base_path}_{i+1}{ext}"
                        pix.save(page_path)
                final_reordered_doc.close()
                doc.close()
                return output_path
            else:
                final_reordered_doc.save(output_path)
                final_reordered_doc.close()
                doc.close()
                return output_path
        
        doc.close()
        return output_folder if results else None
