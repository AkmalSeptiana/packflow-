import pdfplumber
import re

pdf_path = r"D:\PackFlow\resi 2 halaman.pdf"

try:
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n--- PAGE {i+1} ---")
            text = page.extract_text()
            print("TEXT:")
            print(text)
            
            # Check for '#' pattern
            hash_matches = re.findall(r'#\s*(\d+)', text)
            print(f"Hash matches: {hash_matches}")
            
            # Check for resi
            resi_patterns = [r'\b(?:SPXID|SPX|ID|JP|CBN|PLD|TJB|JX|CM|JNE|SHP|SHPE|NX)[\s:.]*[A-Z0-9]{7,25}', r'\b(?!08)(?:\s*\d){10,20}\b']
            for p in resi_patterns:
                m = re.search(p, text, re.IGNORECASE)
                if m:
                    print(f"Found Resi candidate: {m.group(0)}")

except Exception as e:
    print(f"Error: {e}")
