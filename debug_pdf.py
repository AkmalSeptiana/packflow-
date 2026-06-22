import pdfplumber
import re

pdf_path = r"D:\PackFlow\revisi.pdf"
output_file = r"D:\PackFlow\debug_output.txt"

def log(msg):
    with open(output_file, "a") as f:
        f.write(msg + "\n")
    print(msg)

# Clear file
open(output_file, "w").close()

try:
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            log(f"\n--- PAGE {i+1} ---")
            text = page.extract_text()
            if not text:
                log("No text found.")
                continue
            
            log(f"RAW TEXT (total chars: {len(text)})")
            log(text)
            log("-" * 30)
            
            # Find all sequences of digits, spaces, and 'C', 'O', 'I', 'L' (common mangles)
            # focusing on things that might be a tracking number
            potential = re.findall(r'[A-Z0-9\s-]{10,30}', text)
            log("POTENTIAL SEQUENCES:")
            for p in potential:
                clean = re.sub(r'[^A-Z0-9-]', '', p.strip())
                if len(clean) >= 10:
                    log(f"  Raw: '{p.strip()}' -> Clean: '{clean}'")

except Exception as e:
    log(f"Error: {e}")
