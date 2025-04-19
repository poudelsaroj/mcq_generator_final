import requests
import json

def test_google_api():
    """Test Google Gemini API directly without any abstractions."""
    
    api_key = "AIzaSyCU4rOg50EuqY5MFm76-Wz9jLkwnOd9AQA"  # Your Google API key
    
    test_text = """
    Nepal is a landlocked country in South Asia. It is mainly situated in the Himalayas.
    With an estimated population of 30.5 million, Nepal borders China in the north and 
    India in the south, east, and west. Kathmandu is the capital and the largest city.
    """
    
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-04-17:generateContent?key={api_key}"
    
    # Very simple prompt with explicit formatting instructions
    prompt = f"""
    Create 2 questions based on this text: '{test_text}'
    
    Format your response EXACTLY like this:
    Q: [question]
    A: [answer]
    
    Q: [question]
    A: [answer]
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    print("Sending test request to Google Gemini API...")
    response = requests.post(
        url=url,
        headers={"Content-Type": "application/json"},
        json=payload
    )
    
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        if "candidates" in data and data["candidates"]:
            # Print raw response
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            print("\nRaw response:")
            print(text)
            
            # Try parsing
            print("\nTrying to parse Q/A pairs:")
            lines = text.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i].strip()
                if line.startswith('Q:'):
                    print(f"Found question: {line}")
                    if i+1 < len(lines) and lines[i+1].strip().startswith('A:'):
                        print(f"Found answer: {lines[i+1].strip()}")
                i += 1
        else:
            print("No candidates in response")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_google_api()