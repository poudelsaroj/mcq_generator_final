# file_processor.py
import os
import re
import tempfile
import base64
import fitz  # PyMuPDF
import docx
import pytesseract
from PIL import Image
from io import BytesIO
from typing import List, Dict, Any, Optional, Tuple

# Configure pytesseract path if needed (especially on Windows)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

class FileProcessor:
    """Process various file types for text extraction with OCR capabilities"""
    
    def __init__(self, ocr_enabled: bool = True):
        """Initialize file processor with OCR option"""
        self.ocr_enabled = ocr_enabled
    
    def process_file(self, file_content, file_name: str, file_type: str) -> dict:
        """
        Process file and extract text based on file type
        
        Args:
            file_content: Binary file content (already decoded from base64)
            file_name: Name of the file
            file_type: MIME type of the file
            
        Returns:
            Dict with extracted text
        """
        try:
            # Process based on file type
            if 'pdf' in file_type.lower() or file_name.lower().endswith('.pdf'):
                text = self.extract_text_from_pdf(file_content)
            elif 'word' in file_type.lower() or file_name.lower().endswith('.docx'):
                text = self.extract_text_from_docx(file_content)
            elif 'image' in file_type.lower() or any(file_name.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.bmp']):
                text = self.extract_text_from_image(file_content)
            elif 'text' in file_type.lower() or file_name.lower().endswith('.txt'):
                text = file_content.decode('utf-8', errors='ignore')
            else:
                return {"error": f"Unsupported file type: {file_type}"}
                
            return {"text": text}
        except Exception as e:
            return {"error": str(e)}
    
    def extract_text_from_pdf(self, binary_content: bytes) -> str:
        """Extract text from PDF with OCR fallback for scanned pages"""
        extracted_text = ""
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(binary_content)
            temp_file_path = temp_file.name
        
        try:
            # Open PDF with PyMuPDF
            doc = fitz.open(temp_file_path)
            
            for page_num, page in enumerate(doc):
                # Try normal text extraction first
                text = page.get_text()
                
                # If little or no text and OCR is enabled, try OCR
                if len(text.strip()) < 100 and self.ocr_enabled:
                    # Convert page to image
                    pix = page.get_pixmap(matrix=fitz.Matrix(2.0, 2.0))  # Increase resolution for better OCR
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    
                    # Apply OCR
                    ocr_text = pytesseract.image_to_string(img)
                    
                    # Use OCR text if it seems more substantial
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                
                extracted_text += text + "\n\n"
            
            return extracted_text
        finally:
            # Clean up temp file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def extract_text_from_docx(self, binary_content: bytes) -> str:
        """Extract text from DOCX file"""
        with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as temp_file:
            temp_file.write(binary_content)
            temp_file_path = temp_file.name
        
        try:
            doc = docx.Document(temp_file_path)
            full_text = []
            
            for para in doc.paragraphs:
                full_text.append(para.text)
            
            return '\n'.join(full_text)
        finally:
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)
    
    def extract_text_from_image(self, binary_content: bytes) -> str:
        """Extract text from image using OCR"""
        if not self.ocr_enabled:
            raise ValueError("OCR is disabled but required for image processing")
        
        # Open the image from binary content
        img = Image.open(BytesIO(binary_content))
        
        # Apply OCR
        text = pytesseract.image_to_string(img)
        return text
    
    def extract_text_from_pptx(self, binary_content: bytes) -> str:
        """Extract text from PPTX file (simplified implementation)"""
        # This is a placeholder for PPTX extraction
        # For a full implementation, you would use python-pptx
        return "PPTX text extraction not fully implemented yet."


class ChapterDetector:
    """Detect chapters in text and split content by chapters"""
    
    def __init__(self):
        """Initialize chapter detector"""
        # Patterns for chapter detection
        self.chapter_patterns = [
            r'(?:Chapter|CHAPTER)\s+(\d+|[IVX]+)[.\s:]*(.+)?',
            r'(?:Section|SECTION)\s+(\d+|[IVX]+)[.\s:]*(.+)?',
            r'^\s*(\d+|[IVX]+)\.\s*(.+)$',  # Numbered sections like "1. Introduction"
            r'^(Unit|Module|Part)\s+(\d+|[IVX]+)[.\s:]*(.+)?'
        ]
    
    def detect_is_book(self, text: str) -> bool:
        """
        Determine if the document is likely a book based on chapter structure
        
        Args:
            text: Extracted text from the document
            
        Returns:
            True if the document has multiple chapters and book-like structure
        """
        chapters = self.detect_chapters(text)
        
        # If we found multiple chapters with standard naming, likely a book
        if len(chapters) >= 3:
            return True
        
        # Check for other book indicators like TOC
        toc_patterns = [
            r'Table\s+of\s+Contents',
            r'Contents',
            r'TOC',
            r'Index'
        ]
        
        for pattern in toc_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        
        return False
    
    def detect_chapters(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect chapters in the text
        
        Args:
            text: Extracted text from the document
            
        Returns:
            List of chapters with title, number, and content
        """
        # Split text into lines for analysis
        lines = text.split('\n')
        
        # Find potential chapter headings
        chapters = []
        chapter_starts = []
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            for pattern in self.chapter_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    chapter_num = match.group(1)
                    title = match.group(2) if len(match.groups()) > 1 and match.group(2) else f"Chapter {chapter_num}"
                    
                    chapter_starts.append({
                        "line_idx": i,
                        "chapter_num": chapter_num,
                        "title": title
                    })
                    break
        
        # If no chapters found, treat entire text as one chapter
        if not chapter_starts:
            return [{
                "chapter_num": "1",
                "title": "Content",
                "content": text
            }]
        
        # Sort chapters by line index
        chapter_starts.sort(key=lambda x: x["line_idx"])
        
        # Extract content for each chapter
        for i, chapter in enumerate(chapter_starts):
            start_idx = chapter["line_idx"]
            end_idx = chapter_starts[i+1]["line_idx"] if i < len(chapter_starts) - 1 else len(lines)
            
            chapter_content = '\n'.join(lines[start_idx:end_idx])
            chapters.append({
                "chapter_num": chapter["chapter_num"],
                "title": chapter["title"],
                "content": chapter_content
            })
        
        return chapters

    def is_likely_book(self, text: str) -> bool:
        """Determine if the document is likely a book based on chapter structure"""
        # Check for chapter patterns
        chapters = self.extract_chapters(text)
        if len(chapters) >= 3:
            return True
            
        # Check for other book indicators like TOC
        toc_patterns = [r'Table\s+of\s+Contents', r'Contents', r'TOC', r'Index']
        for pattern in toc_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
                
        return False

    def extract_chapters(self, text: str) -> List[Dict[str, str]]:
        """Extract chapters from text"""
        # Implementation that returns a list of chapter dictionaries
        # Each should have 'title' and 'content' keys
        # ...
        # Define chapter patterns (chapter titles, headings)
        chapter_patterns = [
            r'(?:Chapter|CHAPTER)\s+(\d+|[IVX]+)[.\s:]*(.+)?',
            r'(?:Section|SECTION)\s+(\d+|[IVX]+)[.\s:]*(.+)?',
            r'^\s*(\d+|[IVX]+)\.\s*(.+)$',
            r'^(Unit|Module|Part)\s+(\d+|[IVX]+)[.\s:]*(.+)?'
        ]
        
        # Split text into lines
        lines = text.split('\n')
        chapter_starts = []
        
        # Find potential chapter headings
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            for pattern in chapter_patterns:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    num = match.group(1)
                    title = match.group(2) if len(match.groups()) > 1 and match.group(2) else f"Chapter {num}"
                    chapter_starts.append({
                        "index": i,
                        "title": title.strip()
                    })
                    break
        
        # If no chapters found, return whole text as one chapter
        if not chapter_starts:
            return [{"title": "Full Document", "content": text}]
        
        # Extract content for each chapter
        chapters = []
        for i, chapter in enumerate(chapter_starts):
            start = chapter["index"]
            end = chapter_starts[i+1]["index"] if i < len(chapter_starts)-1 else len(lines)
            
            content = '\n'.join(lines[start:end])
            chapters.append({
                "title": chapter["title"],
                "content": content
            })
        
        return chapters