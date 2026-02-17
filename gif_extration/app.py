import streamlit as st
from PIL import Image, ImageEnhance
import pytesseract
import pandas as pd
from io import BytesIO

# Optional: Set path to tesseract executable if needed (especially on Windows)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

st.title("📄 GIF Text Extractor to Excel")

uploaded_file = st.file_uploader("Upload a GIF file", type=["gif"])

if uploaded_file is not None:
    try:
        gif = Image.open(uploaded_file)
        st.image(gif, caption="Uploaded GIF", use_container_width=True)

        if gif.format != 'GIF':
            st.error("The uploaded file is not a valid GIF format.")
        else:
            frames = []
            try:
                while True:
                    frame = gif.copy()
                    frames.append(frame)
                    gif.seek(gif.tell() + 1)
            except EOFError:
                pass

            st.info(f"Total frames detected: {len(frames)}")
            max_frames = min(10, len(frames))  # Limit to first 10 frames

            extracted_data = []

            for idx, frame in enumerate(frames[:max_frames]):
                try:
                    frame = frame.convert("RGB")

                    # Resize large frames
                    max_size = (1500, 1500)
                    frame.thumbnail(max_size, Image.Resampling.LANCZOS)

                    # Preprocess for better OCR
                    gray = frame.convert("L")
                    contrast = ImageEnhance.Contrast(gray).enhance(2.0)
                    resized = contrast.resize((gray.width * 2, gray.height * 2))

                    # Display in Streamlit
                    st.image(resized, caption=f"Processed Frame {idx + 1}", use_container_width=True)

                    # Extract text using pytesseract
                    text = pytesseract.image_to_string(resized, config="--dpi 200")

                    st.markdown(f"**Text from Frame {idx + 1}:**")
                    st.code(text.strip())

                    extracted_data.append({
                        "Frame Number": idx + 1,
                        "Extracted Text": text.strip()
                    })

                except Exception as e:
                    st.error(f"Error with frame {idx + 1}: {e}")
                    extracted_data.append({
                        "Frame Number": idx + 1,
                        "Extracted Text": f"Error: {e}"
                    })

            # Create DataFrame
            if extracted_data:
                df = pd.DataFrame(extracted_data)
                st.dataframe(df)

                # Export to Excel
                def convert_df_to_excel(dataframe):
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='openpyxl') as writer:
                        dataframe.to_excel(writer, index=False, sheet_name='GIF_Text')
                    return output.getvalue()

                excel_data = convert_df_to_excel(df)

                st.download_button(
                    label="📥 Download Extracted Text as Excel",
                    data=excel_data,
                    file_name='gif_text_extraction.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            else:
                st.warning("No text extracted from the GIF.")
    except Exception as e:
        st.error(f"Something went wrong: {e}")
