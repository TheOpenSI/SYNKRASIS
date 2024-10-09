import re
import pandas as pd

with open("logs/mbpp_gpt_3_5.txt") as f:
    data = f.read()

question_pattern = r"#{10}\n\[FINAL\sPROMPT\]\sUser:\s(.*?)\n#{10}"
answer_pattern = r"(?<=\[GPT-3\.5-TURBO\]).*?(### Step-by-step reasoning.*?)(?=\[SUCCESS\])"

question = re.findall(question_pattern, data, re.DOTALL)
answer = re.findall(answer_pattern, data, re.DOTALL)
answer = [a[:-5] for a in answer]

pd.DataFrame({"Question": question, "Answer": answer}).to_csv("services/Finetune/mbpp_finetune_data.csv", index=False)