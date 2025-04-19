import json
import requests
from typing import List, Dict, Any
import concurrent.futures
import time
import re

class EnhancedQuestionGenerator:
    
    def __init__(self, api_key: str = "AIzaSyCU4rOg50EuqY5MFm76-Wz9jLkwnOd9AQA"):
        self.api_key = api_key
        
    def generate_questions(self, context: str, num_questions: int = 3) -> List[Dict[str, str]]:
        """Generate questions using Google Gemini API."""
        print(f"[DEBUG] Generating {num_questions} questions using Gemini API")
        
        # Process in chunks for long text
        if len(context) > 2000:
            chunks = [context[i:i+2000] for i in range(0, len(context), 1500)]
            all_questions = []
            for chunk in chunks:
                chunk_questions = self._generate_chunk_questions(chunk, num_questions//len(chunks) + 1)
                all_questions.extend(chunk_questions)
            return all_questions[:num_questions]
        else:
            return self._generate_chunk_questions(context, num_questions)
    
    def _generate_chunk_questions(self, chunk_text, count):
        """Generate questions for a text chunk using Gemini."""
        if not self.api_key:
            return []
        
        # Use the latest Gemini model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent?key={self.api_key}"
        
        # Simplified, very explicit format instructions
        prompt = f"""
You are creating multiple-choice questions for a reading comprehension test.

Text: "{chunk_text}"

Generate EXACTLY {count} questions based on this text.

Format MUST be:
Q: [Question text]
A: [Answer text - keep to 1-6 words if possible]

Example:
Q: What is the capital of France?
A: Paris

Q: Who wrote Romeo and Juliet?
A: Shakespeare

Your {count} questions:
"""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.2,  # Lower temperature for more reliable format
                "topP": 0.95,
                "maxOutputTokens": 1000
            }
        }
        
        try:
            print(f"[DEBUG] Sending request to Google Gemini API")
            resp = requests.post(
                url=url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=15  # Add timeout to prevent hanging
            )
            
            print(f"[DEBUG] Google API response status={resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                
                # Debug the raw response
                if "candidates" in data and data["candidates"]:
                    text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    print(f"[DEBUG] Raw response first 100 chars: {text_out[:100]}...")
                    
                    # Simple, reliable parsing 
                    qa_pairs = []
                    lines = text_out.split('\n')
                    
                    i = 0
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith('Q:'):
                            question = line[2:].strip()
                            # Look for answer in next line or next few lines
                            for j in range(i+1, min(i+4, len(lines))):
                                if j < len(lines) and lines[j].strip().startswith('A:'):
                                    answer = lines[j].strip()[2:].strip()
                                    qa_pairs.append({
                                        "question": question,
                                        "answer": answer
                                    })
                                    i = j + 1
                                    break
                            else:
                                i += 1
                        else:
                            i += 1
                    
                    print(f"[DEBUG] Successfully parsed {len(qa_pairs)} questions from LLM")
                    return qa_pairs
        except Exception as e:
            print(f"[DEBUG] Error in generate_questions: {str(e)}")
        
        return []

    def validate_pairs(self, qa_pairs: List[Dict[str, str]], 
                      context: str, validator) -> List[Dict[str, str]]:
        """Filter and validate the question-answer pairs using the provided validator."""
        if not qa_pairs:
            return []
            
        valid_pairs = []
        for pair in qa_pairs:
            if validator.is_answer_plausible(
                pair["question"], pair["answer"], context):
                valid_pairs.append(pair)
        
        print(f"[DEBUG] Validated {len(valid_pairs)}/{len(qa_pairs)} questions")
        return valid_pairs


class OnlineDistractionGenerator:
    
    def __init__(self, api_key: str = "AIzaSyCU4rOg50EuqY5MFm76-Wz9jLkwnOd9AQA"):
        self.api_key = api_key
    
    def generate_online_distractors(self, correct: str, context: str, num_distractors: int, attempt=1) -> List[str]:
        """Generate higher quality distractors using Google Gemini."""
        if not self.api_key:
            return []
            
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent?key={self.api_key}"
        
        # Simplified prompt focused on clear formatting requirements
        prompt = f"""
Create {num_distractors} plausible but incorrect options for a multiple-choice question.

Context: "{context}"
Correct answer: "{correct}"

Return ONLY a comma-separated list of {num_distractors} incorrect options:
"""
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.3,
                "topP": 0.95,
                "maxOutputTokens": 500
            }
        }
        
        try:
            resp = requests.post(
                url=url,
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if "candidates" in data and data["candidates"]:
                    text_out = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    # Print raw response for debugging
                    print(f"[DEBUG] Raw distractor response: {text_out[:100]}...")
                    
                    # Handle both comma-separated and numbered formats
                    if re.search(r'^\d+\.', text_out):
                        # Numbered format
                        cands = re.split(r'\d+\.\s*', text_out)
                        cands = [c.strip() for c in cands if c.strip()]
                    else:
                        # Comma-separated format
                        cands = [c.strip() for c in text_out.split(",") if c.strip()]
                    
                    return cands
        except Exception as e:
            print(f"[DEBUG] Distractor generation error: {str(e)}")
            
        return []