# demo.py
from mcq_generator import MCQGenerator
import json

def print_mcq(mcq):
    """Pretty print an MCQ."""
    print("=" * 60)
    print("PASSAGE:")
    print(mcq["passage"])
    print("\nQUESTION:")
    print(mcq["question"])
    print("\nOPTIONS:")
    for i, option in enumerate(mcq["options"]):
        marker = "*" if option == mcq["correct_answer"] else " "
        print(f"{marker} {i+1}) {option}")
    print(f"\nCORRECT ANSWER: {mcq['correct_answer']}")
    print("=" * 60)

if __name__ == "__main__":
    # Initialize the MCQ generator
    mcq_gen = MCQGenerator(model_path="checkpoint-400")
    
    # Example passages
    passages = [
        "Machine learning is a field of inquiry devoted to understanding and building methods that 'learn', that is, methods that leverage data to improve performance on some set of tasks. It is seen as a part of artificial intelligence.",
        
        "Python is a high-level, general-purpose programming language. Its design philosophy emphasizes code readability with the use of significant indentation. Python is dynamically typed and garbage-collected.",
        
        "Climate change includes both global warming driven by human-induced emissions of greenhouse gases and the resulting large-scale shifts in weather patterns."
    ]
    
    # Generate MCQs from each passage
    for i, passage in enumerate(passages):
        print(f"\nGenerating MCQ for passage {i+1}...")
        mcq = mcq_gen.generate_mcq_from_text(passage)
        if mcq:
            print_mcq(mcq)
        else:
            print(f"Failed to generate MCQ for passage {i+1}")
    
    # Generate multiple MCQs from a longer passage
    long_passage = """
    The history of computing hardware spans from prehistoric periods up to the development of the modern day computer. Before the development of the general-purpose computer, most calculations were done by humans. Devices have been used to help computation for thousands of years, mostly using one-to-one correspondence with fingers.
    
    The earliest known tool for use in computation is the Ishango bone, dating from 19,000 to 21,000 years ago. Many mechanical aids to calculation and measurement were constructed for astronomical and navigation use.
    
    The first coherent documentation of the principles that govern computers came from Ada Lovelace in the 1840s. Charles Babbage, an English mechanical engineer and polymath, originated the concept of a programmable computer.
    
    The development of digital electronic computers began in 1937 with the implementation of Boolean logic in electronic circuits by Claude Shannon. While working at Bell Labs, he showed that electronic relays and switches could realize the expressions of Boolean algebra.
    """
    
    print("\nGenerating multiple MCQs from a longer passage...")
    mcqs = mcq_gen.generate_multiple_mcqs(long_passage, num_questions=3)
    for i, mcq in enumerate(mcqs):
        print(f"\nMCQ {i+1}:")
        print_mcq(mcq)