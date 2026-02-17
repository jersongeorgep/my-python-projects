import streamlit as st
import fitz  # PyMuPDF
import io
from PIL import Image

st.set_page_config(page_title="PDF Extractor", layout="wide")
st.title("📄 PDF Text & Image Extractor")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file:
    doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
    all_text = []

    st.subheader("📜 Extracted Text")
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text()
        if text:
            all_text.append(f"\n--- Page {page_num} ---\n{text}")
    
    if all_text:
        joined_text = "\n".join(all_text)
        st.text_area("Unicode Text Output", joined_text, height=400)
    else:
        st.warning("No text found in the PDF.")

    st.subheader("🖼️ Extracted Images")
    img_count = 0
    for page in doc:
        images = page.get_images(full=True)
        for img_index, img in enumerate(images):
            xref = img[0]
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image = Image.open(io.BytesIO(image_bytes))

            img_count += 1
            st.image(image, caption=f"Page {page.number + 1} - Image {img_index + 1}", use_container_width=True)

    if img_count == 0:
        st.info("No images found in the PDF.")