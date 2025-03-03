

###############################################################################
# 2) IMPORT AFTER CHECKING REQUIREMENTS
###############################################################################
import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

###############################################################################
# 3) HARDCODED PASSAGE & CONFIG
###############################################################################
PASSAGE = ('''
  Nepal,[a] officially the Federal Democratic Republic of Nepal,[b] is a landlocked country in South Asia. It is mainly situated in the Himalayas, but also includes parts of the Indo-Gangetic Plain. It borders the Tibet Autonomous Region of China to the north, and India to the south, east, and west, while it is narrowly separated from Bangladesh by the Siliguri Corridor, and from Bhutan by the Indian state of Sikkim. Nepal has a diverse geography, including fertile plains, subalpine forested hills, and eight of the world's ten tallest mountains, including Mount Everest, the highest point on Earth. Kathmandu is the nation's capital and the largest city. Nepal is a multi-ethnic, multi-lingual, multi-religious, and multi-cultural state, with Nepali as the official language.

The name "Nepal" is first recorded in texts from the Vedic period of the Indian subcontinent, the era in ancient Nepal when Hinduism was founded, the predominant religion of the country. In the middle of the first millennium BC, Gautama Buddha, the founder of Buddhism, was born in Lumbini in southern Nepal. Parts of northern Nepal were intertwined with the culture of Tibet. The centrally located Kathmandu Valley is intertwined with the culture of Indo-Aryans, and was the seat of the prosperous Newar confederacy known as Nepal Mandala. The Himalayan branch of the ancient Silk Road was dominated by the valley's traders. The cosmopolitan region developed distinct traditional art and architecture. By the 18th century, the Gorkha Kingdom achieved the unification of Nepal. The Shah dynasty established the Kingdom of Nepal and later formed an alliance with the British Empire, under its Rana dynasty of premiers. The country was never colonised but served as a buffer state between Imperial China and British India. Parliamentary democracy was introduced in 1951 but was twice suspended by Nepalese monarchs, in 1960 and 2005. The Nepalese Civil War in the 1990s and early 2000s resulted in the establishment of a secular republic in 2008, ending the world's last Hindu monarchy.

The Constitution of Nepal, adopted in 2015, affirms the country as a federal parliamentary republic divided into seven provinces. Nepal was admitted to the United Nations in 1955, and friendship treaties were signed with India in 1950 and China in 1960. Nepal hosts the permanent secretariat of the South Asian Association for Regional Cooperation (SAARC), of which it is a founding member. Nepal is also a member of the Non-Aligned Movement and the Bay of Bengal Initiative.

Etymology
Main article: Name of Nepal
Before the unification of Nepal, the Kathmandu Valley was known as Nepal.[c] The precise origin of the term Nepāl is uncertain. Nepal appears in ancient Indian literary texts dated as far back as the fourth century AD.[16] An absolute chronology can not be established, as even the oldest texts may contain anonymous contributions dating as late as the early modern period. Academic attempts to provide a plausible theory are hindered by the lack of a complete picture of history and insufficient understanding of linguistics or relevant Indo-European and Tibeto-Burman languages.[17]

According to Hindu mythology, Nepal derives its name from an ancient Hindu sage called Ne, referred to variously as Ne Muni or Nemi. According to Pashupati Purāna, as a place protected by Ne, the country in the heart of the Himalayas came to be known as Nepāl.[18][19][d] According to Nepāl Mahātmya,[e] Nemi was charged with protection of the country by Pashupati.[20] According to Buddhist mythology, Manjushri Bodhisattva drained a primordial lake of serpents to create the Nepal valley and proclaimed that Adi-Buddha Ne would take care of the community that would settle it. As the cherished of Ne, the valley would be called Nepāl.[21] According to Gopalarājvamshāvali, the genealogy of ancient Gopala dynasty compiled c. 1380s, Nepal is named after Nepa the cowherd, the founder of the Nepali scion of the Abhiras. In this account, the cow that issued milk to the spot, at which Nepa discovered the Jyotirlinga of Pashupatināth upon investigation, was also named Ne.[17]

The Ne Muni etymology was rightly dismissed by the early European visitors.[22] Norwegian indologist Christian Lassen proposed that Nepāla was a compound of Nipa (foot of a mountain) and -ala (short suffix for alaya meaning abode), and so Nepāla meant "abode at the foot of the mountain".[23] Indologist Sylvain Levi found Lassen's theory untenable but had no theories of his own, only suggesting that either Newara is a vulgarism of sanskritic Nepala, or Nepala is Sanskritisation of the local ethnic;[24] his view has found some support though it does not answer the question of etymology.[25][26][27][17] It has also been proposed that Nepa is a Tibeto-Burman stem consisting of Ne (cattle) and Pa (keeper), reflecting the fact that early inhabitants of the valley were Gopalas (cowherds) and Mahispalas (buffalo-herds).[17] Suniti Kumar Chatterji believed Nepal originated from Tibeto-Burman roots – Ne, of uncertain meaning (as multiple possibilities exist), and pala or bal, whose meaning is lost entirely.[28]


''')
NUMBER_OF_QUESTIONS = 3

###############################################################################
# 4) LOCAL MODEL DIRECTORIES
###############################################################################
# Update these paths to wherever you downloaded and stored the model repos:
QG_MODEL_DIR = "/media/saroj/New Volume/own/qa"
DISTRACTOR_MODEL_DIR = "/media/saroj/New Volume/own/distractor"

###############################################################################
# 5) SETUP QUESTION GENERATION MODEL (Local T5-Base)
###############################################################################
print("\nLoading Question Generation Model from local directory...")
qg_tokenizer = AutoTokenizer.from_pretrained(QG_MODEL_DIR)
qg_model = AutoModelForSeq2SeqLM.from_pretrained(QG_MODEL_DIR)

def generate_qa(context, answer="[MASK]", max_length=64,
                do_sample=True, top_k=50, top_p=0.95, temperature=1.0):
    """
    Generates a question and (optionally masked) answer from the provided context.
    Returns a string in the format:
        "question: <QUESTION> answer: <ANSWER>"
    """
    input_text = f"context: {context} answer: {answer} </s>"
    inputs = qg_tokenizer([input_text], return_tensors="pt", truncation=True, padding=True)
    
    outputs = qg_model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        max_length=max_length,
        do_sample=do_sample,
        top_k=top_k,
        top_p=top_p,
        temperature=temperature,
        num_return_sequences=1
    )
    return qg_tokenizer.decode(outputs[0], skip_special_tokens=True)

###############################################################################
# 6) SETUP DISTRACTOR GENERATION MODEL (Local T5-Large)
###############################################################################
print(f"Loading Distractor Generation Model from local directory...")
dist_tokenizer = AutoTokenizer.from_pretrained(DISTRACTOR_MODEL_DIR)
dist_model = AutoModelForSeq2SeqLM.from_pretrained(DISTRACTOR_MODEL_DIR)

SEP_TOKEN = "<sep>"

def generate_distractors(question, context, correct, max_length=64,
                         do_sample=True, top_k=50, top_p=0.95, temperature=1.0):
    """
    Generates three distractors given:
      - question (string)
      - correct answer (string)
      - context (string)

    The T5-large model expects the input format:
      question<sep>correct<sep>context

    Returns a list of strings [distractor1, distractor2, distractor3].
    """
    input_text = f"{question}{SEP_TOKEN}{correct}{SEP_TOKEN}{context}"
    inputs = dist_tokenizer([input_text], return_tensors="pt", truncation=True, padding=True)
    
    outputs = dist_model.generate(
        input_ids=inputs["input_ids"],
        attention_mask=inputs["attention_mask"],
        max_length=max_length,
        do_sample=do_sample,
        top_k=top_k,
        top_p=top_p,
        temperature=temperature,
        num_return_sequences=1
    )
    
    decoded = dist_tokenizer.decode(outputs[0], skip_special_tokens=True, clean_up_tokenization_spaces=True)
    distractors = [d.strip() for d in decoded.split(SEP_TOKEN)]
    return distractors

###############################################################################
# 7) MAIN FUNCTION
###############################################################################
def main():
    print("\n==============================")
    print("MCQ Generation Demo with Local T5")
    print("==============================\n")
    
    passage = PASSAGE
    num_questions = NUMBER_OF_QUESTIONS

    print(f"Passage:\n{passage}\n")
    print(f"Generating {num_questions} MCQs...\n")

    for i in range(num_questions):
        # Step 1: Generate Q & A from the passage
        qa_output = generate_qa(context=passage, answer="[MASK]")
        
        # The model returns something like: "question: <Q> answer: <A>"
        if "question:" in qa_output and "answer:" in qa_output:
            try:
                question_part, answer_part = qa_output.split("answer:")
                question_text = question_part.replace("question:", "").strip()
                correct_answer = answer_part.strip()
            except ValueError:
                question_text = "Could not parse question."
                correct_answer = "Could not parse answer."
        else:
            question_text = "Could not parse question."
            correct_answer = "Could not parse answer."
        
        # Step 2: Generate 3 distractors using Local T5-Large
        distractors = generate_distractors(question_text, passage, correct_answer)
        
        # Step 3: Print the MCQ
        print(f"Q{i+1}. {question_text}")
        print(f"   A) {correct_answer}")
        
        if len(distractors) == 3:
            print(f"   B) {distractors[0]}")
            print(f"   C) {distractors[1]}")
            print(f"   D) {distractors[2]}")
        else:
            print("   (Could not generate 3 distinct distractors)")
            for idx, dist_text in enumerate(distractors, start=1):
                print(f"   Distractor {idx}: {dist_text}")
        print()

if __name__ == "__main__":
    main()
