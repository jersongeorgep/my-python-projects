# OCR - Image & PDF Unicode Text Extraction

A Streamlit application for extracting text from images and PDFs using OCR with Unicode support.

## Features

- 📸 **Image OCR**: Extract text from PNG, JPG, JPEG images
- 📄 **PDF OCR**: Extract text from PDF files with page separations
- 🇮🇳 **Indian Language Support**: Full support for Malayalam, Tamil, Hindi, Telugu, Kannada, Gujarati, Punjabi, Bengali, Odia, Assamese
- 🌐 **Unicode Conversion**: Converts non-Unicode fonts (ISCII, legacy fonts) to proper Unicode format
- 📑 **Page Separations**: PDF pages are clearly marked with "==== Page X ===" separators
- 💾 **Download Results**: Download extracted text as .txt files with UTF-8 encoding

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Install Tesseract OCR

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr

# Install Indian language packs
sudo apt-get install tesseract-ocr-mal  # Malayalam
sudo apt-get install tesseract-ocr-tam  # Tamil
sudo apt-get install tesseract-ocr-hin  # Hindi
sudo apt-get install tesseract-ocr-tel  # Telugu
sudo apt-get install tesseract-ocr-kan  # Kannada
sudo apt-get install tesseract-ocr-guj  # Gujarati
sudo apt-get install tesseract-ocr-pan  # Punjabi
sudo apt-get install tesseract-ocr-ben  # Bengali
sudo apt-get install tesseract-ocr-ori  # Odia
sudo apt-get install tesseract-ocr-asm  # Assamese

# Other languages
sudo apt-get install tesseract-ocr-chi-sim tesseract-ocr-jpn  # Chinese, Japanese, etc.
```

**macOS:**
```bash
brew install tesseract
brew install tesseract-lang  # For additional languages
```

**Windows:**
Download and install from: https://github.com/UB-Mannheim/tesseract/wiki

### 3. Install Poppler (for PDF processing)

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get install poppler-utils
```

**macOS:**
```bash
brew install poppler
```

**Windows:**
Download from: https://github.com/oschwartz10612/poppler-windows/releases/

## Usage

1. Run the Streamlit app:
```bash
streamlit run app.py
```

2. Open your browser to the URL shown (usually http://localhost:8501)

3. Upload an image or PDF file

4. Select OCR language(s) from the sidebar

5. Click "Extract Text" to perform OCR

6. View and download the extracted text

## Supported Languages

### Indian Languages (Unicode Output)
- **Malayalam** (mal) - മലയാളം
- **Tamil** (tam) - தமிழ்
- **Hindi** (hin) - हिन्दी
- **Telugu** (tel) - తెలుగు
- **Kannada** (kan) - ಕನ್ನಡ
- **Gujarati** (guj) - ગુજરાતી
- **Punjabi** (pan) - ਪੰਜਾਬੀ
- **Bengali** (ben) - বাংলা
- **Odia** (ori) - ଓଡ଼ିଆ
- **Assamese** (asm) - অসমীয়া

### Other Languages
- English (eng)
- Chinese Simplified (chi_sim)
- Chinese Traditional (chi_tra)
- Japanese (jpn)
- Korean (kor)
- Arabic (ara)
- Russian (rus)
- German (deu)
- French (fra)
- Spanish (spa)
- Italian (ita)
- Portuguese (por)
- Thai (tha)
- Vietnamese (vie)

You can combine languages using '+' (e.g., "eng+mal" for English and Malayalam, "eng+hin" for English and Hindi).

## Unicode Conversion for Indian Languages

This tool automatically converts non-Unicode fonts (like ISCII or legacy fonts) to proper Unicode format:
- **Malayalam**: Converts legacy fonts to Unicode Malayalam (മലയാളം)
- **Tamil**: Converts legacy fonts to Unicode Tamil (தமிழ்)
- **Hindi**: Converts legacy fonts to Unicode Hindi (हिन्दी)
- And other Indian languages...

The OCR output is always in Unicode (UTF-8) format, ensuring compatibility with modern applications and text editors.

## Notes

- For PDFs, each page will be separated with "==== Page X ===" markers
- Images don't have page separations
- Higher DPI settings provide better OCR accuracy but take longer to process
- Make sure Tesseract OCR and Poppler are properly installed and accessible in your system PATH
- For Indian languages, ensure the corresponding language pack is installed (e.g., `tesseract-ocr-mal` for Malayalam)
- The output text is always in Unicode format, ready for use in any modern application
