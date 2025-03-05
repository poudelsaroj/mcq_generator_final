# api.py

from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect, File, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import base64
import json
from fileprocessor import FileProcessor
from mcq_generator import MCQGenerator

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="MCQ Generator API")

# Initialize components
file_processor = FileProcessor(ocr_enabled=True)
mcq_generator = MCQGenerator(
    qa_model_path="./qa",
    distractor_model_path="./distractor",
    openrouter_api_key=""
)

# CORS for dev – adjust in production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FileInput(BaseModel):
    file_content: str  # Base64-encoded
    file_name: str
    file_type: str
    document_type: str = "document"
    num_questions: int = 5

class MCQInput(BaseModel):
    text: str
    num_questions: int = 5

# Add this new class
class OCRFileInput(BaseModel):
    file_content: str  # Base64-encoded
    file_name: str
    file_type: str
    force_ocr: bool = False
    dpi: int = 300  # Higher DPI for better OCR

class ConnectionManager:
    """Handles WebSocket connections for real-time updates"""
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_json(self, client_id: str, message: Dict[str, Any]):
        ws = self.active_connections.get(client_id)
        if ws:
            try:
                await ws.send_json(message)
            except Exception as e:
                print(f"[DEBUG] Error sending WS message to {client_id}: {e}")

manager = ConnectionManager()

@app.post("/process-file")
def process_file_sync(file_input: FileInput):
    """
    Extracts text from a file (PDF, DOCX, TXT, Image).
    Returns extracted text or an error message.
    """
    try:
        file_bytes = base64.b64decode(file_input.file_content)
        result = file_processor.process_file(
            file_content=file_bytes,
            file_name=file_input.file_name,
            file_type=file_input.file_type
        )
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        return {"text": result["text"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not process file: {str(e)}")

@app.post("/process-file-ocr")
def process_file_with_ocr(file_input: OCRFileInput):
    """
    Enhanced endpoint that applies OCR to extract text from PDF files
    that couldn't be processed with standard methods.
    """
    try:
        file_bytes = base64.b64decode(file_input.file_content)
        
        # Create a FileProcessor with OCR explicitly enabled
        ocr_processor = FileProcessor(ocr_enabled=True)
        
        # Process with enhanced OCR settings
        result = ocr_processor.process_file_with_enhanced_ocr(
            file_content=file_bytes,
            file_name=file_input.file_name,
            file_type=file_input.file_type,
            dpi=file_input.dpi
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
            
        return {"text": result["text"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not process file with OCR: {str(e)}")

@app.websocket("/api/ws/{client_id}")
async def websocket_file_endpoint(websocket: WebSocket, client_id: str):
    """
    WebSocket endpoint for file processing.
    """
    print(f"[DEBUG] WebSocket connected: client_id={client_id}")
    await manager.connect(client_id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            print(f"[DEBUG] WS msg from {client_id}: {data[:100]}...")
            try:
                message = json.loads(data)
                if message.get("command") == "process_file":
                    await manager.send_json(client_id, {"status": "Processing started", "message": "Reading file..."})
                    file_bytes = base64.b64decode(message["file_content"])
                    
                    # Extract document type explicitly from the message
                    document_type = message.get("document_type", "document")
                    is_book = document_type == "book"
                    
                    await manager.send_json(client_id, {"status": "processing", "message": "Extracting text..."})
                    result = file_processor.process_file(
                        file_content=file_bytes,
                        file_name=message["file_name"],
                        file_type=message["file_type"]
                    )
                    
                    if "error" in result:
                        await manager.send_json(client_id, {"status": "error", "message": result["error"]})
                        continue

                    # For PDFs, try to detect chapters
                    chapters = []
                    text = result.get("text", "")
                    
                    # If it's a PDF and requested as a book, try to identify chapters
                    if is_book and message["file_name"].lower().endswith('.pdf'):
                        await manager.send_json(client_id, {"status": "processing", "message": "Detecting chapters..."})
                        try:
                            # Try to detect chapters
                            chapter_texts = detect_chapters(text)
                            if len(chapter_texts) > 1:
                                for i, chapter_text in enumerate(chapter_texts):
                                    chapters.append({
                                        "title": f"Chapter {i+1}",
                                        "content": chapter_text.strip()
                                    })
                                await manager.send_json(client_id, 
                                    {"status": "processing", 
                                     "message": f"Found {len(chapters)} chapters"})
                        except Exception as e:
                            print(f"[DEBUG] Chapter detection error: {str(e)}")
                            # If chapter detection fails, don't fail the whole process
                            pass
                    
                    # If no chapters detected or not a book, use whole text as one chapter
                    if not chapters:
                        if is_book:
                            # If it was supposed to be a book but no chapters found
                            print(f"[DEBUG] No chapters found in book-type document")
                            # Create artificial chapters by size for better UX
                            chapters = create_artificial_chapters(text)
                        else:
                            # Regular document, just use the whole text
                            chapters = [{"content": text, "title": message["file_name"]}]

                    # Format response properly for frontend expectations
                    formatted_result = {
                        "status": "complete", 
                        "text": text,
                        "chapters": chapters,
                        "is_book": is_book or len(chapters) > 1
                    }
                    await manager.send_json(client_id, formatted_result)
                else:
                    await manager.send_json(client_id, {"status": "error", "message": f"Unknown command"})
            except json.JSONDecodeError:
                await manager.send_json(client_id, {"status": "error", "message": "Invalid JSON format"})
            except Exception as e:
                error_msg = f"Processing error: {str(e)}"
                print(f"[DEBUG] {error_msg}")
                await manager.send_json(client_id, {"status": "error", "message": error_msg})
    except WebSocketDisconnect:
        print(f"[DEBUG] WS disconnected: client_id={client_id}")
        manager.disconnect(client_id)
    except Exception as e:
        print(f"[DEBUG] WS error: {e}")
        manager.disconnect(client_id)

# Add this helper function to detect chapters in text
def detect_chapters(text):
    """
    Enhanced chapter detection that specifically handles TOC with page numbers
    and finds chapter boundaries based on content structure.
    """
    import re
    from collections import Counter
    import nltk
    from nltk.tokenize import sent_tokenize
    
    # Download nltk resources if needed
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        nltk.download('punkt')
    
    # Split text into lines for analysis
    lines = text.split('\n')
    
    # 1. First Strategy: Find and utilize Table of Contents
    toc_patterns = [
        r'(?i)^\s*table\s+of\s+contents\s*$',
        r'(?i)^\s*contents\s*$'
    ]
    
    toc_index = -1
    for i, line in enumerate(lines):
        for pattern in toc_patterns:
            if re.match(pattern, line.strip()):
                toc_index = i
                print(f"[DEBUG] Found table of contents at line {i}: '{line}'")
                break
        if toc_index >= 0:
            break
    
    chapters = []
    
    # If we found a TOC, use it to identify chapters and their locations
    if toc_index >= 0:
        # Extract chapter entries with page numbers from TOC
        # Format like: "Chapter 1: Introduction ........... 3"
        toc_chapter_pattern = r'(?i)(?:chapter|part|section)\s+(\d+|[ivxlcdm]+)[^0-9]+?(\d+)$'
        toc_entries = []
        
        # Look at a reasonable number of lines after TOC heading
        for i in range(toc_index + 1, min(toc_index + 50, len(lines))):
            line = lines[i].strip()
            if not line:
                continue
                
            match = re.search(toc_chapter_pattern, line)
            if match:
                chapter_num = match.group(1)
                page_num = match.group(2)
                # Extract title (everything between chapter number and page number)
                title_match = re.search(rf'(?i)(?:chapter|part|section)\s+{chapter_num}[^0-9]+', line)
                title = line[title_match.end():].strip() if title_match else ""
                title = re.sub(r'\.+\s*\d+\s*$', '', title).strip()  # Remove trailing dots and page number
                
                full_title = f"Chapter {chapter_num}{': ' + title if title else ''}"
                toc_entries.append((chapter_num, page_num, full_title))
                print(f"[DEBUG] TOC entry: Chapter {chapter_num}, Page {page_num}, Title: {title}")
        
        # If we found entries in the TOC, try to locate them in the document
        if toc_entries:
            # Simple but effective page boundary detection
            # Look for page numbers that might indicate page boundaries
            page_markers = []
            page_pattern = r'^\s*(\d+)\s*$'  # Plain number on a line by itself
            
            for i, line in enumerate(lines):
                match = re.match(page_pattern, line.strip())
                if match:
                    page_markers.append((i, int(match.group(1))))
            
            # Sort by page number
            page_markers.sort(key=lambda x: x[1])
            
            # Try to correlate TOC entries with page boundaries
            for chapter_num, page_num, title in toc_entries:
                page_num = int(page_num)
                # Find the first page marker with this page number or greater
                for line_idx, marker_page in page_markers:
                    if marker_page >= page_num:
                        # Found potential chapter start based on page number
                        # Look around this point for chapter heading
                        search_range = 15  # Lines to search around the page marker
                        
                        # Look for chapter heading pattern near the page marker
                        chapter_pattern = rf'(?i)chapter\s+{chapter_num}\s*[:.]?'
                        found_heading = False
                        
                        # Search before the page marker first (more common in PDFs)
                        for j in range(max(0, line_idx - search_range), line_idx + search_range):
                            if j < len(lines) and re.search(chapter_pattern, lines[j]):
                                start_idx = j
                                found_heading = True
                                print(f"[DEBUG] Found Chapter {chapter_num} at line {j} based on page {page_num}")
                                break
                        
                        # If we couldn't find heading pattern, use the page marker itself
                        if not found_heading:
                            start_idx = line_idx
                            print(f"[DEBUG] Using page marker at line {line_idx} for Chapter {chapter_num}")
                        
                        # Find where this chapter ends (next chapter or end of doc)
                        end_idx = len(lines)
                        
                        # Look for the next chapter in TOC entries
                        for next_num, next_page, _ in toc_entries:
                            if int(next_page) > page_num:
                                # Find the page marker for the next chapter
                                for next_line_idx, next_marker_page in page_markers:
                                    if next_marker_page >= int(next_page):
                                        end_idx = next_line_idx
                                        break
                                break
                        
                        # Extract chapter content
                        chapter_content = '\n'.join(lines[start_idx:end_idx]).strip()
                        
                        # Only add chapter if it has enough content
                        if len(chapter_content) > 200:
                            chapters.append({
                                "title": title,
                                "content": chapter_content
                            })
                        break
        
        # If we found at least 2 chapters through TOC, we're done
        if len(chapters) >= 2:
            print(f"[DEBUG] Successfully located {len(chapters)} chapters using TOC page numbers")
            return chapters
    
    # 2. Second Strategy: Pattern-based chapter detection
    if not chapters:
        print("[DEBUG] TOC detection failed, falling back to pattern matching")
        # Your existing pattern detection code
        # (Keep all the existing patterns and logic)
        chapter_patterns = [
            r'(?i)^\s*chapter\s+(\d+)\s*:\s*(.*?)$',               # Chapter 1 : Title (with space)
            r'(?i)^\s*chapter\s+(\d+)\s*$',                         # Chapter N alone
            r'(?i)^chapter\s+(\d+)\s*:',                            # Chapter N: without space constraint
            r'(?i)^\s*chapter\s+(\d+|[ivxlcdm]+)[\s\.:]*(.*)$',     # Standard chapter formats
            # ... [your existing patterns] ...
        ]
        
        potential_chapters = []
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            for pattern in chapter_patterns:
                if re.match(pattern, line, re.MULTILINE | re.UNICODE):
                    score = 5  # Higher base score for confident patterns
                    potential_chapters.append((i, line, score))
                    break
        
        if potential_chapters:
            # Process potential chapters into actual chapters
            for idx, (line_idx, heading, _) in enumerate(potential_chapters):
                start_idx = line_idx
                end_idx = potential_chapters[idx + 1][0] if idx + 1 < len(potential_chapters) else len(lines)
                
                chapter_content = '\n'.join([heading] + lines[start_idx + 1:end_idx])
                if len(chapter_content) > 200:
                    chapters.append({
                        "title": heading,
                        "content": chapter_content
                    })
            
            if len(chapters) >= 2:
                print(f"[DEBUG] Pattern detection found {len(chapters)} chapters")
                return chapters
    
    # 3. Final Strategy: Create artificial chapters
    if not chapters:
        print("[DEBUG] All detection methods failed, creating artificial chapters")
        # Modify this part to create at least 2 chapters but not too many
        max_chapter_size = 5000  # Characters per chapter
        total_length = len(text)
        
        # Create at least 2 chapters, but not more than 5 by default
        num_chapters = min(max(2, total_length // max_chapter_size), 5)
        return create_artificial_chapters(text, max_chapter_size, num_chapters=num_chapters)
    
    return chapters

def create_artificial_chapters(text, max_chapter_size=200, num_chapters=5):
    """Create artificial chapters if natural chapters can't be detected"""
    chapters = []
    # Split into chunks of approximately max_chapter_size characters
    total_length = len(text)
    if total_length <= max_chapter_size:
        return [{"title": "Chapter 1", "content": text}]
    
    chapter_size = total_length // num_chapters
    
    for i in range(num_chapters):
        start = i * chapter_size
        end = start + chapter_size if i < num_chapters - 1 else total_length
        chapter_text = text[start:end]
        chapters.append({
            "title": f"Chapter {i+1}",
            "content": chapter_text
        })
    
    return chapters

@app.post("/generate-mcqs")
def generate_mcqs(mcq_input: MCQInput):
    """
    Generates MCQs from given text.
    """
    try:
        if len(mcq_input.text) < 50:
            raise HTTPException(status_code=400, detail="Text should be at least 50 characters long.")

        mcqs = mcq_generator.generate_multiple_mcqs(
            text=mcq_input.text,
            user_requested_count=mcq_input.num_questions
        )
        return {"mcqs": mcqs}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCQ generation failed: {str(e)}")

@app.post("/generate-mcqs-from-file")
def generate_mcqs_from_file(file_input: FileInput):
    """
    Extracts text from a file and then generates MCQs from that text.
    """
    try:
        # First extract text from the file
        file_bytes = base64.b64decode(file_input.file_content)
        result = file_processor.process_file(
            file_content=file_bytes,
            file_name=file_input.file_name,
            file_type=file_input.file_type
        )
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Get the extracted text
        text = result.get("text", "")
        
        if len(text) < 50:
            raise HTTPException(status_code=400, detail="Extracted text is too short for MCQ generation.")
        
        # Get num_questions from the request or use default
        num_questions = file_input.num_questions if hasattr(file_input, 'num_questions') else 5
        
        # Generate MCQs from the extracted text
        mcqs = mcq_generator.generate_multiple_mcqs(
            text=text,
            user_requested_count=num_questions
        )
        
        return {"mcqs": mcqs}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MCQ generation from file failed: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0"}
