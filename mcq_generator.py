# mcq_generator.py
import random
from typing import Dict, List, Any, Optional

from question_generator import QuestionGenerator
from distractor_generator import DistractorGenerator
from utils import split_into_sentences, pick_top_sentences

class MCQGenerator:
    """Generate complete multiple-choice questions."""
    
    def __init__(self, model_path: str = "checkpoint-400"):
        """Initialize the MCQ generator."""
        self.question_generator = QuestionGenerator(model_path)
        self.distractor_generator = DistractorGenerator()
    
    def generate_mcq_from_text(self, passage: str, num_distractors: int = 3) -> Optional[Dict[str, Any]]:
        """
        Generate a complete MCQ from a passage of text.
        
        Args:
            passage: Input text passage
            num_distractors: Number of distractors to generate
            
        Returns:
            Dictionary with 'passage', 'question', 'options', and 'correct_answer' keys
        """
        # Generate question and answer
        qa_result = self.question_generator.generate_from_text(passage)
        if not qa_result:
            return None
        
        question = qa_result["question"]
        correct_answer = qa_result["answer"]
        
        # Generate distractors
        distractors = self.distractor_generator.generate_best_distractors(
            correct_answer, passage, num_distractors
        )
        
        # Fill up to requested number of distractors if needed
        if len(distractors) < num_distractors:
            distractors.extend(["(No more distractors)"] * (num_distractors - len(distractors)))
        
        # Build options and shuffle
        options = distractors + [correct_answer]
        random.shuffle(options)
        
        return {
            "passage": passage,
            "question": question,
            "options": options,
            "correct_answer": correct_answer,
            "correct_option_idx": options.index(correct_answer)
        }
    
    def generate_multiple_mcqs(self, passage: str, num_questions: int = 3) -> List[Dict[str, Any]]:
        """
        Generate multiple MCQs from a passage.
        
        Args:
            passage: Input text passage
            num_questions: Number of MCQs to generate
            
        Returns:
            List of MCQ dictionaries
        """
        # Split into sentences and pick the best ones
        sentences = split_into_sentences(passage)
        if not sentences:
            return []
        
        selected_sents = pick_top_sentences(sentences, num=num_questions * 2)
        
        # Generate MCQs from selected sentences
        mcqs = []
        for sent in selected_sents:
            mcq = self.generate_mcq_from_text(sent)
            if mcq:
                mcqs.append(mcq)
                if len(mcqs) >= num_questions:
                    break
        
        return mcqs