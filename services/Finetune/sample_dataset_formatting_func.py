def formatting_func(df): # data type <class 'datasets.formatting.formatting.LazyBatch'>
    def create_text_row(question: str, answer: str) -> str:
        return f"""<s>### Instruction:\n{question}\n### Response: {answer}</s>"""
    
    
    questions = df["Question"]
    answers = df["Answer"]
    texts = []
    for question, answer in zip(questions, answers):
        text = create_text_row(question, answer)
        texts.append(text)
    return {"text" : texts}