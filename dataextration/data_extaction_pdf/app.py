import streamlit as st
import fitz  # PyMuPDF
import pytesseract
from PIL import Image
import io
import pandas as pd
from docx import Document
from openai import OpenAI
import tempfile
import os

# -------------------------------
# 🔑 OpenAI API Key
# -------------------------------
# Replace YOUR_API_KEY with your actual key
client = OpenAI(api_key="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")

# -------------------------------
# ⚙️ Helper Functions
# -------------------------------
def extract_text_from_pdf(pdf_file):
    """Extract text from a PDF (with OCR for image-based pages)."""
    text_output = ""

    # Create temporary file for reading PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_file.read())
        tmp_path = tmp.name

    doc = fitz.open(tmp_path)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text").strip()

        # If no selectable text, use OCR on the page image
        if not text:
            pix = page.get_pixmap()
            img = Image.open(io.BytesIO(pix.tobytes("png")))
            text = pytesseract.image_to_string(img)

        text_output += f"\n\n--- Page {page_num + 1} ---\n{text}"

    doc.close()
    os.unlink(tmp_path)
    return text_output


def process_with_prompt(extracted_text, prompt_instruction):
    """Send extracted text to GPT for intelligent processing."""
    full_prompt = f"{prompt_instruction}\n\nDocument content:\n{extracted_text[:20000]}"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are an expert document assistant."},
            {"role": "user", "content": full_prompt}
        ]
    )

    return response.choices[0].message.content


def save_to_excel(text):
    """Save extracted text to Excel file."""
    df = pd.DataFrame({"Extracted_Text": text.splitlines()})
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(tmp.name, index=False)
    return tmp.name


def save_to_word(text):
    """Save text to a Word document."""
    doc = Document()
    doc.add_paragraph(text)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".docx")
    doc.save(tmp.name)
    return tmp.name


# -------------------------------
# 🧠 Streamlit User Interface
# -------------------------------
st.set_page_config(page_title="AI PDF Text Extractor", layout="wide")

st.title("📄 AI PDF Text Extractor & Processor")
st.markdown("Upload a PDF file (with text or images), enter your prompt, and download the result as text, Excel, or Word.")

uploaded_pdf = st.file_uploader("📤 Select your PDF file", type=["pdf"])
prompt = st.text_area("🧠 Enter your prompt (optional)", placeholder="e.g., Summarize document or extract tables to Excel...")
output_type = st.selectbox("Select Output Type", ["Text", "Excel", "Word"])

if st.button("🚀 Extract and Process"):
    if not uploaded_pdf:
        st.warning("Please upload a PDF file first.")
    else:
        with st.spinner("Extracting text... This may take a while ⏳"):
            extracted_text = extract_text_from_pdf(uploaded_pdf)

        st.success("✅ Text extraction complete!")

        if prompt.strip():
            with st.spinner("Processing with AI... 🤖"):
                processed_text = process_with_prompt(extracted_text, prompt)
        else:
            processed_text = extracted_text

        # Display and download
        if output_type == "Text":
            st.text_area("📝 Extracted Text / AI Output", processed_text[:10000], height=400)
            st.download_button("⬇️ Download as Text", processed_text, "output.txt")

        elif output_type == "Excel":
            excel_path = save_to_excel(processed_text)
            with open(excel_path, "rb") as f:
                st.download_button("⬇️ Download as Excel", f, "output.xlsx")

        elif output_type == "Word":
            word_path = save_to_word(processed_text)
            with open(word_path, "rb") as f:
                st.download_button("⬇️ Download as Word", f, "output.docx")
