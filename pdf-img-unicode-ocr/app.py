import streamlit as st
import pytesseract
from PIL import Image
import pdf2image
import io
import os
from typing import List, Tuple
import gc
import unicodedata

# Configure page
st.set_page_config(
    page_title="OCR - Image & PDF Unicode Text Extraction",
    page_icon="📄",
    layout="wide"
)

st.title("📄 OCR - Image & PDF Unicode Text Extraction")
st.markdown("Upload images or PDFs to extract text with Unicode support")

# Sidebar for settings
with st.sidebar:
    st.header("Settings")
    
    # OCR language selection (for Tesseract) - Indian languages prioritized
    ocr_language = st.selectbox(
        "OCR Language",
        options=[
            # Indian Languages (prioritized)
            "mal",  # Malayalam
            "tam",  # Tamil
            "hin",  # Hindi
            "tel",  # Telugu
            "kan",  # Kannada
            "guj",  # Gujarati
            "pan",  # Punjabi
            "ben",  # Bengali
            "ori",  # Odia
            "asm",  # Assamese
            "eng+mal",  # English + Malayalam
            "eng+tam",  # English + Tamil
            "eng+hin",  # English + Hindi
            "eng+tel",  # English + Telugu
            "eng+kan",  # English + Kannada
            # Other languages
            "eng",
            "eng+chi_sim",
            "eng+chi_tra",
            "eng+jpn",
            "eng+kor",
            "eng+ara",
            "eng+rus",
            "eng+deu",
            "eng+fra",
            "eng+spa",
            "eng+ita",
            "eng+por",
            "eng+tha",
            "eng+vie"
        ],
        index=0,
        help="Select the language(s) for OCR. Indian languages output Unicode. Use '+' to combine multiple languages."
    )
    
    # Show language info
    if ocr_language in ["mal", "tam", "hin", "tel", "kan", "guj", "pan", "ben", "ori", "asm"]:
        st.info("🇮🇳 Indian language selected - Output will be in Unicode format")
    
    # DPI setting for PDF conversion
    pdf_dpi = st.slider(
        "PDF DPI",
        min_value=200,
        max_value=600,
        value=250,
        step=50,
        help="Higher DPI = better quality but slower processing. Lower DPI (200-250) recommended for large PDFs."
    )
    
    # PDF page range
    st.markdown("#### PDF Page Range")
    from_page = st.number_input(
        "From Page",
        min_value=1,
        max_value=10000,
        value=1,
        step=1,
        help="Start page number (1-based)"
    )
    to_page = st.number_input(
        "To Page",
        min_value=int(from_page),
        max_value=10000,
        value=int(from_page) + 49,
        step=1,
        help="End page number (inclusive). Keep the range small for faster OCR."
    )
    
    st.markdown("---")
    st.markdown("### Instructions")
    st.markdown("""
    1. Upload an image (PNG, JPG, JPEG) or PDF file
    2. Select your language (Malayalam, Tamil, Hindi, etc.)
    3. Click 'Extract Text' to perform OCR
    4. For PDFs, each page will be separated with '==== Page X =='
    5. Output will be in Unicode format
    """)
    
    st.markdown("---")
    st.markdown("### 📥 Install Indian Language Packs")
    st.markdown("""
    **Linux (Ubuntu/Debian):**
    ```bash
    sudo apt-get install tesseract-ocr-mal  # Malayalam
    sudo apt-get install tesseract-ocr-tam  # Tamil
    sudo apt-get install tesseract-ocr-hin  # Hindi
    sudo apt-get install tesseract-ocr-tel  # Telugu
    sudo apt-get install tesseract-ocr-kan  # Kannada
    sudo apt-get install tesseract-ocr-guj  # Gujarati
    sudo apt-get install tesseract-ocr-pan  # Punjabi
    sudo apt-get install tesseract-ocr-ben  # Bengali
    ```
    """)

def ensure_unicode(text: str) -> str:
    """Ensure text is properly Unicode encoded."""
    try:
        # Normalize Unicode characters
        text = unicodedata.normalize('NFC', text)
        # Ensure it's valid UTF-8
        text.encode('utf-8')
        return text
    except UnicodeEncodeError:
        # If encoding fails, try to fix it
        return text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')

def extract_text_from_image(image: Image.Image, lang: str = "eng", progress_bar=None) -> str:
    """Extract text from a PIL Image using Tesseract OCR. Returns Unicode text."""
    try:
        if progress_bar:
            progress_bar.progress(0.5, text="Running OCR on image...")
        
        # Use UTF-8 encoding explicitly for Indian languages
        text = pytesseract.image_to_string(image, lang=lang)
        
        # Ensure Unicode encoding
        text = ensure_unicode(text)
        
        if progress_bar:
            progress_bar.progress(1.0, text="OCR completed!")
        return text
    except Exception as e:
        if progress_bar:
            progress_bar.empty()
        error_msg = str(e)
        if "language" in error_msg.lower() or "lang" in error_msg.lower():
            st.error(f"❌ Language pack not installed. Please install tesseract-ocr-{lang.split('+')[0]} package.")
        else:
            st.error(f"Error during OCR: {error_msg}")
        return ""

def extract_text_from_pdf(
    pdf_file,
    lang: str = "eng",
    dpi: int = 300,
    first_page: int = 1,
    last_page: int = 50,
    progress_bar=None,
    status_text=None
) -> List[Tuple[int, str]]:
    """Extract text from PDF file, returning list of (page_number, text) tuples."""
    try:
        pdf_bytes = pdf_file.read()
        file_size_mb = len(pdf_bytes) / (1024 * 1024)
        
        if file_size_mb > 50:
            st.warning(f"⚠️ Large PDF detected ({file_size_mb:.1f} MB). Processing may take longer. Consider using lower DPI.")
        
        if progress_bar:
            progress_bar.progress(0.1, text="Converting PDF to images...")
        
        # Convert PDF to images with memory-efficient settings
        images = pdf2image.convert_from_bytes(
            pdf_bytes,
            dpi=dpi,
            thread_count=1,  # Reduce memory usage
            first_page=int(first_page),
            last_page=int(last_page)
        )
        
        total_pages = len(images)
        if total_pages == 0:
            return []

        # Note: total_pages here is the number of pages rendered in the requested range.
        if status_text:
            status_text.text(f"Rendered {total_pages} page(s) (requested {first_page} to {last_page})")
        
        results = []
        for offset, image in enumerate(images):
            page_num = int(first_page) + offset
            if progress_bar:
                progress = 0.1 + ((offset + 1) / total_pages) * 0.8
                progress_bar.progress(progress, text=f"Processing page {page_num} ({offset + 1} of {total_pages} in range)...")
            if status_text:
                status_text.text(f"Processing page {page_num} ({offset + 1}/{total_pages} in range)")
            
            try:
                # Extract text with Unicode support
                text = pytesseract.image_to_string(image, lang=lang)
                # Ensure Unicode encoding
                text = ensure_unicode(text)
                results.append((page_num, text))
            except Exception as e:
                error_msg = str(e)
                if "language" in error_msg.lower() or "lang" in error_msg.lower():
                    st.warning(f"⚠️ Page {page_num}: Language pack not installed. Install tesseract-ocr-{lang.split('+')[0]}")
                else:
                    st.warning(f"Error processing page {page_num}: {error_msg}")
                results.append((page_num, ""))
            
            # Free memory after each page
            del image
            gc.collect()
        
        # Free PDF images memory
        del images
        gc.collect()
        
        if progress_bar:
            progress_bar.progress(1.0, text="PDF processing completed!")
        
        return results
    except Exception as e:
        if progress_bar:
            progress_bar.empty()
        st.error(f"Error processing PDF: {str(e)}")
        return []

def main():
    uploaded_file = st.file_uploader(
        "Upload Image or PDF",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Supported formats: PNG, JPG, JPEG, PDF"
    )
    
    if uploaded_file is not None:
        file_type = uploaded_file.type
        
        # Display file info
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**File:** {uploaded_file.name}")
        with col2:
            st.info(f"**Type:** {file_type}")
        
        # File size warning
        uploaded_file.seek(0, 2)  # Seek to end
        file_size = uploaded_file.tell()
        uploaded_file.seek(0)  # Reset to beginning
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size_mb > 20:
            st.warning(f"⚠️ Large file detected ({file_size_mb:.1f} MB). Processing may take time. Consider using lower DPI for PDFs.")
        
        # Extract text button
        if st.button("🔍 Extract Text", type="primary", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            try:
                if file_type.startswith("image/"):
                    # Handle image files
                    try:
                        status_text.text("Loading image...")
                        progress_bar.progress(0.1, text="Loading image...")
                        
                        image = Image.open(io.BytesIO(uploaded_file.read()))
                        st.image(image, caption="Uploaded Image", use_container_width=True)
                        
                        progress_bar.progress(0.3, text="Image loaded. Starting OCR...")
                        
                        extracted_text = extract_text_from_image(image, lang=ocr_language, progress_bar=progress_bar)
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        if extracted_text.strip():
                            st.success("✅ Text extracted successfully!")
                            st.markdown("### Extracted Text (Unicode):")
                            # Display Unicode text properly
                            st.text_area(
                                "Text Output",
                                value=extracted_text,
                                height=400,
                                label_visibility="collapsed"
                            )
                            
                            # Show encoding info for Indian languages
                            if ocr_language in ["mal", "tam", "hin", "tel", "kan", "guj", "pan", "ben", "ori", "asm"]:
                                try:
                                    # Verify Unicode encoding
                                    extracted_text.encode('utf-8')
                                    st.success("✅ Text is properly encoded in Unicode (UTF-8)")
                                except:
                                    st.warning("⚠️ Encoding verification failed")
                            
                            # Download button (UTF-8 encoded)
                            st.download_button(
                                label="📥 Download Text (Unicode)",
                                data=extracted_text,
                                file_name=f"{os.path.splitext(uploaded_file.name)[0]}_extracted.txt",
                                mime="text/plain"
                            )
                        else:
                            st.warning("⚠️ No text found in the image.")
                        
                        # Free memory
                        del image
                        gc.collect()
                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"Error processing image: {str(e)}")
                
                elif file_type == "application/pdf":
                    # Handle PDF files
                    try:
                        uploaded_file.seek(0)  # Reset file pointer
                        status_text.text("Starting PDF processing...")
                        
                        page_results = extract_text_from_pdf(
                            uploaded_file,
                            lang=ocr_language,
                            dpi=pdf_dpi,
                            first_page=from_page,
                            last_page=to_page,
                            progress_bar=progress_bar,
                            status_text=status_text
                        )
                        
                        progress_bar.empty()
                        status_text.empty()
                        
                        if page_results:
                            st.success(f"✅ Text extracted from {len(page_results)} page(s)!")
                            
                            # Combine all pages with separators
                            full_text = ""
                            for page_num, text in page_results:
                                full_text += f"==== Page {page_num} ==\n\n"
                                full_text += text
                                full_text += "\n\n"
                            
                            st.markdown("### Extracted Text (Unicode):")
                            st.text_area(
                                "Text Output",
                                value=full_text,
                                height=600,
                                label_visibility="collapsed"
                            )
                            
                            # Show encoding info for Indian languages
                            if ocr_language in ["mal", "tam", "hin", "tel", "kan", "guj", "pan", "ben", "ori", "asm"]:
                                try:
                                    # Verify Unicode encoding
                                    full_text.encode('utf-8')
                                    st.success("✅ Text is properly encoded in Unicode (UTF-8)")
                                except:
                                    st.warning("⚠️ Encoding verification failed")
                            
                            # Download button (UTF-8 encoded)
                            st.download_button(
                                label="📥 Download Text (Unicode)",
                                data=full_text,
                                file_name=f"{os.path.splitext(uploaded_file.name)[0]}_extracted.txt",
                                mime="text/plain"
                            )
                            
                            # Show page-by-page breakdown
                            with st.expander("📑 View by Page"):
                                for page_num, text in page_results:
                                    st.markdown(f"#### Page {page_num}")
                                    st.text(text)
                                    st.markdown("---")
                        else:
                            st.warning("⚠️ No text found in the PDF.")
                    except Exception as e:
                        progress_bar.empty()
                        status_text.empty()
                        st.error(f"Error processing PDF: {str(e)}")
                        st.info("💡 Make sure you have poppler-utils installed: `sudo apt-get install poppler-utils` (Linux) or `brew install poppler` (Mac)")
                else:
                    progress_bar.empty()
                    status_text.empty()
                    st.error("Unsupported file type. Please upload PNG, JPG, JPEG, or PDF.")
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"Unexpected error: {str(e)}")
            finally:
                # Final cleanup
                gc.collect()

if __name__ == "__main__":
    main()
