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
    Raises the threshold to 0.4 to ensure answers are more relevant.
    Also do a minimal type check if question has certain keywords.
    """
    def __init__(self):
        self.sbert = SentenceTransformer("all-MiniLM-L6-v2")
        self.threshold = 0.4  # higher threshold than 0.15

    def is_answer_plausible(self, question: str, answer: str, context: str) -> bool:
        # Type-check rule first
        if not question_answer_type_check(question, answer):
            print(f"[DEBUG] Type-check failed: Q='{question}' => A='{answer}'")
            return False

        if not answer.strip() or "could not parse" in answer.lower():
            return False

        ans_emb = self.sbert.encode(answer, convert_to_tensor=True)
        ctx_emb = self.sbert.encode(context, convert_to_tensor=True)
        sim = float(util.cos_sim(ans_emb, ctx_emb)[0][0])
        print(f"[DEBUG] SBERT check: answer='{answer}' sim={sim:.3f}, threshold={self.threshold}")
        return sim >= self.threshold

class DistractorGenerator:
    """
    T5 => if <3 => LLM => if <3 => sense2vec => if <3 => emergency
    + generats up to 5 T5 distractors to reduce fallback usage.
    + retries LLM once if code=429 (ex: usage limit).
    """

    def __init__(self, distractor_model_path: str, openrouter_api_key: str, device: str):
        self.device = device
        print(f"[DEBUG] Loading T5 distractor from: {os.path.abspath(distractor_model_path)}")
        self.dist_tokenizer = AutoTokenizer.from_pretrained(distractor_model_path)
        self.dist_model = AutoModelForSeq2SeqLM.from_pretrained(distractor_model_path).to(self.device)
        self.api_key = openrouter_api_key
        self.sbert = SentenceTransformer("all-MiniLM-L6-v2")

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
        """
        We'll do up to 2 attempts if we see a 429 error from the provider.
        """
        if not self.api_key:
            return self._emergency_fallback(correct, context, num_distractors)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://mcq-generator.app",
            "X-Title": "MCQ Generator",
            "Content-Type": "application/json"
        }
        prompt = (
            f"Generate {num_distractors} plausible but incorrect multiple-choice answers where "
            f"'{correct}' is correct, from context '{context}'. Only a comma list, no extras."
        )
        payload = {
            "model": "google/gemini-2.0-flash-lite-preview-02-05:free",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        try:
            resp = requests.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, data=json.dumps(payload))
            print(f"[DEBUG] LLM status={resp.status_code} text={resp.text[:200]}...")

            if resp.status_code == 200:
                data = resp.json()
                if "choices" not in data or not data["choices"]:
                    print("[DEBUG] No 'choices' in LLM response => emergency fallback")
                    return self._emergency_fallback(correct, context, num_distractors)
                text_out = data["choices"][0]["message"]["content"].strip()
                cands = [x.strip() for x in text_out.split(",") if x.strip()]
                cands = [re.sub(r'^\d+\.\s*', '', c) for c in cands]
                filtered = self._filter_candidates(cands, correct, context)
                if len(filtered) < num_distractors:
                    needed = num_distractors - len(filtered)
                    more = self._emergency_fallback(correct, context, needed)
                    filtered.extend(more)
                return filtered[:num_distractors]
            else:
                # If 429 => wait 2 seconds, try again once
                if resp.status_code == 429 and attempt < 2:
                    print("[DEBUG] LLM got 429 => sleeping 2s and retrying once more.")
                    time.sleep(2)
                    return self._generate_llm_distractors(correct, context, num_distractors, attempt=2)

                return self._emergency_fallback(correct, context, num_distractors)

        except Exception as e:
            print(f"[DEBUG] LLM exception: {e}")
            return self._emergency_fallback(correct, context, num_distractors)

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
        for c in cands:
            dlow = c.lower()
            if dlow not in seen and clower not in dlow:
                final.append(c)
                seen.add(dlow)
        return final

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

    def generate_distractors(self, question: str, correct_answer: str, context: str, num_distractors: int = 3) -> List[str]:
        # 1) T5 local (with up to 5 sequences)
        t5_raw = self._generate_t5_distractors(question, correct_answer, context)
        filtered = self._filter_candidates(t5_raw, correct_answer, context)
        # If <3 => LLM
        if len(filtered) < num_distractors:
            llm = self._generate_llm_distractors(correct_answer, context, num_distractors)
            return llm
        else:
            # re-rank T5
            final_t5 = self._re_rank_distractors(filtered, correct_answer, context, top_k=num_distractors)
            if len(final_t5) < num_distractors:
                # fallback LLM
                llm = self._generate_llm_distractors(correct_answer, context, num_distractors)
                if len(llm) < num_distractors:
                    # sense2vec
                    return self._sense2vec_wordnet(correct_answer, context, num_distractors)
                return llm
            return final_t5


class MCQGenerator:
    """
    Enhanced pipeline:
    1) chunk text => top sentences
    2) for each sentence => two Q/A approaches:
       - [MASK]
       - Key phrase
    3) validate Q/A with:
       - higher SBERT threshold
       - minimal question->answer type check
    4) T5 distractors => LLM => sense2vec => emergency
    5) remove duplicates, re-rank, return top user_requested_count
    """

    def __init__(self,
                 qa_model_path: str = "./qa",
                 distractor_model_path: str = "./distractor",
                 openrouter_api_key: str = "",
                 max_retries: int = 2):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[DEBUG] Loading QA model from {os.path.abspath(qa_model_path)}")
        self.qg_tokenizer = AutoTokenizer.from_pretrained(qa_model_path)
        self.qg_model = AutoModelForSeq2SeqLM.from_pretrained(qa_model_path).to(self.device)

        self.answer_validator = AnswerValidator()
        self.distractor_gen = DistractorGenerator(distractor_model_path, openrouter_api_key, self.device)
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
        seen = set()
        final_dist = []
        for d in distractors:
            dl = d.lower()
            if dl not in seen and dl != answer.lower():
                final_dist.append(d)
                seen.add(dl)
        if len(final_dist) < 3:
            final_dist += ["(No more distractors)"] * (3 - len(final_dist))
        final_dist = final_dist[:3]

        options = [answer] + final_dist
        random.shuffle(options)
        return {
            "question": question,
            "correct_answer": answer,
            "correct_option_index": options.index(answer),
            "options": options
        }

    def _score_mcq(self, mcq: Dict[str, Any]) -> float:
        """
        Re-rank final MCQs by simple heuristics:
          +1 if question has >6 words
          +1 if correct_answer != "No valid answer"
        """
        score = 0
        qwords = mcq["question"].split()
        if len(qwords) > 6:
            score += 1
        if "no valid answer" not in mcq["correct_answer"].lower():
            score += 1
        return float(score)

    def generate_multiple_mcqs(self, text: str, user_requested_count: int) -> List[Dict[str, Any]]:
        """
        1) chunk by sentences
        2) produce 2 QA approaches per sentence => up to 2 MCQs
        3) validate => build final MCQ
        4) remove duplicates
        5) re-rank => pick top user_requested_count
        """
        # step1: pick top user_requested_count*2 sentences by length
        sents = split_into_sentences(text)
        scored_sents = [(s, len(s.split())) for s in sents]
        scored_sents.sort(key=lambda x: x[1], reverse=True)
        top_sents = [x[0] for x in scored_sents[:user_requested_count * 2]]

        mcqs = []
        for sent in top_sents:
            # approach 1: masked
            qaA = self._generate_qa_masked(sent)
            mcqA = self._validate_build_mcq(qaA["question"], qaA["answer"], sent)
            mcqs.append(mcqA)

            # approach 2: key phrase
            qaB = self._generate_qa_keyphrase(sent)
            mcqB = self._validate_build_mcq(qaB["question"], qaB["answer"], sent)
            mcqs.append(mcqB)

            if len(mcqs) >= user_requested_count * 3:  # some margin
                break

        # remove duplicates by question
        unique_mcqs = remove_duplicate_questions(mcqs)

        # re-rank
        scored = []
        for m in unique_mcqs:
            s = self._score_mcq(m)
            scored.append((m, s))
        scored.sort(key=lambda x: x[1], reverse=True)

        final = [x[0] for x in scored[:user_requested_count]]
        return final
