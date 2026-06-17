import pdfplumber

pdf_path = r'C:\Users\Administrator\Downloads\Telegram Desktop\JB CONTOH.pdf'
with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages):
        print(f"--- Page {i+1} ---")
        words = page.extract_words()
        for w in words:
            print(f"{w['text']} ({w['x0']:.1f}, {w['top']:.1f})")
