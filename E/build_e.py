import json, csv, pandas as pd
PKG=__import__("os").environ["CCN_PKG"] + ""
num=json.load(open(__import__("os").environ["CCN_WORK"] + "/A/e_numeric_inputs.json"))
rub=pd.read_csv(__import__("os").environ["CCN_WORK"] + "/E/rubric_answers.csv")
tmpl=pd.read_csv(f"{PKG}/tasks/templates/E_answers_submission.csv")
rows=[]
for q in tmpl.question_id:
    if q in num: rows.append(dict(question_id=q, answer=round(num[q]["value"],3), evidence=num[q]["evidence"]))
    else:
        r=rub[rub.question_id==q].iloc[0]; rows.append(dict(question_id=q, answer=r.answer, evidence=r.evidence))
pd.DataFrame(rows).to_csv(__import__("os").environ["CCN_WORK"] + "/submissions/E_answers_submission.csv", index=False, quoting=csv.QUOTE_MINIMAL)
print(len(rows))
