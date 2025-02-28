# api.py
from fastapi import FastAPI, HTTPException, Body, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import base64

from mcq_generator import MCQGenerator
from fileprocessor import FileProcessor, ChapterDetector
from fastapi.middleware.cors import CORSMiddleware

from fastapi import WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState
import json

# Initialize the components
mcq_generator = MCQGenerator(model_path="checkpoint-400")
file_processor = FileProcessor(ocr_enabled=True)
chapter_detector = ChapterDetector()

app = FastAPI(title="MCQ Generator API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class PassageInput(BaseModel):
    text: str
    num_questions: Optional[int] = 1
    num_distractors: Optional[int] = 3

class FileInput(BaseModel):
    file_content: str  # Base64 encoded file content
    file_name: str
    file_type: str
    num_questions: Optional[int] = 1
    document_type: Optional[str] = "document"  # "document" or "book"

class MCQResponse(BaseModel):
    mcqs: List[Dict[str, Any]]
    count: int

class ChapterResponse(BaseModel):
    is_book: bool
    chapters: List[Dict[str, Any]]

# Add a WebSocket connection manager for tracking active connections
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, client_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[client_id] = websocket

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]

    async def send_message(self, client_id: str, message: dict):
        if client_id in self.active_connections:
            try:
                await self.active_connections[client_id].send_json(message)
            except Exception as e:
                print(f"Error sending message to client {client_id}: {e}")

manager = ConnectionManager()

@app.post("/generate-mcqs", response_model=MCQResponse)
async def generate_mcqs(input_data: PassageInput = Body(...)):
    """Generate MCQs from a given text passage."""
    try:
        if input_data.num_questions == 1:
            # Generate a single MCQ
            mcq = mcq_generator.generate_mcq_from_text(
                input_data.text, 
                num_distractors=input_data.num_distractors
            )
            if not mcq:
                raise HTTPException(status_code=500, detail="Failed to generate MCQ.")
            mcqs = [mcq]
        else:
            # Generate multiple MCQs
            mcqs = mcq_generator.generate_multiple_mcqs(
                input_data.text, 
                num_questions=input_data.num_questions
            )
            if not mcqs:
                raise HTTPException(status_code=500, detail="Failed to generate MCQs.")
        
        return {"mcqs": mcqs, "count": len(mcqs)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating MCQs: {str(e)}")

@app.post("/process-file", response_model=ChapterResponse)
async def process_file(file_input: FileInput = Body(...)):
    """Process a file to extract text and detect if it's a book with chapters."""
    try:
        # Decode base64 file content
        file_content = base64.b64decode(file_input.file_content)
        
        # Process the file to extract text
        result = file_processor.process_file(
            file_content=file_content,
            file_name=file_input.file_name,
            file_type=file_input.file_type
        )
        
        if not result.get("text"):
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")
        
        text_content = result["text"]
        
        # Detect if the document is a book and extract chapters
        is_book = chapter_detector.is_likely_book(text_content)
        
        if is_book or file_input.document_type == "book":
            chapters = chapter_detector.extract_chapters(text_content)
            return {
                "is_book": True,
                "chapters": chapters
            }
        else:
            # For regular documents, return the text as a single chapter
            return {
                "is_book": False,
                "chapters": [{
                    "title": "Full Document",
                    "content": text_content
                }]
            }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/generate-mcqs-from-file", response_model=MCQResponse)
async def generate_mcqs_from_file(file_input: FileInput = Body(...)):
    """Process a file and generate MCQs from its content."""
    try:
        # Decode base64 file content
        file_content = base64.b64decode(file_input.file_content)
        
        # Process the file to extract text
        result = file_processor.process_file(
            file_content=file_content,
            file_name=file_input.file_name,
            file_type=file_input.file_type
        )
        
        if not result.get("text"):
            raise HTTPException(status_code=400, detail="Could not extract text from the file.")
        
        text_content = result["text"]
        
        # Generate MCQs from the extracted text
        mcqs = mcq_generator.generate_multiple_mcqs(
            text_content, 
            num_questions=file_input.num_questions
        )
        
        if not mcqs:
            raise HTTPException(status_code=500, detail="Failed to generate MCQs from the file.")
        
        return {"mcqs": mcqs, "count": len(mcqs)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.websocket("/api/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    print(f"WebSocket connection request from client {client_id}")
    await manager.connect(client_id, websocket)
    print(f"WebSocket connection established with client {client_id}")
    
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            print(f"Received message from client {client_id}: {data[:50]}...")  # Log the first 50 chars
            
            try:
                payload = json.loads(data)
                command = payload.get("command")
                
                if command == "process_file":
                    # Send processing status
                    await manager.send_message(client_id, {
                        "status": "Processing started",
                        "message": "Extracting text from file..."
                    })
                    
                    # Get file info from payload
                    file_content = base64.b64decode(payload["file_content"])
                    file_name = payload["file_name"]
                    file_type = payload["file_type"]
                    document_type = payload.get("document_type", "document")
                    
                    # Process the file
                    result = file_processor.process_file(
                        file_content=file_content,
                        file_name=file_name,
                        file_type=file_type
                    )
                    
                    # Check for errors
                    if "error" in result:
                        await manager.send_message(client_id, {
                            "status": "error",
                            "message": result["error"]
                        })
                        continue
                    
                    if not result.get("text"):
                        await manager.send_message(client_id, {
                            "status": "error",
                            "message": "Could not extract text from file"
                        })
                        continue
                    
                    text_content = result["text"]
                    
                    # Check if it's a book with chapters
                    is_book = chapter_detector.is_likely_book(text_content)
                    chapters = chapter_detector.extract_chapters(text_content)
                    
                    # Send response based on book or document
                    await manager.send_message(client_id, {
                        "status": "complete",
                        "is_book": is_book,
                        "chapters": chapters
                    })
                
                else:
                    await manager.send_message(client_id, {
                        "status": "error",
                        "message": f"Unknown command: {command}"
                    })
                    
            except json.JSONDecodeError:
                await manager.send_message(client_id, {
                    "status": "error",
                    "message": "Invalid JSON format"
                })
            except Exception as e:
                print(f"Error processing message: {str(e)}")
                await manager.send_message(client_id, {
                    "status": "error",
                    "message": f"Error processing request: {str(e)}"
                })
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        print(f"Client disconnected: {client_id}")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.get("/test")
async def test_connection():
    return {"status": "ok", "message": "API connection successful"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)