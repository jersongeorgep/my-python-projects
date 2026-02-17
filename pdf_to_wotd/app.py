import streamlit as st
from pdf2image import convert_from_path, pdfinfo_from_path
import pytesseract
from docx import Document
import re
import tempfile
import os

# Function to clean text
def clean_text(text: str) -> str:
    """Remove NULL and non-XML-compatible control characters"""
    return re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F]', '', text)

# Streamlit App
st.set_page_config(page_title="Malayalam PDF to DOCX OCR", layout="centered")
st.title("📄 Malayalam OCR: PDF to Word Converter")

# File uploader
uploaded_pdf = st.file_uploader("Upload PDF file", type=["pdf"])

if uploaded_pdf:
    # Temporary save of uploaded file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_pdf:
        tmp_pdf.write(uploaded_pdf.read())
        tmp_pdf_path = tmp_pdf.name

    # Output path for DOCX
    doc = Document()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tmp_docx:
        docx_path = tmp_docx.name

    try:
        # Get total pages
        pdf_info = pdfinfo_from_path(tmp_pdf_path)
        total_pages = pdf_info["Pages"]

        with st.spinner(f"Processing {total_pages} pages..."):
            for i in range(1, total_pages + 1):
                st.info(f"🔍 OCR on page {i}/{total_pages}...")

                # Convert page to image
                pages = convert_from_path(tmp_pdf_path, dpi=300, first_page=i, last_page=i)
                raw_text = pytesseract.image_to_string(pages[0], lang='mal')
                text = clean_text(raw_text)

                if text.strip():
                    doc.add_paragraph(text)
                doc.add_page_break()

            # Save the DOCX file
            doc.save(docx_path)
            st.success("✅ Done! Document is ready to download.")

            # Provide download button
            with open(docx_path, "rb") as f:
                st.download_button("📥 Download Word Document", f, file_name="output.docx")

    except Exception as e:
        st.error(f"❌ Error: {e}")

    # Clean up
    finally:
        os.remove(tmp_pdf_path)
        if os.path.exists(docx_path):
            os.remove(docx_path)