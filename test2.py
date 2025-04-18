import os
import sys
import json
import requests

def test_llm_question_generation():
    """Test the LLM-based question generation functionality."""
    
    # Use the provided API key
    api_key = "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"
    
    # Test passage - using a shorter text to avoid large responses
    test_passage = """
    Nepal is a landlocked country in South Asia. It is mainly situated in the Himalayas.
    With an estimated population of 30.5 million, Nepal borders China in the north and 
    India in the south, east, and west. Kathmandu is the capital and the largest city.
    """
    
    print("\n=== Testing LLM Question Generation ===\n")
    print(f"Sample text passage:\n{test_passage}\n")
    
    print("Attempting to generate questions using LLM...")
    
    # Direct API call for testing with simpler prompt
    prompt = (
        f"Generate 2 multiple-choice questions based on this text: '{test_passage}'\n"
        f"Format each as 'Q: [question]' on one line followed by 'A: [answer]' on the next line."
    )
    
    try:
        print("Sending API request...")
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://mcq-generator.app",
                "X-Title": "MCQ Generator",
                "Content-Type": "application/json"
            },
            json={
                # Try a different model - Claude is usually more reliable for formatting
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500
            }
        )
        
        print(f"\nAPI Response Status: {response.status_code}")
        response.raise_for_status()
        
        # Print raw text before parsing JSON
        print("\nRaw response text (first 100 chars):")
        raw_text = response.text
        print(raw_text[:100] + "..." if len(raw_text) > 100 else raw_text)
        
        # Safely parse JSON with error handling
        try:
            data = response.json()
            print("\nJSON parsed successfully")
            
            # Extract content
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0]["message"]["content"].strip()
                print(f"\nContent returned (first 200 chars):\n{content[:200]}...\n")
                
                # Improved parsing - handle unexpected prefixes and find unique QA pairs
                qa_pairs = []
                seen_questions = set()
                
                # First, clean the content by removing numeric prefixes
                clean_content = '\n'.join([
                    line for line in content.split('\n')
                    if not (line.strip().replace('.', '').isdigit() or line.strip() == '')
                ])
                
                # Now parse line by line
                lines = clean_content.split('\n')
                i = 0
                while i < len(lines):
                    line = lines[i].strip()
                    if line.startswith('Q:'):
                        question = line[2:].strip()
                        if i+1 < len(lines) and lines[i+1].strip().startswith('A:'):
                            answer = lines[i+1].strip()[2:].strip()
                            
                            # Only add if we haven't seen this question before
                            if question not in seen_questions:
                                qa_pairs.append({"question": question, "answer": answer})
                                seen_questions.add(question)
                        i += 2
                    else:
                        i += 1
                
                if qa_pairs:
                    print(f"\nSUCCESS: Extracted {len(qa_pairs)} unique questions:")
                    for i, q in enumerate(qa_pairs, 1):
                        print(f"\nQuestion {i}:")
                        print(f"Q: {q['question']}")
                        print(f"A: {q['answer']}")
                else:
                    print("\nERROR: Could not parse questions and answers from the response")
                    
                    # Manual fallback parsing for debugging
                    print("\nAttempting manual parsing as fallback:")
                    
                    for line in content.split('\n'):
                        if 'Q:' in line:
                            print(f"Found potential question: {line.strip()}")
                        if 'A:' in line:
                            print(f"Found potential answer: {line.strip()}")
            else:
                print("\nERROR: Unexpected response format, missing 'choices'")
                
        except json.JSONDecodeError as e:
            print(f"\nERROR: Failed to parse JSON response: {e}")
            print("This could be caused by invalid JSON from the API or a truncated response")
                
    except requests.exceptions.RequestException as e:
        print(f"\nERROR: Request failed: {e}")

if __name__ == "__main__":
    test_llm_question_generation()