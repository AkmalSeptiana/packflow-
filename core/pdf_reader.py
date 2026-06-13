import pdfplumber
import re

class ShopeePDFReader:
    def __init__(self, logger=None):
        self._log = logger
        # Keywords to find the SKU table area
        self.sku_keywords = ["SKU", "NAMA PRODUK", "VARIASI", "ITEM", "DESKRIPSI", "JUMLAH", "QTY", "CATATAN"]

    def log(self, message):
        if self._log:
            self._log(message)

    def extract_data(self, pdf_path):
        results = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for i, page in enumerate(pdf.pages):
                    # ALIGNED WITH main_window.py expectations
                    page_data = {
                        "page_number": i + 1,
                        "resi": None,
                        "nomor_pesanan": None,
                        "items": [],
                        "sku_header_coords": None,
                        "unboxing_coords": None,
                        "penerima_coords": None
                    }
                    
                    text = page.extract_text()
                    if not text:
                        continue

                    # 1. Extract Order Info (Prioritizing Various Providers)
                    resi_patterns = [
                        r'\b(?:GK|IN)-\d+-[A-Z0-9-]+\b',               # Instant GK- or IN- patterns
                        r'\bIN-[A-Z0-9-]+\b',                          # Other IN- formats
                        r'\b00\d{10,11}\b',                            # Sicepat
                        r'\b1\d{12,13}\b',                             # Anteraja (starts with 1, 13-14 digits)
                        r'(?:SPXID|SPX|ID|JP|CBN|PLD|TJB|JX|CM|JNE|SHP|SHPE|NX)[\s:.]*[A-Z0-9]{7,25}', # Alphanumeric with flexible separators
                        r'\b\d{10,20}\b'                               # General numeric fallback (relaxed length)
                    ]
                    
                    all_matches = []
                    for pattern in resi_patterns:
                        for m in re.finditer(pattern, text, re.IGNORECASE):
                            val = m.group(0).strip()
                            if len(val) >= 7:
                                all_matches.append(val)
                    
                    if all_matches:
                        # Prioritize SPXID if multiple matches found
                        spx_matches = [m for m in all_matches if "SPX" in m.upper()]
                        resi_val = spx_matches[0] if spx_matches else all_matches[0]
                        
                        # Deep Clean
                        for char in [":", ".", ",", "(", ")"]:
                            resi_val = resi_val.replace(char, " ")
                        
                        # Identify Prefix - Initialize as empty
                        found_prefix = ""
                        prefixes = ["SPXID", "SPX", "ID", "JP", "CBN", "PLD", "TJB", "JX", "CM", "JNE", "SHPE", "SHP", "NX"]
                        for p in prefixes:
                            if resi_val.upper().startswith(p):
                                found_prefix = p
                                break
                        
                        # Body processing
                        if found_prefix:
                            body = resi_val[len(found_prefix):]
                            
                            # Most standard providers in Indonesia use numeric bodies after the prefix
                            # But some can have letters at the end (like ID...N)
                            digit_only_providers = ["SPXID", "SPX", "JP", "CBN", "PLD", "TJB", "JX", "CM", "JNE", "SHP", "NX"]
                            is_digit_provider = any(found_prefix.upper() == p for p in digit_only_providers)
                            
                            if is_digit_provider:
                                # Standard tracking numbers (like SPXID, J&T, etc) should only be numeric after the prefix
                                body = re.sub(r'COD', '', body, flags=re.IGNORECASE)
                                body = re.sub(r'[^0-9]', '', body) # ONLY KEEP DIGITS
                                
                                # Normalize Shopee Express
                                if found_prefix.upper() in ["SPXID", "SPX"]:
                                    page_data["resi"] = "SPXID" + body
                                else:
                                    page_data["resi"] = found_prefix.upper() + body
                            elif found_prefix.upper() == "ID":
                                # SPECIAL: ID prefix can be numeric or have trailing letters
                                body = re.sub(r'COD', '', body, flags=re.IGNORECASE)
                                body = re.sub(r'[^A-Z0-9]', '', body, flags=re.IGNORECASE)
                                page_data["resi"] = "ID" + body.upper()
                            else:
                                # Fallback for unexpected alphanumeric formats
                                body = re.sub(r'[^A-Z0-9]', '', body, flags=re.IGNORECASE)
                                body = re.sub(r'COD', '', body, flags=re.IGNORECASE)
                                page_data["resi"] = found_prefix.upper() + body
                        else:
                            # NO PREFIX: numeric-only resi like Sicepat/Anteraja
                            # Just clean up spaces and noise from the whole string
                            clean_val = re.sub(r'[^0-9]', '', resi_val)
                            page_data["resi"] = clean_val
                            
                        self.log(f"Nomor Resi: {page_data['resi']}")
                        found_resi = True
                    
                    order_match = re.search(r'PESANAN[:\s]*([A-Z0-9]+)', text, re.IGNORECASE)
                    if order_match:
                        page_data["nomor_pesanan"] = order_match.group(1)
                        self.log(f"Nomor Pesanan: {page_data['nomor_pesanan']}")

                    # 1b. Extract Recipient (Penerima) - Fixed & Robust
                    words = page.extract_words()
                    penerima_node = None
                    for w in words:
                        w_text = w['text'].upper()
                        if "PENERIMA" in w_text and "PENGIRIM" not in w_text:
                            penerima_node = w
                            break
                    
                    if penerima_node:
                        target_y = penerima_node['top']
                        line_words = [w for w in words if abs(w['top'] - target_y) < 5 and w['x0'] >= penerima_node['x0']]
                        line_words.sort(key=lambda x: x['x0'])
                        full_line_text = " ".join([w['text'] for w in line_words])
                        name_part = re.sub(r'^[Pp]enerima\s*:\s*', '', full_line_text).strip()
                        name_clean = re.split(r'PENGIRIM|KOTA|KAB\.|\*{2,}', name_part, flags=re.IGNORECASE)[0].strip()
                        name_clean = re.split(r'\s{2,}|\|', name_clean)[0].strip()
                        page_data["penerima"] = name_clean or "NO_NAME"
                    else:
                        # Final Fallback for Receiver: look for anything bold/large near the top if keyword fails?
                        # For now use Resi if name unknown
                        page_data["penerima"] = page_data.get("resi", "UNKNOWN")
                    
                    self.log(f"Penerima: {page_data['penerima']}")

                    # 1c. Extract City (Kota) near Pengirim
                    kota_found = False
                    pengirim_node = next((w for w in words if "PENGIRIM" in w['text'].upper()), None)
                    if pengirim_node:
                        target_y = pengirim_node['top']
                        city_node = next((w for w in words if ("KOTA" in w['text'].upper() or "KAB." in w['text'].upper()) 
                                         and abs(w['top'] - target_y) < 10 and w['x0'] > pengirim_node['x1']), None)
                        if city_node:
                            line_words = [w for w in words if abs(w['top'] - city_node['top']) < 5 and w['x0'] >= city_node['x0']]
                            line_words.sort(key=lambda x: x['x0'])
                            # Join all words on the line into one string to handle merged text
                            raw_full_line = " ".join([w['text'] for w in line_words]).strip()
                            
                            # Use Regex to find KOTA or KAB and stop before long digit sequences (phone/resi)
                            # This handles "StoreKOTA PALEMBANG8810..." -> "KOTA PALEMBANG"
                            match = re.search(r'(KOTA|KAB\.?)\s*(.*?)(?=\s*\d{6,}|$)', raw_full_line, re.IGNORECASE)
                            if match:
                                city_raw = match.group(1) + " " + match.group(2)
                            else:
                                # Fallback if regex fails: use original joined list
                                city_raw = raw_full_line
                            
                            # Clean up tokens like COD, ECO, etc.
                            noise = ["COD", "NON-COD", "ECO", "REG", "SPX"]
                            for n in noise:
                                city_raw = re.sub(fr'\b{n}\b', '', city_raw, flags=re.IGNORECASE)

                            # Normalize city string
                            # 1. Remove "KOTA" (case insensitive)
                            city_normalized = re.sub(r'\bKOTA\b', '', city_raw, flags=re.IGNORECASE).strip()
                            # 2. Normalize KABUPATEN/KAB to KAB.
                            city_normalized = re.sub(r'\bKABUPATEN\b', 'KAB.', city_normalized, flags=re.IGNORECASE)
                            city_normalized = re.sub(r'\bKAB\b(?!\.)', 'KAB.', city_normalized, flags=re.IGNORECASE)
                            
                            page_data["kota"] = city_normalized
                            kota_found = True if page_data["kota"] else False

                    # Final Fallback for City: Search whole page for KOTA/KAB if Pengirim line failed
                    if not kota_found:
                        # Improved Fallback: Find the word after "KOTA " or "KAB. "
                        for w in sorted(words, key=lambda x: (x['top'], x['x0'])):
                            t_up = w['text'].upper()
                            if t_up in ["KOTA", "KAB."]:
                                # Take the next few words on the same line
                                next_words = [nw for nw in words if abs(nw['top'] - w['top']) < 5 and nw['x0'] > w['x1']]
                                next_words.sort(key=lambda x: x['x0'])
                                if next_words:
                                    # Fallback extraction
                                    raw_val = f"{t_up} {next_words[0]['text'].strip()}"
                                    # Normalize
                                    norm_val = re.sub(r'\bKOTA\b', '', raw_val, flags=re.IGNORECASE).strip()
                                    norm_val = re.sub(r'\bKABUPATEN\b', 'KAB.', norm_val, flags=re.IGNORECASE)
                                    norm_val = re.sub(r'\bKAB\b(?!\.)', 'KAB.', norm_val, flags=re.IGNORECASE)
                                    page_data["kota"] = norm_val
                                    kota_found = True
                                    break
                                    
                        if not kota_found:
                            page_data["kota"] = "NO_KOTA"
                    
                    # Last minute clean up for COD
                    if page_data["kota"].upper() == "COD":
                        page_data["kota"] = "NO_KOTA"
                    
                    self.log(f"Kota Pengirim: {page_data['kota']}")

                    # 2. Capture Positions (More robust search)
                    words = page.extract_words()
                    # Search for SKU Header
                    for kw in self.sku_keywords:
                        matches = page.search(kw)
                        if matches:
                            page_data["sku_header_coords"] = matches[0]
                            self.log(f"Header ditemukan: '{kw}'")
                            break
                    
                    # Search for Penerima
                    penerima_matches = page.search("Penerima", case=False)
                    if penerima_matches:
                        page_data["penerima_coords"] = penerima_matches[0]
                        self.log("Penerima ditemukan")
                        
                    # Search for Unboxing
                    unboxing_matches = page.search("UNBOXING", case=False)
                    if unboxing_matches:
                        page_data["unboxing_coords"] = unboxing_matches[0]
                        self.log("Unboxing ditemukan")

                    # 3. Robust Line-by-Line SKU Extraction
                    # Using sku_header_coords for boundary
                    anchor = page_data["sku_header_coords"] or page_data["unboxing_coords"]
                    y_start = anchor['bottom'] if anchor else 300
                    y_end = page.height - 5
                    self.log(f"Scanning SKUs from y={y_start} to y={y_end} (Page Height: {page.height})")
                    
                    # Group words into lines
                    lines = {}
                    for w in words:
                        if y_start < w['top'] < y_end:
                            y_key = round(w['top'])
                            found_y = False
                            for existing_y in lines.keys():
                                if abs(existing_y - y_key) <= 3:
                                    lines[existing_y].append(w)
                                    found_y = True
                                    break
                            if not found_y:
                                lines[y_key] = [w]

                    for y, line_words in sorted(lines.items()):
                        line_words = sorted(line_words, key=lambda w: w['x0'])
                        line_text = " ".join([w['text'] for w in line_words]).strip()
                        
                        if not line_text: continue
                        self.log(f"Line: '{line_text}'")
                        
                        # Filter out table noise and other text sections
                        noise_keywords = ["SKU", "NAMA PRODUK", "QTY", "JUMLAH", "#", "TOTAL", "PESANAN", 
                                         "CATATAN PEMBELI", "PESAN DARI PEMBELI", "PESAN:", "WAJIB VIDEO"]
                        if any(kw in line_text.upper() for kw in noise_keywords):
                            continue

                        # Robust Split for Qty vs SKU
                        parts = line_text.split()
                        if len(parts) < 1: continue

                        # A. Skip Row Index (First part if digit and separated)
                        if parts[0].isdigit() and len(parts) > 1:
                            parts = parts[1:]

                        # B. Identify Qty at the very end
                        qty = 1
                        sku_parts = parts
                        if len(parts) >= 2:
                            if parts[-1].isdigit():
                                qty = int(parts[-1])
                                sku_parts = parts[:-1]
                            elif len(parts) >= 3 and parts[-2].isdigit():
                                qty = int(parts[-2])
                                sku_parts = parts[:-2]

                        sku_candidate = " ".join(sku_parts).strip()
                        if len(sku_candidate) >= 2 and any(c.isalpha() for c in sku_candidate):
                            if not re.match(r'^\d{4}-\d{2}-\d{2}$', sku_candidate):
                                page_data["items"].append((sku_candidate, qty))
                                self.log(f"Terbaca: SKU='{sku_candidate}', Qty={qty}")
                    
                    if page_data["items"]:
                        results.append(page_data)
                    else:
                        self.log(f"Halaman {i+1}: Tidak ada SKU terdeteksi.")
                        
        except Exception as e:
            self.log(f"Error pembacaan PDF: {str(e)}")
            
        return results


class TikTokPDFReader:
    def __init__(self, logger=None):
        self._log = logger

    def log(self, message):
        if self._log:
            self._log(message)

    def _extract_page_raw(self, page, page_index):
        """Extract raw data from a single PDF page."""
        page_data = {
            "page_number": page_index + 1,
            "resi": None,
            "nomor_pesanan": None,
            "items": [],
            "sku_header_coords": None,
            "unboxing_coords": None,
            "penerima_coords": None,
            "penerima": "UNKNOWN",
            "kota": "NO_KOTA",
            "cod_coords": None,
            "crop_y": None,
            "is_shipping_label": False  # True if this page has sender/receiver info
        }
        
        text = page.extract_text()
        if not text:
            return None

        words = page.extract_words()
        lines = [line.strip() for line in text.splitlines() if line.strip()]

        # Extract Order ID
        order_match = re.search(r'order\s*id\s*[:\s]*(\d+)', text, re.IGNORECASE)
        if order_match:
            page_data["nomor_pesanan"] = order_match.group(1).strip()

        # Extract Resi (Tracking Number)
        resi_patterns = [
            r'\b(?:GK|IN)-\d+-[A-Z0-9-]+\b',
            r'\bIN-[A-Z0-9-]+\b',
            r'\b00\d{10,11}\b',
            r'\b1\d{12,13}\b',
            r'(?:SPXID|SPX|ID|JP|CBN|PLD|TJB|JX|CM|JNE|SHPE|SHP|NX)[\s:.]*[A-Z0-9]{7,25}',
            r'\b[A-Z]{2,4}\d{9,15}[A-Z]*\b',
            r'\b\d{10,15}\b'
        ]
        all_matches = []
        for pattern in resi_patterns:
            for m in re.finditer(pattern, text, re.IGNORECASE):
                val = m.group(0).strip()
                if len(val) >= 7:
                    all_matches.append(val)

        if all_matches:
            jx_matches = [m for m in all_matches if any(prefix in m.upper() for prefix in ["JX", "JP", "NLID", "SPX", "NX"])]
            resi_val = jx_matches[0] if jx_matches else all_matches[0]
            for char in [":", ".", ",", "(", ")"]:
                resi_val = resi_val.replace(char, " ")
            resi_val = re.sub(r'\s+', '', resi_val)
            if resi_val != page_data["nomor_pesanan"]:
                page_data["resi"] = resi_val.upper()

        # Extract Recipient Name (Penerima)
        penerima_node = next((w for w in words if "PENERIMA" in w['text'].upper() and "PENGIRIM" not in w['text'].upper()), None)
        if penerima_node:
            page_data["is_shipping_label"] = True
            target_y = penerima_node['top']
            line_words = [w for w in words if abs(w['top'] - target_y) < 5 and w['x0'] >= penerima_node['x0']]
            line_words.sort(key=lambda x: x['x0'])
            full_line_text = " ".join([w['text'] for w in line_words])
            name_part = re.sub(r'^[Pp]enerima\s*:\s*', '', full_line_text).strip()
            # DON'T split at asterisks (*) so we can keep masked names like A**a R**a
            name_clean = re.split(r'\(|\+\d+|PENGIRIM|KOTA|KAB\.', name_part, flags=re.IGNORECASE)[0].strip()
            page_data["penerima"] = name_clean or "UNKNOWN"

        # Identify 'Pengirim' node
        pengirim_node = next((w for w in words if "PENGIRIM" in w['text'].upper()), None)
        city_val = "NO_KOTA"
        line_text = ""
        
        if pengirim_node:
            page_data["is_shipping_label"] = True
            
            # Extract City (Kota) - Precise 'Detect Sender -> Scan Below -> Take Rightmost'
            target_y = pengirim_node['bottom']
            # Search precisely for the next line down
            below_words = [w for w in words if target_y < w['top'] < target_y + 18]
            
            if not below_words:
                # Fallback range if vertical spacing is larger
                below_words = [w for w in words if target_y < w['top'] < target_y + 30]
            
            if below_words:
                below_words.sort(key=lambda x: x['x0'])
                line_text = " ".join([w['text'] for w in below_words])
                
                # Filter Shop Name if it's somehow caught
                blacklist = ["BERKAH", "HERBALL", "STORE", "SHOP", "PENGIRIM"]
                is_likely_name = any(b in line_text.upper() for b in blacklist) or "," not in line_text
                
                if is_likely_name:
                    # Hop to the next line (Address line)
                    new_target_y = max(w['bottom'] for w in below_words)
                    below_words = [w for w in words if new_target_y < w['top'] < new_target_y + 25]
                    if below_words:
                        below_words.sort(key=lambda x: x['x0'])
                        line_text = " ".join([w['text'] for w in below_words])

                # Split and take the RIGHTMOST part
                parts = [p.strip() for p in re.split(r',|\s{2,}', line_text) if p.strip()]
                if parts:
                    # Take last, strip punctuation like trailing commas
                    raw_city = parts[-1].strip("., ")
                    city_val = re.sub(r'[^A-Z\s]', '', raw_city.upper()).strip()
                    # Check for generic province indicators to avoid them
                    provinces = ["TIMUR", "BARAT", "SELATAN", "UTARA", "TENGAH", "JAYA", "ISTIMEWA"]
                    if city_val in provinces and len(parts) >= 2:
                        city_val = re.sub(r'[^A-Z\s]', '', parts[-2].strip("., ").upper()).strip()

        # 2. Fallback to Destination address ONLY if sender city failed
        if not city_val or city_val == "NO_KOTA":
            for idx, line in enumerate(lines):
                if "weight" in line.lower() and idx > 0:
                    prev_line = lines[idx-1]
                    parts = [p.strip() for p in re.split(r',|\s{2,}', prev_line) if p.strip()]
                    if parts:
                        raw_city = parts[-1].strip("., ")
                        city_val = re.sub(r'[^A-Z\s]', '', raw_city.upper()).strip()
                    break
        
        # Final cleanup and Shop Name fallback
        if city_val:
            # 1. Remove "KOTA"
            city_val = re.sub(r'\bKOTA\b', '', city_val, flags=re.IGNORECASE).strip()
            # 2. Normalize KABUPATEN/KAB to KAB.
            city_val = re.sub(r'\bKABUPATEN\b', 'KAB.', city_val, flags=re.IGNORECASE)
            city_val = re.sub(r'\bKAB\b(?!\.)', 'KAB.', city_val, flags=re.IGNORECASE)
            
            shop_words = ["BERKAH", "HERBALL"]
            if any(sw in city_val.upper() for sw in shop_words):
                if "SAMARINDA" in line_text.upper(): city_val = "SAMARINDA"
                elif "JAKARTA" in line_text.upper(): city_val = "JAKARTA"
                elif "SURABAYA" in line_text.upper(): city_val = "SURABAYA"
                else: city_val = "NO_KOTA"
            
        page_data["kota"] = city_val or "NO_KOTA"

        # --- Find COD coordinates for label placement ---
        cod_word = next((w for w in words if w['text'].upper() == "COD"), None)
        if cod_word:
            page_data["cod_coords"] = {
                'x0': cod_word['x0'], 'top': cod_word['top'],
                'x1': cod_word['x1'], 'bottom': cod_word['bottom']
            }

        # --- Find crop_y: prioritized at "In transit by" or "Product Name" header ---
        transit_word = next((w for w in words if w['text'].lower() == "transit" and w['top'] > 200), None)
        product_name_word = next((w for w in words if "PRODUCT" in w['text'].upper() and w['top'] > 200), None)
        
        if transit_word:
            page_data["crop_y"] = transit_word['top'] - 4
        elif product_name_word:
            page_data["crop_y"] = product_name_word['top'] - 25 # Move up to cover "In transit" if it exists nearby
        else:
            # Fallback: check below Order Id / Estimated Date line
            order_id_words = [w for w in words if w['text'].lower() in ['order', 'estimated', 'date:'] and w['top'] > 250]
            if order_id_words:
                max_bottom = max(w['bottom'] for w in order_id_words)
                same_line_words = [w for w in words if abs(w['top'] - order_id_words[0]['top']) < 5]
                if same_line_words:
                    max_bottom = max(max_bottom, max(w['bottom'] for w in same_line_words))
                page_data["crop_y"] = max_bottom + 3

        # Extract Coordinates for fallback positioning
        for kw in ["Product Name", "Seller SKU", "Qty"]:
            matches = page.search(kw, case=False)
            if matches:
                page_data["sku_header_coords"] = matches[0]
                break
        
        matches = page.search("Penerima", case=False)
        if matches:
            page_data["penerima_coords"] = matches[0]
        
        matches = page.search("UNBOXING", case=False)
        if matches:
            page_data["unboxing_coords"] = matches[0]

        # Extract SKU items from product table
        header_idx = -1
        for idx, line in enumerate(lines):
            if "product name" in line.lower() and "qty" in line.lower():
                header_idx = idx
                break

        if header_idx != -1:
            for line in lines[header_idx+1:]:
                if any(k in line.lower() for k in ["order id:", "qty total:", "total qty:"]):
                    break
                parts = line.strip().split()
                if len(parts) >= 2:
                    if parts[-1].isdigit():
                        qty = int(parts[-1])
                        sku_candidate = parts[-2]
                        if any(c.isalpha() for c in sku_candidate) and len(sku_candidate) >= 2:
                            page_data["items"].append((sku_candidate, qty))

        return page_data

    def extract_data(self, pdf_path):
        results = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                # Phase 1: Extract raw data from ALL pages
                all_pages_raw = []
                self.log(f"Membaca {len(pdf.pages)} halaman PDF TikTok...")
                
                for i, page in enumerate(pdf.pages):
                    page_data = self._extract_page_raw(page, i)
                    if page_data:
                        all_pages_raw.append(page_data)
                    else:
                        self.log(f"Halaman {i+1}: Tidak ada teks terdeteksi.")

                # Phase 2: Group pages by Order ID and merge
                order_groups = {}  # order_id -> list of page_data (in page order)
                no_order_pages = []
                
                for pd in all_pages_raw:
                    oid = pd["nomor_pesanan"]
                    if oid:
                        if oid not in order_groups:
                            order_groups[oid] = []
                        order_groups[oid].append(pd)
                    else:
                        # Pages without Order ID - keep as standalone
                        no_order_pages.append(pd)

                self.log(f"Terdeteksi {len(order_groups)} order unik dari {len(all_pages_raw)} halaman.")

                # Phase 3: For each order, merge items into the first (shipping label) page
                for oid, pages in order_groups.items():
                    if not pages:
                        continue
                    
                    # Find the shipping label page (first page with Pengirim/Penerima)
                    shipping_page = None
                    for p in pages:
                        if p["is_shipping_label"]:
                            shipping_page = p
                            break
                    
                    # Fallback: use first page
                    if not shipping_page:
                        shipping_page = pages[0]
                    
                    # Merge items from ALL pages of this order into the shipping page
                    merged_items = []
                    for p in pages:
                        if p is shipping_page:
                            merged_items.extend(p["items"])
                        else:
                            # Items from continuation pages
                            merged_items.extend(p["items"])
                            self.log(f"Order {oid}: Menggabungkan SKU dari halaman {p['page_number']} ke halaman {shipping_page['page_number']}")
                    
                    shipping_page["items"] = merged_items
                    
                    # Propagate metadata from other pages if shipping page is missing data
                    for p in pages:
                        if p is shipping_page:
                            continue
                        if not shipping_page["resi"] and p["resi"]:
                            shipping_page["resi"] = p["resi"]
                        if shipping_page["penerima"] == "UNKNOWN" and p["penerima"] != "UNKNOWN":
                            shipping_page["penerima"] = p["penerima"]
                        if shipping_page["kota"] == "NO_KOTA" and p["kota"] != "NO_KOTA":
                            shipping_page["kota"] = p["kota"]
                        if not shipping_page["cod_coords"] and p.get("cod_coords"):
                            shipping_page["cod_coords"] = p["cod_coords"]
                        if not shipping_page["crop_y"] and p.get("crop_y"):
                            shipping_page["crop_y"] = p["crop_y"]

                    # Log what was found
                    if shipping_page["items"]:
                        item_str = ", ".join([f"{s}x{q}" for s, q in shipping_page["items"]])
                        self.log(f"Order {oid} (Hal.{shipping_page['page_number']}): Resi={shipping_page['resi']}, Items=[{item_str}]")
                        results.append(shipping_page)
                    else:
                        self.log(f"Order {oid}: Tidak ada SKU terdeteksi setelah merge.")

                # Add standalone pages (no Order ID)
                for pd in no_order_pages:
                    if pd["items"]:
                        results.append(pd)
                    else:
                        self.log(f"Halaman {pd['page_number']}: Tidak ada SKU terdeteksi.")

        except Exception as e:
            self.log(f"Error pembacaan PDF TikTok: {str(e)}")
        return results


class LazadaPDFReader:
    def __init__(self, logger=None):
        self._log = logger
        self.hub_cities = {
            "TBET": "JAKARTA", "CPTA": "JAKARTA", "BKLI": "MEDAN", "KDON": "PALEMBANG",
            "MDN": "MEDAN", "PLB": "PALEMBANG", "BDG": "BANDUNG", "BKI": "BEKASI",
            "BPN": "BALIKPAPAN", "SUB": "SURABAYA", "SBY": "SURABAYA", "JOG": "YOGYAKARTA",
            "SMG": "SEMARANG", "MGL": "MAGELANG", "MND": "MANADO", "MKS": "MAKASSAR",
            "TGR": "TANGERANG"
        }

    def log(self, message):
        if self._log:
            self._log(message)

    def extract_data(self, pdf_path):
        results = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                order_meta = {}

                for i, page in enumerate(pdf.pages):
                    page_data = {
                        "page_number": i + 1,
                        "resi": None,
                        "nomor_pesanan": None,
                        "items": [],
                        "sku_header_coords": None,
                        "unboxing_coords": None,
                        "penerima_coords": None,
                        "penerima": "UNKNOWN",
                        "kota": "NO_KOTA"
                    }
                    
                    text = page.extract_text()
                    if not text:
                        continue

                    # Extract Resi (LEX ID tracking number: 14-15 digit starting with 11, 12, 31 or LX)
                    resi_match = re.search(r'\b(1[123]\d{12})\b', text)
                    if resi_match:
                        page_data["resi"] = resi_match.group(1).strip()
                        self.log(f"Nomor Resi: {page_data['resi']}")
                    
                    if not page_data["resi"]:
                        lx_match = re.search(r'\b(LX[A-Z0-9]+)\b', text, re.IGNORECASE)
                        if lx_match:
                            page_data["resi"] = lx_match.group(1).upper()
                            self.log(f"Nomor Resi: {page_data['resi']}")

                    # Extract Recipient Name (Penerima)
                    words = page.extract_words()
                    penerima_node = next((w for w in words if "PENERIMA" in w['text'].upper() and "PENGIRIM" not in w['text'].upper()), None)
                    if penerima_node:
                        target_y = penerima_node['top']
                        line_words = [w for w in words if abs(w['top'] - target_y) < 5 and w['x0'] >= penerima_node['x0']]
                        line_words.sort(key=lambda x: x['x0'])
                        full_line_text = " ".join([w['text'] for w in line_words])
                        name_part = re.sub(r'^[Pp]enerima\s*:\s*', '', full_line_text).strip()
                        name_clean = re.split(r'\(|\+\d+|\*|PENGIRIM|KOTA|KAB\.', name_part, flags=re.IGNORECASE)[0].strip()
                        if name_clean:
                            page_data["penerima"] = name_clean
                            self.log(f"Penerima: {page_data['penerima']}")

                    # Extract Destination City (Kota)
                    words = page.extract_words()
                    words.sort(key=lambda w: (w['top'], w['x0']))
                    city_val = "NO_KOTA"
                    for idx, w in enumerate(words):
                        t_up = w['text'].upper()
                        if t_up in ["KOTA", "KAB."]:
                            context_prev = [nw['text'].upper() for nw in words[max(0, idx-5):idx]]
                            if "PENGIRIM" in context_prev or "TOKO" in context_prev:
                                continue
                            line_words = [nw for nw in words if abs(nw['top'] - w['top']) < 3 and nw['x0'] >= w['x0']]
                            line_words.sort(key=lambda x: x['x0'])
                            city_str = " ".join([nw['text'] for nw in line_words])
                            city_clean = city_str.strip()
                            city_clean = "".join([c for c in city_clean if not c.isdigit()]).strip()
                            # 1. Remove "KOTA"
                            city_clean = re.sub(r'\bKOTA\b', '', city_clean, flags=re.IGNORECASE).strip()
                            # 2. Normalize KABUPATEN/KAB to KAB.
                            city_clean = re.sub(r'\bKABUPATEN\b', 'KAB.', city_clean, flags=re.IGNORECASE)
                            city_clean = re.sub(r'\bKAB\b(?!\.)', 'KAB.', city_clean, flags=re.IGNORECASE)
                            if city_clean:
                                city_val = city_clean
                                break

                    # Fallback to hub code
                    if city_val == "NO_KOTA":
                        hub_match = re.search(r'\b([A-Z]{3,5})\d\s*\|\s*([A-Z]{3,5})\b', text)
                        if hub_match:
                            hub_code = hub_match.group(2).upper()
                            city_val = self.hub_cities.get(hub_code, hub_code)
                            self.log(f"Kota dideteksi dari Hub Code {hub_code} -> {city_val}")

                    page_data["kota"] = city_val
                    self.log(f"Kota Tujuan: {page_data['kota']}")

                    # Extract Coordinates
                    matches = page.search("SKU", case=False)
                    if matches:
                        page_data["sku_header_coords"] = matches[0]
                    
                    matches = page.search("Penerima", case=False)
                    if matches:
                        page_data["penerima_coords"] = matches[0]
                    
                    matches = page.search("UNBOXING", case=False)
                    if matches:
                        page_data["unboxing_coords"] = matches[0]

                    # Extract SKU items
                    lines = [line.strip() for line in text.splitlines() if line.strip()]
                    header_idx = -1
                    for idx, line in enumerate(lines):
                        if "#" in line and "sku" in line.lower() and "qty" in line.lower():
                            header_idx = idx
                            break
                    if header_idx == -1:
                        for idx, line in enumerate(lines):
                            if "sku" in line.lower() and "qty" in line.lower():
                                header_idx = idx
                                break

                    if header_idx != -1:
                        for line in lines[header_idx+1:]:
                            line = line.strip()
                            if not line:
                                continue
                            parts = line.split()
                            if len(parts) >= 3:
                                if parts[0].isdigit() and parts[-1].isdigit():
                                    qty = int(parts[-1])
                                    sku_parts = parts[1:-1]
                                    sku_candidate = " ".join(sku_parts).strip()
                                    if len(sku_candidate) >= 2:
                                        page_data["items"].append((sku_candidate, qty))
                                        self.log(f"Terbaca: SKU='{sku_candidate}', Qty={qty}")
                    
                    if page_data["items"]:
                        results.append(page_data)
                    else:
                        self.log(f"Halaman {i+1}: Tidak ada SKU terdeteksi.")

                    # Save metadata map
                    if page_data["resi"] and page_data["kota"] != "NO_KOTA":
                        order_meta["active"] = {
                            "resi": page_data["resi"],
                            "penerima": page_data["penerima"],
                            "kota": page_data["kota"]
                        }

                # Propagate LEX metadata
                for page_data in results:
                    if not page_data["resi"] and "active" in order_meta:
                        page_data["resi"] = order_meta["active"]["resi"]
                        page_data["penerima"] = order_meta["active"]["penerima"]
                        page_data["kota"] = order_meta["active"]["kota"]
                        self.log(f"Propagasi LEX Metadata -> Resi: {page_data['resi']}, Kota: {page_data['kota']}")

        except Exception as e:
            self.log(f"Error pembacaan PDF Lazada: {str(e)}")
        return results

