# mcq_generator.py

import os
import re
import json
import random
import time
import requests
from typing import Dict, Any, List, Tuple

import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from sentence_transformers import SentenceTransformer, util

import spacy
nlp = spacy.load("en_core_web_sm")

import nltk
from nltk.corpus import wordnet as wn
from nltk.tokenize import sent_tokenize

try:
    nltk.data.find("tokenizers/punkt")
except LookupError:
    nltk.download("punkt")
try:
    nltk.data.find("corpora/wordnet")
except LookupError:
    nltk.download("wordnet")

try:
    from sense2vec import Sense2Vec
    s2v = Sense2Vec().from_disk("s2v_old")  # Adjust if needed
    s2v_available = True
except:
    s2v = None
    s2v_available = False

import concurrent.futures

# # Import LLM components from generator.py
# from generator import LLMQuestionGenerator, DistractorGeneratorLLM

# Import advanced components from generator.py
from generator import EnhancedQuestionGenerator, OnlineDistractionGenerator

def remove_duplicate_questions(mcqs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Remove MCQs with exact same question text."""
    seen = set()
    result = []
    for m in mcqs:
        q_lower = m["question"].strip().lower()
        if q_lower not in seen:
            result.append(m)
            seen.add(q_lower)
    return result

def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences using NLTK."""
    return sent_tokenize(text)

def question_answer_type_check(question: str, answer: str) -> bool:
    """
    A minimal "type check" to avoid "nationality => city" type mismatches.
    For example:
      - if question says "nationality" or "demonym", we expect "Nepali" or "Nepalese" not "Kathmandu".
      - if question says "city" or "capital", we expect "Kathmandu" or "Paris" not "Nepali".
    Expand as desired.
    """
    q_lower = question.lower()
    a_lower = answer.lower()

    # Example rule: if question has "nationality" or "demonym",
    # the answer must not be a city name or "Kathmandu".
    if ("nationality" in q_lower or "demonym" in q_lower):
        # If answer is "kathmandu" or "mount everest" we reject
        city_keywords = ["kathmandu", "city", "mount", "beijing", "capital", "paris"]
        for ck in city_keywords:
            if ck in a_lower:
                return False

    # Another rule: if question has "capital" or "city", we reject "nepali" or "hindu" etc.
    if ("capital" in q_lower or "city" in q_lower):
        # If answer is "nepali" or "himalayas" => reject
        nationality_keywords = ["nepali", "himalayas", "hindu", "buddhist", "french"]
        for nk in nationality_keywords:
            if nk in a_lower:
                return False

    # If question says "largest mountain" => answer shouldn't be "Nepali," etc.
    if ("largest mountain" in q_lower or "tallest mountain" in q_lower):
        # If answer is "nepali" or "kathmandu" => reject
        if "nepali" in a_lower or "kathmandu" in a_lower:
            return False

    return True

class AnswerValidator:
    """
    Validates if an answer is plausible for a given question and context
    """
    def __init__(self):
        self.sbert = SentenceTransformer("all-MiniLM-L6-v2")
        self.threshold = 0.05  # Lower threshold for better recall

    def is_answer_plausible(self, question: str, answer: str, context: str) -> bool:
        # Reject empty, too short, or generic answers
        if not answer or len(answer) < 2 or "could not parse" in answer.lower():
            print(f"[DEBUG] Rejecting answer '{answer}' (too short/generic)")
            return False
            
        # Type-check rule first
        if not question_answer_type_check(question, answer):
            print(f"[DEBUG] Type-check failed: Q='{question}' => A='{answer}'")
            return False

        # Check if answer is found in context (high confidence match)
        if answer.lower() in context.lower():
            return True

        # Semantic similarity check
        ans_emb = self.sbert.encode(answer, convert_to_tensor=True)
        ctx_emb = self.sbert.encode(context, convert_to_tensor=True)
        sim = float(util.cos_sim(ans_emb, ctx_emb)[0][0])
        print(f"[DEBUG] SBERT check: answer='{answer}' sim={sim:.3f}, threshold={self.threshold}")
        return sim >= self.threshold

class DistractorGenerator:
    """
    T5 => if <3 =>  if <3 => sense2vec => if <3 => emergency
    + generates up to 5 T5 distractors to reduce fallback usage.
    + retries Google API once if code=429 (ex: usage limit).
    """

    def __init__(self, distractor_model_path: str, google_api_key: str, device: str):
        self.device = device
        print(f"[DEBUG] Loading T5 distractor from: {os.path.abspath(distractor_model_path)}")
        self.dist_tokenizer = AutoTokenizer.from_pretrained(distractor_model_path)
        self.dist_model = AutoModelForSeq2SeqLM.from_pretrained(distractor_model_path).to(self.device)
        self.api_key = google_api_key  # Store as api_key for internal use
        self.sbert = SentenceTransformer("all-MiniLM-L6-v2")
        # Initialize the online distractor generator
        self.online_distractor_gen = OnlineDistractionGenerator(api_key=google_api_key)

    def _generate_t5_distractors(self, question: str, correct: str, context: str) -> List[str]:
        # We request up to 5 sequences
        SEP_TOKEN = "<sep>"
        input_text = f"{question}{SEP_TOKEN}{correct}{SEP_TOKEN}{context}"
        inputs = self.dist_tokenizer([input_text],
                                     return_tensors="pt",
                                     max_length=512,
                                     truncation=True,
                                     padding=True).to(self.device)

        with torch.no_grad():
            # We generate up to 5 sequences
            outputs = self.dist_model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=64,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=1.0,
                num_return_sequences=5
            )

        all_cands = []
        for out in outputs:
            decoded = self.dist_tokenizer.decode(out, skip_special_tokens=True)
            partial = [d.strip() for d in decoded.split(SEP_TOKEN) if d.strip()]
            all_cands.extend(partial)
        # remove duplicates among T5 outputs
        final = []
        seen = set()
        for c in all_cands:
            cl = c.lower()
            if cl not in seen:
                final.append(c)
                seen.add(cl)
        print(f"[DEBUG] T5 raw distractor candidates={final}")
        return final

    def _generate_llm_distractors(self, correct: str, context: str, num_distractors: int, attempt=1) -> List[str]:
        
        # Use the LLM distractor generator implemented in generator.py
        cands = self.llm_distractor_gen.generate_llm_distractors(
            correct, context, num_distractors, attempt)
        
        # Filter candidates as before
        filtered = self._filter_candidates(cands, correct, context)
        if len(filtered) < num_distractors:
            needed = num_distractors - len(filtered)
            more = self._emergency_fallback(correct, context, needed)
            filtered.extend(more)
        
        return filtered[:num_distractors]

    def _generate_online_distractors(self, correct: str, context: str, num_distractors: int, attempt=1) -> List[str]:
        """Generate distractors using Google API with minimal filtering."""
        # Use the online distractor generator implemented in generator.py
        cands = self.online_distractor_gen.generate_online_distractors(
            correct, context, num_distractors, attempt)
        
        if len(cands) >= num_distractors:
            # Trust LLM output with minimal filtering
            # Just check for basic issues like duplicates and identical matches
            filtered = []
            seen = set([correct.lower()])  # Add correct answer to seen set first
            
            for cand in cands:
                cand_lower = cand.lower()
                if cand_lower not in seen and cand_lower != correct.lower():
                    filtered.append(cand)
                    seen.add(cand_lower)
                    if len(filtered) >= num_distractors:
                        break
                        
            # Only if we have enough after this minimal filtering, return directly
            if len(filtered) >= num_distractors:
                return filtered[:num_distractors]
        
        # If we don't have enough after minimal filtering, then try standard filtering
        filtered = self._filter_candidates(cands, correct, context)
        if len(filtered) < num_distractors:
            needed = num_distractors - len(filtered)
            # Try to get more from LLM with another attempt before using emergency
            if attempt < 2:
                # Try again with LLM
                print(f"[DEBUG] Not enough distractors ({len(filtered)}), retrying LLM")
                more_cands = self.online_distractor_gen.generate_online_distractors(
                    correct, context, needed, attempt + 1)
                more_filtered = self._filter_candidates(more_cands, correct, context)
                filtered.extend(more_filtered)
            
            # Only use emergency fallback if absolutely necessary
            if len(filtered) < num_distractors:
                more = self._emergency_fallback(correct, context, num_distractors - len(filtered))
                filtered.extend(more)
        
        return filtered[:num_distractors]

    def _sense2vec_wordnet(self, correct: str, context: str, num: int) -> List[str]:
        cands = []
        if s2v_available and correct.strip():
            tagged = correct + "|NOUN"
            try:
                sim_list = s2v.most_similar(tagged, n=15)
                for cc, sc in sim_list:
                    c_text = cc.split("|")[0]
                    if c_text.lower() != correct.lower():
                        cands.append(c_text)
            except:
                pass

        for syn in wn.synsets(correct):
            for lemma in syn.lemmas():
                lw = lemma.name().replace("_", " ")
                if lw.lower() != correct.lower():
                    cands.append(lw)

        final = self._re_rank_distractors(cands, correct, context, top_k=num)
        if len(final) < num:
            need = num - len(final)
            extra = self._emergency_fallback(correct, context, need)
            final += extra
        return final[:num]

    def _emergency_fallback(self, correct: str, context: str, num: int) -> List[str]:
        base = [
            "None of the above",
            "All of the above",
            "Not enough information",
            "Another random guess"
        ]
        random.shuffle(base)
        return base[:num]

    def _filter_candidates(self, cands: List[str], correct: str, context: str) -> List[str]:
        final = []
        seen = set()
        clower = correct.lower()
        
        # Normalize function to remove articles and standardize forms
        def normalize(text):
            # Remove leading articles and trailing punctuation
            text = re.sub(r'^(a|an|the)\s+', '', text.lower())
            text = re.sub(r'[.,!?]$', '', text)  # Remove trailing punctuation
            # Lemmatize to handle plurals/singulars using spacy
            doc = nlp(text)
            lemmas = [token.lemma_ for token in doc]
            return " ".join(lemmas)
        
        # Get normalized correct answer for comparison
        normalized_correct = normalize(correct)
        
        # Get semantic representation of correct answer
        correct_emb = self.sbert.encode(correct, convert_to_tensor=True)
        
        # Metric for distractor quality - should be related but different enough
        distractor_scores = []
        
        for c in cands:
            # Skip empty candidates
            if not c.strip():
                continue
                
            dlow = c.lower()
            normalized_c = normalize(c)
            
            # Check if this is a duplicate or too similar to correct answer
            if (normalized_c not in seen and 
                normalized_c != normalized_correct and
                clower not in dlow and
                dlow not in clower and
                not self._is_minimal_variation(c, [correct] + final)):
                
                # Get similarity score - we want distractors that are related
                # but not too similar to correct answer
                c_emb = self.sbert.encode(c, convert_to_tensor=True)
                sim = float(util.cos_sim(c_emb, correct_emb)[0][0])
                
                # Ideal distractors are somewhat related (0.3-0.7 similarity)
                # Too similar (>0.8) might be synonyms, too different (<0.2) might be irrelevant
                if 0.25 <= sim <= 0.8:
                    distractor_scores.append((c, sim))
                    seen.add(normalized_c)
        
        # Sort by distance from optimal similarity (around 0.5)
        distractor_scores.sort(key=lambda x: abs(x[1] - 0.5))
        
        final = [item[0] for item in distractor_scores]
        
        # Debug
        print(f"[DEBUG] Filtered {len(final)}/{len(cands)} distractor candidates")
        return final

    def _is_minimal_variation(self, candidate: str, existing_items: List[str]) -> bool:
        """Check if candidate is just a minimal variation of existing items."""
        for item in existing_items:
            # Check if edit distance is very small
            if abs(len(item) - len(candidate)) <= 2:
                # Simple check for differing by just one character
                if len(item) == len(candidate):
                    diff_chars = sum(1 for a, b in zip(item.lower(), candidate.lower()) if a != b)
                    if diff_chars <= 2:  # Differs by at most 2 chars
                        return True
                
                # If they're almost the same length, it's likely just a minimal difference
                len_diff = abs(len(item) - len(candidate))
                if len_diff <= 3:  # Only small differences like "a" or "the" or "s"
                    return True
                    
        return False

    def _re_rank_distractors(self, cands: List[str], correct: str, context: str, top_k: int) -> List[str]:
        if not cands:
            return []
        correct_emb = self.sbert.encode(correct, convert_to_tensor=True)
        context_emb = self.sbert.encode(context, convert_to_tensor=True)
        c_embs = self.sbert.encode(cands, convert_to_tensor=True)

        sim_ans = util.cos_sim(c_embs, correct_emb).squeeze(1)
        sim_ctx = util.cos_sim(c_embs, context_emb).squeeze(1)

        results = []
        for i, cand in enumerate(cands):
            ans_score = float(sim_ans[i])  # we want this small
            ctx_score = float(sim_ctx[i])  # we want this large
            final_score = ctx_score - ans_score
            results.append((cand, final_score))

        results.sort(key=lambda x: x[1], reverse=True)
        top = [r[0] for r in results[:top_k]]
        return top

    def _filter_distractors(self, distractors: List[str], correct: str, question: str) -> List[str]:
        """Filter out low-quality distractors."""
        filtered = []
        correct_lower = correct.lower()
        
        # Check similarity using embeddings
        correct_emb = self.sbert.encode(correct, convert_to_tensor=True)
        dist_embs = self.sbert.encode(distractors, convert_to_tensor=True)
        similarities = util.cos_sim(dist_embs, correct_emb)
        
        for i, dist in enumerate(distractors):
            dist_lower = dist.lower()
            sim = float(similarities[i])
            
            # Check if distractor is too similar or too different from correct answer
            if 0.3 < sim < 0.85 and dist_lower != correct_lower:
                # Check if distractor length is reasonable
                if 0.3 < len(dist)/len(correct) < 3:
                    filtered.append(dist)
                    
        return filtered

    def generate_distractors(self, question: str, correct_answer: str, context: str, num_distractors: int = 3) -> List[str]:
        """Generate distractors, prioritizing online LLM API for speed and quality."""
        # Start with online API if available
        if hasattr(self, 'api_key') and self.api_key:
            online_distractors = self._generate_online_distractors(correct_answer, context, num_distractors)
            if online_distractors:  # Return immediately if we have results
                return online_distractors[:num_distractors]
        
        # Only fall back to T5 if online generation failed
        t5_raw = self._generate_t5_distractors(question, correct_answer, context)
        filtered = self._filter_candidates(t5_raw, correct_answer, context)
        
        if len(filtered) >= num_distractors:
            return filtered[:num_distractors]  # Skip re-ranking for speed
        
        # Last resort: sense2vec/wordnet
        return self._sense2vec_wordnet(correct_answer, context, num_distractors)

class MCQGenerator:
    def __init__(self,
                 qa_model_path: str = "./qa",
                 distractor_model_path: str = "./distractor",
                 google_api_key: str = "AIzaSyCU4rOg50EuqY5MFm76-Wz9jLkwnOd9AQA",
                 max_retries: int = 2):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"[DEBUG] Loading QA model from {os.path.abspath(qa_model_path)}")
        self.qg_tokenizer = AutoTokenizer.from_pretrained(qa_model_path)
        self.qg_model = AutoModelForSeq2SeqLM.from_pretrained(qa_model_path).to(self.device)

        self.answer_validator = AnswerValidator()
        self.distractor_gen = DistractorGenerator(distractor_model_path, google_api_key, self.device)
        self.online_generator = EnhancedQuestionGenerator(google_api_key)
        self.max_retries = max_retries

    # Q/A approach #1
    def _generate_qa_masked(self, sentence: str) -> Dict[str, str]:
        input_text = f"context: {sentence} answer: [MASK] </s>"
        inputs = self.qg_tokenizer(
            [input_text],
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        ).to(self.device)

        with torch.no_grad():
            outputs = self.qg_model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=64,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=1.0
            )
        decoded = self.qg_tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "question:" in decoded and "answer:" in decoded:
            try:
                q_part, a_part = decoded.split("answer:")
                question = q_part.replace("question:", "").strip()
                answer = a_part.strip()
                return {"question": question, "answer": answer}
            except:
                pass
        return {"question": "Could not parse question", "answer": "Could not parse answer"}

    # Q/A approach #2
    def _extract_key_phrase(self, sentence: str) -> str:
        doc = nlp(sentence)
        noun_chunks = list(doc.noun_chunks)
        if not noun_chunks:
            return ""
        # pick longest
        noun_chunks.sort(key=lambda c: len(c.text.split()), reverse=True)
        return noun_chunks[0].text.strip()

    def _generate_qa_keyphrase(self, sentence: str) -> Dict[str, str]:
        keyp = self._extract_key_phrase(sentence)
        if not keyp:
            return {"question": "No key phrase found", "answer": "No key phrase found"}
        input_text = f"context: {sentence} answer: {keyp} </s>"
        inputs = self.qg_tokenizer(
            [input_text],
            return_tensors="pt",
            max_length=512,
            truncation=True,
            padding=True
        ).to(self.device)
        with torch.no_grad():
            outputs = self.qg_model.generate(
                inputs["input_ids"],
                attention_mask=inputs["attention_mask"],
                max_length=64,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=1.0
            )
        decoded = self.qg_tokenizer.decode(outputs[0], skip_special_tokens=True)
        if "question:" in decoded and "answer:" in decoded:
            try:
                q_part, a_part = decoded.split("answer:")
                question = q_part.replace("question:", "").strip()
                answer = a_part.strip()
                return {"question": question, "answer": answer}
            except:
                pass
        return {"question": "Could not parse question", "answer": keyp}

    def _generate_why_how_question(self, sentence: str) -> Dict[str, str]:
        """Generate why/how questions that test deeper understanding."""
        doc = nlp(sentence)
        has_cause = any(token.dep_ == "advcl" for token in doc)
        
        if has_cause:
            input_text = f"Generate a 'why' question from: {sentence} </s>"
        else:
            input_text = f"Generate a 'how' question from: {sentence} </s>"
            
        inputs = self.qg_tokenizer([input_text], return_tensors="pt", 
                                  max_length=512, truncation=True).to(self.device)
        # Rest of generation code...

    def _generate_qa_with_context(self, sentence: str, text: str) -> Dict[str, str]:
        """Generate QA using the target sentence and surrounding context."""
        sents = split_into_sentences(text)
        try:
            idx = sents.index(sentence)
            start = max(0, idx - 1)
            end = min(len(sents), idx + 2)
            context = " ".join(sents[start:end])
        except:
            context = sentence
            
        # Now use this expanded context for generation
        input_text = f"context: {context} answer: [MASK] </s>"
        # Rest of your generation code...

    def _validate_build_mcq(self, question: str, answer: str, context: str) -> Dict[str, Any]:
        """
        1) Check SBERT + type-check => if fail => dummy
        2) If pass => generate distractors
        3) combine => final MCQ
        """
        if not self.answer_validator.is_answer_plausible(question, answer, context):
            return {
                "question": "Could not generate valid question",
                "correct_answer": "No valid answer",
                "correct_option_index": 0,
                "options": ["(1)", "(2)", "(3)", "(4)"]
            }

        # distractors
        distractors = self.distractor_gen.generate_distractors(
            question=question,
            correct_answer=answer,
            context=context,
            num_distractors=3
        )
        # remove duplicates
        seen = set([answer.lower()])  # Add correct answer to seen set first
        final_dist = []
        for d in distractors:
            dl = d.lower()
            if dl not in seen:
                final_dist.append(d)
                seen.add(dl)
        if len(final_dist) < 3:
            final_dist += ["(No more distractors)"] * (3 - len(final_dist))
        final_dist = final_dist[:3]

        options = [answer] + final_dist
        random.shuffle(options)
        correct_index = options.index(answer)
        
        # Verify the correct answer is in options
        if answer not in options:
            print(f"ERROR: Correct answer '{answer}' not in options: {options}")
            options[0] = answer  # Force correct answer into first position
            correct_index = 0
        
        return {
            "question": question,
            "correct_answer": answer,
            "correct_option_index": correct_index,
            "options": options
        }

    def _score_mcq(self, mcq: Dict[str, Any]) -> float:
        """Enhanced scoring for better question selection."""
        score = 0
        question = mcq["question"]
        answer = mcq["correct_answer"]
        
        # Reward question words
        if any(qw in question.lower() for qw in ["what", "why", "how", "which", "where", "when"]):
            score += 2
            
        # Reward non-trivial questions (longer than 6 words)
        qwords = question.split()
        if len(qwords) > 6:
            score += 1
            
        # Reward questions with specific entities (names, places, etc.)
        q_doc = nlp(question)
        if len(q_doc.ents) > 0:
            score += 2
            
        # Penalize "no valid answer"
        if "no valid answer" in answer.lower():
            score -= 5
            
        # Reward diverse option lengths (avoids obvious answers)
        option_lengths = [len(opt) for opt in mcq["options"]]
        if max(option_lengths) - min(option_lengths) < 10:
            score += 1
            
        return float(score)

    def _select_key_sentences(self, text: str, count: int) -> List[str]:
        """Select important sentences based on multiple factors."""
        sents = split_into_sentences(text)
        if len(sents) <= count:
            return sents
            
        # Calculate TF-IDF to identify important terms
        from sklearn.feature_extraction.text import TfidfVectorizer
        vectorizer = TfidfVectorizer(stop_words='english')
        try:
            tfidf_matrix = vectorizer.fit_transform(sents)
            importance_scores = tfidf_matrix.sum(axis=1).A1
        except:
            # Fallback to length-based if TF-IDF fails
            importance_scores = [len(s.split()) for s in sents]
        
        # Add scores for sentences with named entities
        for i, sent in enumerate(sents):
            doc = nlp(sent)
            if len(doc.ents) > 0:
                importance_scores[i] += 2  # Bonus for sentences with entities
        
        # Add scores for sentences with key content markers
        keywords = ["important", "significant", "key", "main", "crucial", "essential"]
        for i, sent in enumerate(sents):
            if any(kw in sent.lower() for kw in keywords):
                importance_scores[i] += 1
                
        # Get top sentences
        top_indices = sorted(range(len(importance_scores)), 
                            key=lambda i: importance_scores[i], 
                            reverse=True)[:count*2]
        top_indices.sort()  # Keep original order
        return [sents[i] for i in top_indices]

    def _select_question_type(self, sentence, story_elements):
        """Choose appropriate question type based on sentence content."""
        doc = nlp(sentence)
        
        # Look for cause-effect relationships for "why" questions
        has_causal = any(token.dep_ == "advcl" for token in doc)
        
        # Look for action verbs for "how" questions
        has_action = any(token.pos_ == "VERB" and token.dep_ == "ROOT" for token in doc)
        
        # Look for character names for "who" questions
        has_character = any(ent.label_ == "PERSON" for ent in doc.ents)
        
        # Look for locations for "where" questions
        has_location = any(ent.label_ == "LOC" or ent.label_ == "GPE" for ent in doc.ents)
        
        if has_causal:
            return "why"
        elif has_action:
            return "how"
        elif has_character:
            return "who"
        elif has_location:
            return "where"
        else:
            return "what"  # Default

    def generate_multiple_mcqs(self, text: str, user_requested_count: int = 5) -> List[Dict[str, Any]]:
        """Generate multiple MCQs from text with improved quality and diversity."""
        all_questions = []
        
        # Skip segmentation for LLM - send complete text for better context understanding
        if hasattr(self.distractor_gen, 'api_key') and self.distractor_gen.api_key:
            try:
                print(f"[DEBUG] Attempting LLM generation for complete text...")
                enhanced_questions = self.online_generator.generate_questions(
                    text, user_requested_count * 1.5)  # Request extra questions for filtering
                
                if enhanced_questions:
                    # Apply minimal validation - trust LLM output more
                    validated_questions = []
                    for q in enhanced_questions:
                        # Simple validation - skip semantic validation for speed
                        if q['answer'] and len(q['answer']) >= 2 and q['answer'].lower() in text.lower():
                            validated_questions.append({
                                'question': q['question'],
                                'answer': q['answer'],
                                'context': text,
                                'quality_score': 3.0,  # Higher score for LLM questions
                                'source': 'llm'
                            })
                    
                    if len(validated_questions) >= user_requested_count:
                        # We have enough questions from LLM, proceed directly to MCQ creation
                        final_questions = validated_questions[:user_requested_count]
                        return self._convert_to_mcqs(final_questions)
            except Exception as e:
                print(f"[DEBUG] LLM generation error: {e}")
        
        # Fall back to traditional methods only if LLM didn't produce enough
        segments = self._segment_text_intelligently(text)
        fallback_questions = self._process_segments_batch(segments, user_requested_count)
        
        # Use simple deduplication instead of expensive semantic similarity
        seen_questions = set()
        unique_fallbacks = []
        for q in fallback_questions:
            q_lower = q['question'].lower()
            if q_lower not in seen_questions:
                unique_fallbacks.append(q)
                seen_questions.add(q_lower)
        
        final_questions = unique_fallbacks[:user_requested_count]
        return self._convert_to_mcqs(final_questions)

    def _convert_to_mcqs(self, questions):
        """Helper method to convert questions to MCQs with options"""
        final_mcqs = []
        for q in questions:
            distractors = self.distractor_gen.generate_distractors(
                q['question'], q['answer'], q['context'], 3)
                
            options = [q['answer']] + distractors
            random.shuffle(options)
            
            mcq = {
                "question": q['question'],
                "correct_answer": q['answer'],
                "options": options,
                "correct_option_index": options.index(q['answer']),
                "context": q['context']
            }
            final_mcqs.append(mcq)
        
        return final_mcqs

    def _generate_questions_from_segment(self, segment_text, count=5):
        """Generate questions from a text segment using multiple approaches."""
        questions = []
        
        # Try enhanced approach first if API key is available
        if hasattr(self.distractor_gen, 'api_key') and self.distractor_gen.api_key:
            try:
                print(f"[DEBUG] Calling online generator for text: {segment_text[:50]}...")
                enhanced_questions = self.online_generator.generate_questions(segment_text, count)
                
                if not enhanced_questions:
                    print(f"[DEBUG] Online generator returned no questions, falling back")
                else:
                    print(f"[DEBUG] Online generator returned {len(enhanced_questions)} questions")
                    
                    # Apply enhanced validation 
                    validated_questions = self.online_generator.validate_pairs(
                        enhanced_questions, segment_text, self.answer_validator)
                    
                    for q in validated_questions:
                        questions.append({
                            'question': q['question'],
                            'answer': q['answer'],
                            'context': segment_text,
                            'quality_score': 2.0  # Enhanced questions get higher base score
                        })
            except Exception as e:
                print(f"[DEBUG] Error using online generator: {e}")
        
        # FALLBACK: If we still don't have enough questions, use local generation methods
        if len(questions) < count:
            print(f"[DEBUG] Falling back to local question generation methods")
            sentences = split_into_sentences(segment_text)
            top_sentences = self._select_key_sentences(segment_text, count*2)
            
            for sent in top_sentences[:count*2]:
                # Generate using mask approach
                qa1 = self._generate_qa_masked(sent)
                if self.answer_validator.is_answer_plausible(qa1['question'], qa1['answer'], sent):
                    questions.append({
                        'question': qa1['question'], 
                        'answer': qa1['answer'],
                        'context': segment_text,
                        'quality_score': 1.0
                    })
                
                # Generate using keyphrase approach
                qa2 = self._generate_qa_keyphrase(sent)
                if self.answer_validator.is_answer_plausible(qa2['question'], qa2['answer'], sent):
                    questions.append({
                        'question': qa2['question'], 
                        'answer': qa2['answer'],
                        'context': segment_text,
                        'quality_score': 1.0
                    })
                    
                # Exit early if we have enough
                if len(questions) >= count*2:
                    break
        
        # Verify and return results
        verified_questions = [q for q in questions if self._verify_answer_in_context(
            q['question'], q['answer'], segment_text)]
        
        return verified_questions

    def _verify_answer_in_context(self, question, answer, context):
        """Verify that the answer is actually supported by the context."""
        # Implement additional verification logic here
        # For example, check if key terms from answer appear in context
        answer_terms = [term for term in answer.lower().split() if len(term) > 3]
        
        # For longer answers, at least some significant terms should appear in context
        if len(answer_terms) > 1:
            matches = sum(1 for term in answer_terms if term in context.lower())
            if matches < 1:
                print(f"[DEBUG] Answer terms not found in context: {answer}")
                return False
        
        # Use existing validator as backup
        return self.answer_validator.is_answer_plausible(question, answer, context)

    def _ensure_question_diversity(self, questions: List[Dict]) -> List[Dict]:
        """Ensure a mix of question types and cognitive levels."""
        # Group questions by type
        question_by_type = {}
        for q in questions:
            q_text = q['question'].lower()
            q_type = next((t for t in ["what", "who", "where", "when", "why", "how"] if q_text.startswith(t)), "other")
            if q_type not in question_by_type:
                question_by_type[q_type] = []
            question_by_type[q_type].append(q)
        
        # Prioritize diversity in the final selection
        diverse_questions = []
        remaining = []
        
        # Take top questions from each type
        for q_type, qs in question_by_type.items():
            if qs:
                # Sort by quality score
                sorted_qs = sorted(qs, key=lambda x: x.get('quality_score', 0), reverse=True)
                # Take the best question of each type
                diverse_questions.append(sorted_qs[0])
                # Add the rest to remaining
                remaining.extend(sorted_qs[1:])
        
        # Sort remaining by quality score
        remaining = sorted(remaining, key=lambda x: x.get('quality_score', 0), reverse=True)
        
        # Return diverse questions + top remaining up to the requested count
        return diverse_questions + remaining

    def _process_segments_batch(self, segments, count_per_segment):
        """Process segments in parallel for better performance."""
        # First try with concurrent futures, but fall back to sequential if that fails
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = []
                for segment in segments:
                    futures.append(
                        executor.submit(self._generate_questions_from_segment, segment, count_per_segment)
                    )
                
                # Collect results as they complete
                all_questions = []
                for future in concurrent.futures.as_completed(futures):
                    try:
                        segment_questions = future.result()
                        if segment_questions:
                            all_questions.extend(segment_questions)
                    except Exception as e:
                        print(f"[DEBUG] Error processing segment: {str(e)}")
                        
                return all_questions
        except Exception as e:
            print(f"[DEBUG] Error in parallel processing, falling back to sequential: {str(e)}")
            # Fall back to sequential processing if concurrent fails
            all_questions = []
            for segment in segments:
                try:
                    segment_questions = self._generate_questions_from_segment(segment, count_per_segment)
                    if segment_questions:
                        all_questions.extend(segment_questions)
                except Exception as e:
                    print(f"[DEBUG] Error processing segment sequentially: {str(e)}")
            return all_questions

    def _is_similar_question(self, question1, question2):
        """Check if two questions are semantically similar to avoid duplicates."""
        # Simple text matching
        if question1.lower() == question2.lower():
            return True
            
        # Check for substring containment
        if question1.lower() in question2.lower() or question2.lower() in question1.lower():
            return True
        
        # Use SBERT for more sophisticated matching
        q1_emb = self.distractor_gen.sbert.encode(question1, convert_to_tensor=True)
        q2_emb = self.distractor_gen.sbert.encode(question2, convert_to_tensor=True)
        similarity = float(util.cos_sim(q1_emb, q2_emb)[0][0])
        
        # Higher threshold for considering questions similar
        return similarity > 0.8

    def _segment_text_intelligently(self, text: str) -> List[str]:
        """
        Split text into logical segments for better question generation.
        Tries to keep related sentences together while limiting segment size.
        """
        # First split into sentences
        sentences = split_into_sentences(text)
        
        # For very short texts, return the whole text as a single segment
        if len(sentences) <= 5:
            return [text]
        
        # For longer texts, segment into logical chunks
        segments = []
        current_segment = []
        current_length = 0
        max_segment_length = 1000  # Characters
        
        for sentence in sentences:
            # If adding this sentence would make segment too long, start a new segment
            # Unless this is the first sentence in the segment
            if current_length + len(sentence) > max_segment_length and current_segment:
                segments.append(" ".join(current_segment))
                current_segment = [sentence]
                current_length = len(sentence)
            else:
                current_segment.append(sentence)
                current_length += len(sentence)
        
        # Don't forget the last segment
        if current_segment:
            segments.append(" ".join(current_segment))
        
        return segments
