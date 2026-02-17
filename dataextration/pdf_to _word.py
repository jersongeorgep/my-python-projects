from pdf2image import convert_from_path
import pytesseract
from docx import Document
import re
from pdf2image.pdf2image import pdfinfo_from_path

def clean_text(text: str) -> str:
    """Remove NULL and non-XML-compatible control characters"""
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)

# Input / Output paths
pdf_file = "/home/allianze/Downloads/output_image_pdf.pdf"
docx_file = "/home/allianze/Downloads/output.docx"

# Create Word document
doc = Document()

# Get total number of pages
pdf_info = pdfinfo_from_path(pdf_file)
total_pages = pdf_info["Pages"]

for i in range(1, total_pages + 1):
    print(f"Processing page {i}/{total_pages}...")

    # Convert one page at a time (saves memory)
    pages = convert_from_path(pdf_file, dpi=300, first_page=i, last_page=i)
    
    # OCR with Malayalam
    raw_text = pytesseract.image_to_string(pages[0], lang='mal')
    
    # Clean invalid characters
    text = clean_text(raw_text)

    # Add text to Word
    if text.strip():  # skip empty pages
        doc.add_paragraph(text)
    doc.add_page_break()

# Save Word file
doc.save(docx_file)
print(f"✅ Done! Saved at {docx_file}")