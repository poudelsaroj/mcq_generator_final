import json
import requests
from typing import List, Dict, Any
import concurrent.futures

class LLMQuestionGenerator:
    """
    Uses LLMs via OpenRouter API to generate high-quality questions and answers
    from provided text context.
    """
    
    def __init__(self, api_key: str = "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"):
        self.api_key = api_key
        
    def generate_questions(self, context: str, num_questions: int = 3) -> List[Dict[str, str]]:
        """Generate questions and answers using LLM."""
        # Split very large contexts to process in parallel
        if len(context) > 2000:
            chunks = [context[i:i+2000] for i in range(0, len(context), 1500)]
            # Use ThreadPoolExecutor for parallel processing
            with concurrent.futures.ThreadPoolExecutor() as executor:
                results = list(executor.map(
                    lambda chunk: self._generate_chunk_questions(chunk, num_questions//len(chunks) + 1),
                    chunks
                ))
            # Combine and deduplicate results
            all_questions = []
            for result in results:
                all_questions.extend(result)
            return all_questions[:num_questions]
        else:
            return self._generate_chunk_questions(context, num_questions)

    def _generate_chunk_questions(self, chunk_text, count):
        """Helper method for processing individual chunks."""
        if not self.api_key:
            return []  # Fall back to existing methods if no API key

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://mcq-generator.app",
            "X-Title": "MCQ Generator",
            "Content-Type": "application/json"
        }
        
        # Updated prompt based on successful testing with Gemini model
        prompt = (
            f"As an experienced teacher creating a comprehension assessment, develop {count} "
            f"multiple-choice questions based on this text:\n\n\"{chunk_text}\"\n\n"
            f"Follow these educational principles:\n"
            f"1. Create questions at different levels of Bloom's taxonomy (knowledge, comprehension, application, analysis)\n"
            f"2. Include inference questions that require students to 'read between the lines'\n"
            f"3. Ask about character motivations, central themes, and author's purpose where appropriate\n"
            f"4. Vary question types: literal comprehension, vocabulary in context, and text structure\n"
            f"5. Ensure questions assess genuine understanding rather than mere recall\n\n"
            f"Format each as:\nQ: [question text]\nA: [correct answer]"
        )
        
        payload = {
            "model": "google/gemini-2.0-flash-exp:free",  # Use the model that tested well
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 500
        }
        
        try:
            print(f"[DEBUG] Sending LLM question generation request to OpenRouter")
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", 
                               headers=headers, json=payload)
            
            print(f"[DEBUG] LLM question gen status={resp.status_code}")
            
            if resp.status_code == 200:
                data = resp.json()
                if "choices" in data and data["choices"]:
                    text_out = data["choices"][0]["message"]["content"].strip()
                    
                    # Parse the response into question-answer pairs
                    qa_pairs = []
                    
                    # Clean and parse the content
                    lines = text_out.split('\n')
                    i = 0
                    while i < len(lines):
                        line = lines[i].strip()
                        if line.startswith('Q:'):
                            question = line[2:].strip()
                            if i+1 < len(lines) and lines[i+1].strip().startswith('A:'):
                                answer = lines[i+1].strip()[2:].strip()
                                qa_pairs.append({
                                    "question": question,
                                    "answer": answer
                                })
                            i += 2
                        else:
                            i += 1
                    
                    print(f"[DEBUG] LLM generated {len(qa_pairs)} questions")
                    return qa_pairs
        except Exception as e:
            print(f"[DEBUG] LLM Q&A generation error: {e}")
        
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