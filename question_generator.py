# question_generator.py
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer
from typing import Tuple, Dict, List, Optional

class QuestionGenerator:
    """Generate questions and answers using a fine-tuned T5 model."""
    
    def __init__(self, model_path: str = "checkpoint-400"):
        """
        Initialize the question generator with a fine-tuned T5 model.
        
        Args:
            model_path: Path to the fine-tuned model directory
        """
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading T5 model from {model_path} on {self.device}")
        
        # Use the base t5 tokenizer instead of loading from checkpoint
        self.tokenizer = T5Tokenizer.from_pretrained("t5-base")
        self.model = T5ForConditionalGeneration.from_pretrained(model_path).to(self.device)
    
    def generate_question_answer(self, passage: str, max_length: int = 128) -> str:
        """
        Given a passage, generate a question and answer.
        
        Args:
            passage: Input text
            max_length: Maximum output length
        
        Returns:
            String in the format "Question: ... Answer: ..."
        """
        prompt = "Generate MCQ: " + passage
        inputs = self.tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=512).to(self.device)
        
        with torch.no_grad():
            output_ids = self.model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=max_length,
                num_beams=4,
                early_stopping=True
            )
            
        decoded = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return decoded
    
    def parse_t5_output(self, t5_output: str) -> Tuple[str, str]:
        """
        Parse T5 output to extract question and answer.
        
        Args:
            t5_output: Output from generate_question_answer
            
        Returns:
            Tuple of (question, answer)
        """
        # Remove leading/trailing spaces
        text = t5_output.strip()
        
        # Find positions of 'Question:' and 'Answer:'
        q_idx = text.lower().find("question:")
        a_idx = text.lower().find("answer:")
        
        question_part = ""
        answer_part = ""
        
        if q_idx != -1 and a_idx != -1:
            question_part = text[q_idx + len("question:"):a_idx].strip()
            answer_part = text[a_idx + len("answer:"):].strip()
            
        return question_part, answer_part
    
    def generate_from_text(self, passage: str) -> Optional[Dict[str, str]]:
        """
        Generate a question-answer pair from a passage.
        
        Args:
            passage: Input text
            
        Returns:
            Dictionary with 'question' and 'answer' keys, or None if generation failed
        """
        t5_output = self.generate_question_answer(passage)
        question, answer = self.parse_t5_output(t5_output)
        
        if not question or not answer:
            return None
            
        return {
            "question": question,
            "answer": answer
        }