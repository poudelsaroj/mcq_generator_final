# fileprocessor.py

import os
import tempfile
import base64
import fitz  # PyMuPDF
import docx
import pytesseract
from PIL import Image
from io import BytesIO
from typing import Dict, Any

class FileProcessor:
    """Processes PDFs, DOCX, images, or text files to extract text. Supports OCR if needed."""

    def __init__(self, ocr_enabled: bool = True):
        self.ocr_enabled = ocr_enabled

    def process_file(self, file_content: bytes, file_name: str, file_type: str) -> Dict[str, Any]:
        """
        Determines file type and extracts text accordingly.
        """
        try:
            ft_lower = file_type.lower()
            fn_lower = file_name.lower()

            if 'pdf' in ft_lower or fn_lower.endswith('.pdf'):
                text = self.extract_text_from_pdf(file_content)
            elif 'word' in ft_lower or fn_lower.endswith('.docx'):
                text = self.extract_text_from_docx(file_content)
            elif ('image' in ft_lower or fn_lower.endswith(('.jpg', '.jpeg', '.png', '.bmp'))):
                text = self.extract_text_from_image(file_content)
            elif 'text' in ft_lower or fn_lower.endswith('.txt'):
                text = file_content.decode('utf-8', errors='ignore')
            else:
                return {"error": f"Unsupported file type: {file_type}"}

            return {"text": text}
        except Exception as e:
            return {"error": str(e)}

    def process_file_with_enhanced_ocr(self, file_content: bytes, file_name: str, file_type: str, dpi: int = 300) -> Dict[str, Any]:
        """
        Enhanced OCR processing for difficult files, using higher quality settings
        for better text recognition.
        """
        try:
            ft_lower = file_type.lower()
            fn_lower = file_name.lower()

            # For PDF files, use an enhanced OCR approach
            if 'pdf' in ft_lower or fn_lower.endswith('.pdf'):
                text = self.extract_text_from_pdf_with_enhanced_ocr(file_content, dpi)
            # For images, use enhanced OCR
            elif ('image' in ft_lower or fn_lower.endswith(('.jpg', '.jpeg', '.png', '.bmp'))):
                text = self.extract_text_from_image_with_enhanced_ocr(file_content, dpi)
            else:
                # Fall back to standard processing for other file types
                return self.process_file(file_content, file_name, file_type)

            return {"text": text}
        except Exception as e:
            return {"error": str(e)}

    def extract_text_from_pdf(self, binary_content: bytes) -> str:
        """Extracts text from PDF using PyMuPDF, with OCR fallback if necessary."""
        extracted_text = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tempf:
            tempf.write(binary_content)
            temp_path = tempf.name

        try:
            doc = fitz.open(temp_path)
            for page in doc:
                text = page.get_text()
                if len(text.strip()) < 100 and self.ocr_enabled:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    text = pytesseract.image_to_string(img)
                extracted_text += text + "\n"
            return extracted_text
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def extract_text_from_pdf_with_enhanced_ocr(self, binary_content: bytes, dpi: int = 300) -> str:
        """
        Extracts text from PDF with enhanced OCR settings for better quality.
        Always uses OCR on every page with high-quality settings.
        """
        extracted_text = ""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tempf:
            tempf.write(binary_content)
            temp_path = tempf.name

        try:
            doc = fitz.open(temp_path)
            for page in doc:
                # Always use OCR for every page with higher resolution
                pix = page.get_pixmap(matrix=fitz.Matrix(dpi/72, dpi/72))
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                
                # Configure pytesseract with better settings
                custom_config = r'--oem 3 --psm 6 -l eng'  # OEM 3 = default OCR engine, PSM 6 = assume single uniform block of text
                text = pytesseract.image_to_string(img, config=custom_config)
                
                extracted_text += text + "\n"
            return extracted_text
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def extract_text_from_docx(self, binary_content: bytes) -> str:
        """Extracts text from DOCX files."""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".docx") as tempf:
            tempf.write(binary_content)
            temp_path = tempf.name

        try:
            doc = docx.Document(temp_path)
            return "\n".join([para.text for para in doc.paragraphs])
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def extract_text_from_image(self, binary_content: bytes) -> str:
        """Extracts text from an image via OCR."""
        img = Image.open(BytesIO(binary_content))
        return pytesseract.image_to_string(img)

    def extract_text_from_image_with_enhanced_ocr(self, binary_content: bytes, dpi: int = 300) -> str:
        """
        Extracts text from an image using enhanced OCR settings.
        """
        img = Image.open(BytesIO(binary_content))
        
        # Calculate new dimensions based on DPI (if needed)
        if dpi != 72:  # Standard screen DPI
            factor = dpi / 72
            new_width = int(img.width * factor)
            new_height = int(img.height * factor)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Use better OCR config
        custom_config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(img, config=custom_config)
