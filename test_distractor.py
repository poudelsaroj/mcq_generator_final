# test_distractor_generator.py
from distractor_generator import DistractorGenerator

def test_distractor_generation():
    # Create an instance of the distractor generator
    generator = DistractorGenerator()
    
    # Test cases with different types of correct answers and contexts
    test_cases = [
        {
            "correct_answer": "photosynthesis", 
            "context": "Plants convert sunlight into energy through a process called photosynthesis, which involves chlorophyll."
        },
        {
            "correct_answer": "Abraham Lincoln",
            "context": "Abraham Lincoln was the 16th president of the United States and led the country through the Civil War."
        },
        {
            "correct_answer": "1945",
            "context": "World War II ended in 1945 with the surrender of Japan after atomic bombs were dropped."
        },
        {
            "correct_answer": "mitochondria",
            "context": "The mitochondria is often called the powerhouse of the cell because it produces ATP."
        }
    ]
    
    # Run tests
    for i, case in enumerate(test_cases):
        print(f"\n--- Test Case {i+1} ---")
        print(f"Correct Answer: {case['correct_answer']}")
        print(f"Context: {case['context']}")
        
        # Generate distractors
        distractors = generator.generate_best_distractors(
            case["correct_answer"], 
            case["context"],
            num_distractors=3
        )
        
        print(f"Generated Distractors: {distractors}")
        
        # Check if we got actual distractors and not fallback options
        has_emergency = any("Alternative to" in d for d in distractors)
        has_fallback = any("None of the above" in d for d in distractors)
        
        if has_emergency or has_fallback:
            print("WARNING: Using emergency/fallback distractors")

if __name__ == "__main__":
    test_distractor_generation()