# MCQ Generator

An AI-powered application for automatically generating Multiple Choice Questions (MCQs) from uploaded documents. The system uses state-of-the-art NLP models to extract context, generate relevant questions, correct answers, and plausible distractors.

## 📋 Features

- Generate high-quality MCQs from various document formats (PDF, DOCX, TXT, images)
- Automatic text extraction with OCR fallback for scanned documents
- Special handling for book-like documents with chapter detection
- Mobile-friendly React Native frontend
- FastAPI backend with WebSocket support for real-time progress updates
- Customizable number of questions to generate

## 🏗️ Project Structure

```
├── api.py                 # FastAPI server implementation
├── mcq_generator.py       # Core MCQ generation logic
├── fileprocessor.py       # Document processing utilities
├── test.py                # Test script for the MCQ generator
├── frontend1/             # React Native mobile app
├── qa/                    # Question generation model (T5-based)
├── distractor/            # Distractor generation model
├── s2v_old/               # Sense2Vec model for semantic processing
```

## 🚀 Installation

### Prerequisites

- Python 3.8+
- Node.js and npm (for frontend)
- Expo CLI (for mobile app development)

### Backend Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/mcq_generator_final.git
   cd mcq_generator_final
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv myvenv
   source myvenv/bin/activate  # On Windows, use: myvenv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Download the models:
   - [Question Generation Model (1.2GB)](https://drive.google.com/drive/folders/1jbMKWI2xwUFOxdTCBv3qiVGoyv-biiEb?usp=sharing) - Extract to `qa` directory
   - [Distractor Generation Model (1.5GB)](https://drive.google.com/drive/folders/1mrEbzCwrVevZYY7hwrh3PmPy8nSBDhi4?usp=sharing) - Extract to `distractor` directory
   - [Sense2Vec Model (573MB)](https://github.com/explosion/sense2vec/releases/download/v1.0.0/s2v_reddit_2015_md.tar.gz) - Extract to `s2v_old` directory

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend1
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Update the server URL in `frontend1/services/apiService.js` to point to your backend server.

## 🔌 Running the Application

### Starting the Backend

```bash
uvicorn api:app --host 0.0.0.0 --port 8000
```

### Starting the Frontend (Development Mode)

```bash
cd frontend1
expo start
```

Connect using the Expo Go app on your mobile device or use an emulator.

## 📚 Usage

1. Launch the application on your device
2. Tap "Upload Document" to select a file (PDF, DOCX, TXT, or image)
3. Choose whether the document is a regular document or a book
4. For books, you can choose to process the entire book or select specific chapters
5. Set the number of questions to generate
6. Review and save the generated MCQs

### Command Line Usage

You can also generate MCQs using the command line:

```bash
python test.py --input_file path/to/your/document.pdf --num_questions 10
```

## 🧠 Model Information

### Question Generation Model
- Based on T5 transformer architecture
- Fine-tuned on SQuAD and RACE datasets
- Optimized for creating context-relevant questions

### Distractor Generation Model
- Specialized T5-based model for generating plausible incorrect options
- Trained to create distractors that are semantically related but factually incorrect

### Sense2Vec Model
- Used for semantic understanding and relationship processing
- Helps in creating better distractors by identifying semantic relationships

## 💻 API Reference

The system exposes several API endpoints:

- `POST /process-file` - Process a document and extract text
- `POST /generate-mcqs-from-file` - Generate MCQs from a file
- `POST /generate-mcqs` - Generate MCQs from raw text
- `WebSocket /api/ws/{client_id}` - Real-time processing updates

### Example API Usage

```python
import requests

# Generate MCQs from text
response = requests.post(
    "http://localhost:8000/generate-mcqs",
    json={
        "text": "Your document text here...",
        "num_questions": 5
    }
)

mcqs = response.json()
print(mcqs)
```

## 📱 Mobile App Features

- Document upload from device storage
- Camera capture for scanning documents
- Real-time progress tracking during MCQ generation
- Save and share generated MCQs
- Offline mode for viewing previously generated MCQs

## 🔧 Troubleshooting

- **Model loading issues**: Ensure all model files are correctly placed in their respective directories
- **Memory errors**: For large documents, try processing in smaller chunks
- **OCR problems**: For poor quality scans, try improving the image quality before upload
- **Backend connection issues**: Verify the API URL in the frontend configuration

## 🛠️ Technologies Used

- **Backend**: Python, FastAPI, WebSockets, PyTorch, Transformers, Spacy
- **Frontend**: React Native, Expo, JavaScript
- **Models**: T5 (fine-tuned), Sense2Vec
- **Document Processing**: PyMuPDF, PyPDF2, Tesseract OCR

## 🔜 Future Enhancements

- Subject-specific models for domains like medicine, law, etc.
- Difficulty level classification for questions
- Export options to various LMS formats
- Support for more document formats
- Enhanced UI for desktop environments

## 📝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgements

- The SQuAD dataset for question generation training
- The RACE dataset for MCQ format training
- Hugging Face for model hosting and libraries
- The open-source community for various tools and libraries used