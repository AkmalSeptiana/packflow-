import re

class SKUParser:
    def __init__(self, ignored_skus=None, default_suffix="ARY", sku_whitelist=None):
        self.ignored_skus = [s.upper() for s in (ignored_skus or [])]
        self.default_suffix = default_suffix
        self.sku_whitelist = [s.upper() for s in (sku_whitelist or [])]

    def parse_line(self, sku_str, qty):
        sku_str = sku_str.strip()
        if not sku_str or any(ignored in sku_str.upper() for ignored in self.ignored_skus):
            return []

        # 1. Isolate all alphanumeric clusters
        raw_parts = re.findall(r'[A-Z0-9]{1,}', sku_str.upper())
        
        results = []
        active_internal_mult = 1
        found_suffix = self.default_suffix
        
        # 2. Determine Suffix (Last word longer than 1 char, not in whitelist, not a number)
        for p in reversed(raw_parts):
            if p not in self.sku_whitelist and not p.isdigit() and p not in self.ignored_skus and len(p) >= 2:
                found_suffix = p
                break

        # 3. Process parts with Smart Splitting (Handle 1AQU, 3HEX, etc.)
        for i, p in enumerate(raw_parts):
            # A. Standalone Digit
            if p.isdigit():
                # Ignore row number (standalone '1' at the very beginning)
                if i == 0 and p == "1" and len(raw_parts) > 1:
                    continue
                active_internal_mult = int(p)
                continue
            
            # B. Glued Digit + Product (e.g. 1AQU, 2HEX)
            # We try to split it into (Number) and (Brand)
            match = re.match(r'^(\d+)([A-Z]+)$', p)
            if match:
                m_val = int(match.group(1))
                internal_name = match.group(2)
                if internal_name in self.sku_whitelist:
                    results.append({
                        "name": internal_name,
                        "total_qty": m_val * qty,
                        "suffix": found_suffix
                    })
                    active_internal_mult = 1
                    continue

            # C. Standalone Product Name
            if p in self.sku_whitelist:
                results.append({
                    "name": p,
                    "total_qty": active_internal_mult * qty,
                    "suffix": found_suffix
                })
                active_internal_mult = 1 # Reset
        
        return results

    def build_label(self, parsed_items):
        if not parsed_items:
            return ""

        grouped = {}
        suffixes = set()
        
        for item in parsed_items:
            name = item['name']
            grouped[name] = grouped.get(name, 0) + item['total_qty']
            suffixes.add(item['suffix'])

        suffix_str = self.default_suffix if self.default_suffix else (" + ".join(sorted(list(suffixes))) if suffixes else "")
        suffix_str = suffix_str.strip('.')

        components = []
        for name, qty in grouped.items():
            components.append(f"{qty}-{name}")

        if len(components) == 1:
            return f"{components[0]}-{suffix_str}"
        else:
            label = " + ".join(components)
            return f"{label} - {suffix_str}" if label else ""
