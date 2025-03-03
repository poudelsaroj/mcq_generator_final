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
    allow_origins=["*"],
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
    Enhanced chapter detection using multiple strategies to identify chapter boundaries
    in various document types and formats.
    """
    import re
    from collections import Counter
    
    # More comprehensive chapter heading patterns
    chapter_patterns = [
        # Standard chapter headings
        r'(?i)^\s*chapter\s+(\d+|[ivxlcdm]+)[\s\.:]*(.*)$',  # Chapter 1: Title
        r'(?i)^\s*section\s+(\d+|[ivxlcdm]+)[\s\.:]*(.*)$',  # Section 1: Title
        r'(?i)^\s*part\s+(\d+|[ivxlcdm]+)[\s\.:]*(.*)$',     # Part I: Title
        r'(?i)^\s*unit\s+(\d+|[ivxlcdm]+)[\s\.:]*(.*)$',     # Unit 1: Title
        
        # Numbered headings
        r'^\s*(\d+)[\.\s]+([\p{Lu}][\p{L}\s].*)$',           # 1. Title or 1 Title
        r'^\s*(\d+\.\d+)[\.\s]+([\p{Lu}][\p{L}\s].*)$',      # 1.1 Title (subsections)
        
        # Roman numerals as headings
        r'^\s*([IVXLCDM]+)[\.\s]+([\p{Lu}][\p{L}\s].*)$',    # IV. TITLE
        
        # Special formats
        r'^\s*LESSON\s+(\d+|[IVXLCDM]+)[\s\.:]*(.*)$',       # LESSON 1: Title
        r'^\s*LECTURE\s+(\d+|[IVXLCDM]+)[\s\.:]*(.*)$',      # LECTURE 1: Title
        r'^\s*MODULE\s+(\d+|[IVXLCDM]+)[\s\.:]*(.*)$',       # MODULE 1: Title
        
        # Appendices and supplementary sections
        r'(?i)^\s*appendix\s+([a-z]|[IVXLCDM]+)[\s\.:]*(.*)$',  # Appendix A: Title
        r'(?i)^\s*annex\s+([a-z]|[IVXLCDM]+)[\s\.:]*(.*)$',     # Annex I: Title
    ]
    
    # Split the text into lines for analysis
    lines = text.split('\n')
    
    # First pass - identify potential chapter headings
    potential_chapters = []
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        
        for pattern in chapter_patterns:
            if re.match(pattern, line, re.MULTILINE | re.UNICODE):
                # Look for clues that this is really a heading:
                # 1. Short line (headings are usually short)
                # 2. Previous line might be empty
                # 3. Current line might have different formatting (ALL CAPS, etc.)
                is_short_line = len(line) < 100
                prev_line_empty = i > 0 and not lines[i-1].strip()
                is_capitalized = line.isupper() or (line[0:1].isupper() if line else False)
                
                score = 0
                if is_short_line: score += 2
                if prev_line_empty: score += 1
                if is_capitalized: score += 1
                
                if score >= 2:  # Threshold for considering a line as a chapter heading
                    potential_chapters.append((i, line, score))
                break
    
    # If no potential chapters found through patterns, try structural analysis
    if not potential_chapters:
        # Look for formatting clues like consistent line spacing or style
        line_lengths = [len(line.strip()) for line in lines if line.strip()]
        avg_length = sum(line_lengths) / max(len(line_lengths), 1)
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check if this line is significantly shorter than average
            # and followed by longer content (potential heading)
            if len(line) < avg_length * 0.5 and i < len(lines) - 1 and len(lines[i+1].strip()) > avg_length:
                if line[0:1].isupper():  # First letter capitalized
                    potential_chapters.append((i, line, 1))  # Lower score for structural detection
    
    # If still no chapters found or too few, fall back to content-based segmentation
    if len(potential_chapters) <= 1:
        # Create artificial chapters based on content size
        return create_artificial_chapters(text)
    
    # Extract actual chapter text based on identified headings
    chapters = []
    for idx, (line_idx, heading, _) in enumerate(potential_chapters):
        start_idx = line_idx
        end_idx = potential_chapters[idx + 1][0] if idx + 1 < len(potential_chapters) else len(lines)
        
        chapter_title = heading.strip()
        chapter_content = '\n' + '\n'.join([heading] + lines[start_idx + 1:end_idx])
        
        # Skip very short chapters that might be false positives
        if len(chapter_content.strip()) > 200:
            chapters.append({
                "title": chapter_title,
                "content": chapter_content.strip()
            })
    
    # If we identified headings but didn't get valid chapters, fall back to simpler approach
    if not chapters:
        return [{"title": "Chapter 1", "content": text}]
    
    return chapters

def create_artificial_chapters(text, max_chapter_size=5000):
    """Create artificial chapters if natural chapters can't be detected"""
    chapters = []
    # Split into chunks of approximately max_chapter_size characters
    total_length = len(text)
    if total_length <= max_chapter_size:
        return [{"title": "Chapter 1", "content": text}]
    
    num_chapters = max(3, total_length // max_chapter_size)
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
def health_check():
    return {"status": "ok"}
