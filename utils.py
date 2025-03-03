# utils.py
import re
import spacy
import nltk
from typing import List, Optional, Any
from nltk.tokenize import sent_tokenize
from nltk.corpus import wordnet as wn

# Download necessary NLTK resources if not already available
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/wordnet')
except LookupError:
    nltk.download('wordnet')

# Initialize spaCy model
nlp = spacy.load("en_core_web_sm")

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences."""
    return sent_tokenize(text)

def pick_top_sentences(sentences: List[str], num: int = 3) -> List[str]:
    """
    Pick the most informative sentences for question generation.
    """
    # Simple heuristic: longer sentences tend to have more information
    # Filter out very short sentences
    filtered_sentences = [s for s in sentences if len(s.split()) > 5]
    
    # If we don't have enough sentences after filtering, return all
    if len(filtered_sentences) <= num:
        return filtered_sentences
    
    # Sort by length (word count) and return top 'num' sentences
    return sorted(filtered_sentences, key=lambda s: len(s.split()), reverse=True)[:num]

def is_time_phrase(text: str) -> bool:
    """Determine if the text is a time-related expression."""
    time_patterns = [
        r'\b(year|month|day|decade|century|era)\b',
        r'\b\d{4}\b',  # Years like 1999
        r'\b(January|February|March|April|May|June|July|August|September|October|November|December)\b',
        r'\b(early|late|mid)\s+\d{1,2}(st|nd|rd|th)\s+(century|decade)\b',
    ]
    for pattern in time_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False

def is_synonym_or_lemma(word1: str, word2: str) -> bool:
    """Check if two words are synonyms or share the same lemma."""
    # Check if they're the same word
    if word1.lower() == word2.lower():
        return True
    
    # Check lemmas
    doc1 = nlp(word1)
    doc2 = nlp(word2)
    if doc1 and doc2 and doc1[0].lemma_ == doc2[0].lemma_:
        return True
    
    # Check WordNet synonyms
    synsets1 = wn.synsets(word1)
    synsets2 = wn.synsets(word2)
    for syn1 in synsets1:
        for syn2 in synsets2:
            if syn1 == syn2:
                return True
            
    # Check lemmas in synsets
    lemmas1 = set()
    lemmas2 = set()
    
    for syn in synsets1:
        for lemma in syn.lemmas():
            lemmas1.add(lemma.name().lower())
    
    for syn in synsets2:
        for lemma in syn.lemmas():
            lemmas2.add(lemma.name().lower())
    
    return bool(lemmas1.intersection(lemmas2))

def is_partial_match(short_text: str, long_text: str) -> bool:
    """Check if the shorter text is a part of the longer text."""
    return short_text.lower() in long_text.lower()

def spacy_pos_to_wordnet_pos(spacy_pos: str) -> Optional[str]:
    """Convert spaCy POS tags to WordNet POS tags."""
    if spacy_pos.startswith('NOUN'):
        return wn.NOUN
    elif spacy_pos.startswith('VERB'):
        return wn.VERB
    elif spacy_pos.startswith('ADJ'):
        return wn.ADJ
    elif spacy_pos.startswith('ADV'):
        return wn.ADV
    return None

def extract_main_token(phrase: str) -> Optional[str]:
    """Extract the main token (head word) from a phrase."""
    doc = nlp(phrase)
    if len(doc) == 0:
        return None
    
    # If it's a single token, return it
    if len(doc) == 1:
        return doc[0].text
    
    # Find the root of the phrase
    for token in doc:
        if token.dep_ == "ROOT":
            return token.text
    
    # If no root found, return the last noun or the last token
    for token in reversed(doc):
        if token.pos_ == "NOUN":
            return token.text
    
    # Default to last token
    return doc[-1].text
