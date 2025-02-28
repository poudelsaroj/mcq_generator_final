# distractor_generator.py
import random
import requests
from typing import List, Optional, Tuple
import spacy
import nltk
from nltk.corpus import wordnet as wn
from sentence_transformers import SentenceTransformer, util
import torch

from utils import (
    nlp, is_time_phrase, is_synonym_or_lemma, is_partial_match,
    spacy_pos_to_wordnet_pos, extract_main_token
)

try:
    from sense2vec import Sense2Vec
    s2v = Sense2Vec().from_disk("s2v_old")
    s2v_available = True
except Exception as e:
    print(f"Sense2Vec not available: {e}")
    s2v = None
    s2v_available = False

class DistractorGenerator:
    """Generate distractors for multiple-choice questions."""
    
    def __init__(self):
        """Initialize the distractor generator."""
        # Load SBERT for distractor re-ranking
        self.sbert_model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def generate_time_distractors(self, time_text: str, num_distractors: int = 3) -> List[str]:
        """Generate distractors for time expressions like 'early 1990s'."""
        pattern = r"(early|late|mid)\s+(\d{4})s"
        match = re.search(pattern, time_text.lower())
        if not match:
            return ["in the early 2000s", "in the mid 1990s", "in the late 1980s"][:num_distractors]
        
        descriptor = match.group(1)
        decade_str = match.group(2)
        try:
            decade_int = int(decade_str)
        except:
            decade_int = 1990
            
        descriptors = ["early", "mid", "late"]
        shifts = [-1, 0, 1, 2, -2]
        candidates = []
        
        for desc in descriptors:
            for shift in shifts:
                new_decade = decade_int + (shift * 10)
                if desc == descriptor and new_decade == decade_int:
                    continue
                cand = f"in the {desc} {new_decade}s"
                candidates.append(cand)
                
        random.shuffle(candidates)
        return candidates[:num_distractors]
    
    def generate_location_distractors(self, location_text: str, num_distractors: int = 3) -> List[str]:
        """Generate distractors for location entities."""
        locations = ["London", "Berlin", "Tokyo", "Sydney", "New York", "Paris", "Beijing", "Moscow", "Cairo"]
        random.shuffle(locations)
        return locations[:num_distractors]
    
    def generate_person_distractors(self, person_text: str, num_distractors: int = 3) -> List[str]:
        """Generate distractors for person entities."""
        people = ["John Smith", "Marie Curie", "Albert Einstein", "Stephen Hawking", "Jane Austen", 
                  "Barack Obama", "Nelson Mandela", "Mahatma Gandhi", "Leonardo da Vinci"]
        random.shuffle(people)
        return people[:num_distractors]
    
    def get_conceptnet_candidates(self, word: str, language: str = "en", limit: int = 50) -> List[str]:
        """Get related terms from ConceptNet."""
        url = f"http://api.conceptnet.io/c/{language}/{word}?limit={limit}"
        try:
            resp = requests.get(url)
            if resp.status_code != 200:
                return []
            data = resp.json()
            candidates = []
            for edge in data.get("edges", []):
                for node in [edge.get("start", {}), edge.get("end", {})]:
                    term = node.get("term", "")
                    parts = term.split("/")
                    if len(parts) >= 4:
                        candidate = parts[3].replace("_", " ").strip()
                        if candidate.lower() != word.lower():
                            candidates.append(candidate)
            return list(set(candidates))
        except:
            return []
    
    def wordnet_candidates(self, word: str, pos=wn.NOUN) -> List[str]:
        """Get related terms from WordNet."""
        distractors = set()
        synsets = wn.synsets(word, pos=pos)
        if not synsets:
            return []
            
        # Add synonyms
        for syn in synsets:
            for lemma in syn.lemmas():
                lw = lemma.name().replace("_", " ")
                if lw.lower() != word.lower():
                    distractors.add(lw)
        
        # Add hypernyms -> hyponyms
        for syn in synsets:
            for hyper in syn.hypernyms():
                for hypo in hyper.hyponyms():
                    for lemma in hypo.lemmas():
                        lw = lemma.name().replace("_", " ")
                        if lw.lower() != word.lower():
                            distractors.add(lw)
                            
        return list(distractors)
    
    def sense2vec_candidates(self, tagged_word: str, topn: int = 15) -> List[str]:
        """Get similar terms from Sense2Vec."""
        if not s2v_available:
            return []
            
        candidates = []
        try:
            sim_list = s2v.most_similar(tagged_word, n=topn)
            for cand, score in sim_list:
                cand_word = cand.split("|")[0]
                if cand_word.lower() != tagged_word.split("|")[0].lower():
                    candidates.append(cand_word)
        except (KeyError, ValueError):
            # Fallback if sense2vec doesn't have this key
            pass
            
        return list(set(candidates))
    
    def filter_candidates(self, candidates: List[str], correct_answer: str, context: str) -> List[str]:
        """Filter candidates to remove irrelevant distractors."""
        context_lower = context.lower()
        filtered = []
        
        for c in candidates:
            c_lower = c.lower()
            # Skip if synonym or direct match
            if is_synonym_or_lemma(c, correct_answer):
                continue
            # Skip if partial match (e.g., "photosynthetic" vs "photosynthesis")
            if is_partial_match(c, correct_answer):
                continue
            # Skip if appears in context
            if c_lower in context_lower:
                continue
            # Skip if contains correct answer
            if correct_answer.lower() in c_lower:
                continue
                
            filtered.append(c)
            
        return list(set(filtered))
    
    def threshold_rerank(
        self,
        candidates: List[str],
        correct_answer: str,
        context: str,
        answer_sim_threshold: float = 0.8,
        context_sim_threshold: float = 0.3,
        top_k: int = 3
    ) -> List[str]:
        """Re-rank candidates based on semantic similarity."""
        if not candidates:
            return []
            
        correct_emb = self.sbert_model.encode(correct_answer, convert_to_tensor=True)
        context_emb = self.sbert_model.encode(context, convert_to_tensor=True)
        candidate_embs = self.sbert_model.encode(candidates, convert_to_tensor=True)
        
        sim_ans = util.cos_sim(candidate_embs, correct_emb).squeeze(dim=1)
        sim_ctx = util.cos_sim(candidate_embs, context_emb).squeeze(dim=1)
        
        results = []
        for i, cand in enumerate(candidates):
            ans_score = float(sim_ans[i])
            ctx_score = float(sim_ctx[i])
            
            # We want distractors that are not too similar to the answer
            # but are related to the context
            if ans_score < answer_sim_threshold and ctx_score > context_sim_threshold:
                final_score = ctx_score - ans_score
                results.append((cand, final_score))
                
        results.sort(key=lambda x: x[1], reverse=True)
        return [r[0] for r in results[:top_k]]
    
    def generate_best_distractors(self, correct_answer: str, context: str, num_distractors: int = 3) -> List[str]:
        """Generate the best distractors for a given answer and context."""
        # Check if time phrase
        if is_time_phrase(correct_answer):
            return self.generate_time_distractors(correct_answer, num_distractors)
        
        # Check if named entity
        doc_ent = nlp(correct_answer)
        if doc_ent.ents:
            ent = doc_ent.ents[0]
            label = ent.label_
            if label in ["GPE", "LOC"]:
                return self.generate_location_distractors(correct_answer, num_distractors)
            elif label in ["PERSON", "ORG"]:
                return self.generate_person_distractors(correct_answer, num_distractors)
        
        # Single word or multiword
        tokens = correct_answer.split()
        multiword = (len(tokens) > 1)
        
        if not multiword:
            # Single word approach
            doc2 = nlp(correct_answer)
            if doc2 and len(doc2) == 1:
                spacy_pos = doc2[0].tag_
                wn_pos = spacy_pos_to_wordnet_pos(spacy_pos)
            else:
                wn_pos = wn.NOUN
            
            # Get candidates from multiple sources
            cnet_cands = self.get_conceptnet_candidates(correct_answer)
            wn_cands = self.wordnet_candidates(correct_answer, pos=wn_pos)
            
            # Sense2Vec
            if wn_pos == wn.NOUN:
                s2v_tag = f"{correct_answer}|NOUN"
            elif wn_pos == wn.VERB:
                s2v_tag = f"{correct_answer}|VERB"
            elif wn_pos == wn.ADJ:
                s2v_tag = f"{correct_answer}|ADJ"
            else:
                s2v_tag = f"{correct_answer}|NOUN"
                
            s2v_cands = self.sense2vec_candidates(s2v_tag, topn=15)
            
            # Combine, filter, and re-rank
            all_cands = list(set(cnet_cands + wn_cands + s2v_cands))
            filtered = self.filter_candidates(all_cands, correct_answer, context)
            final_distractors = self.threshold_rerank(filtered, correct_answer, context, top_k=num_distractors)
            
            return final_distractors
        else:
            # Multiword approach
            main_token = extract_main_token(correct_answer)
            doc3 = nlp(main_token)
            if doc3:
                wn_pos = spacy_pos_to_wordnet_pos(doc3[0].tag_)
            else:
                wn_pos = wn.NOUN
            
            # Get candidates from multiple sources
            cnet_cands = self.get_conceptnet_candidates(correct_answer)
            wn_cands = self.wordnet_candidates(correct_answer, wn_pos)
            
            # Sense2Vec for main token
            if wn_pos == wn.NOUN:
                s2v_tag = f"{main_token}|NOUN"
            elif wn_pos == wn.VERB:
                s2v_tag = f"{main_token}|VERB"
            elif wn_pos == wn.ADJ:
                s2v_tag = f"{main_token}|ADJ"
            else:
                s2v_tag = f"{main_token}|NOUN"
                
            s2v_cands = self.sense2vec_candidates(s2v_tag, topn=15)
            
            # Combine, filter, and re-rank
            all_cands = list(set(cnet_cands + wn_cands + s2v_cands))
            filtered = self.filter_candidates(all_cands, correct_answer, context)
            final_distractors = self.threshold_rerank(filtered, correct_answer, context, top_k=num_distractors)
            
            return final_distractors