import streamlit as st
from PIL import Image
from io import BytesIO

st.set_page_config(page_title="Image to PDF Converter", page_icon="📄", layout="centered")

st.title("📸 Image to PDF Converter")
st.write("Upload your images below and download them as a single PDF file.")

# File uploader (multiple images)
uploaded_files = st.file_uploader(
    "Choose image files",
    type=["jpg", "jpeg", "png"],
    accept_multiple_files=True
)

if uploaded_files:
    # Show previews
    st.subheader("Uploaded Images Preview")
    cols = st.columns(3)
    for i, uploaded_file in enumerate(uploaded_files):
        img = Image.open(uploaded_file)
        cols[i % 3].image(img, caption=uploaded_file.name, use_container_width=True)

    # Convert to PDF button
    if st.button("🧾 Convert to PDF"):
        # Convert all uploaded images to RGB
        images = [Image.open(file).convert("RGB") for file in uploaded_files]

        # Save to in-memory file
        pdf_bytes = BytesIO()
        images[0].save(pdf_bytes, format="PDF", save_all=True, append_images=images[1:])
        pdf_bytes.seek(0)

        # Download button
        st.download_button(
            label="⬇️ Download PDF",
            data=pdf_bytes,
            file_name="converted_images.pdf",
            mime="application/pdf"
        )
