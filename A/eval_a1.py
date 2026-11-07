import json
import sys
sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/A")
import pandas as pd
import dq_agent as DQ
from ccn_tools import score as SC

raw = DQ.load()
fnd = DQ.detect(raw)
key = pd.read_csv(DQ.PKG / "tasks/dev/A1_dev_issue_labels_2023_2024.csv")
sub = DQ.submission(fnd, [2023, 2024])
res = SC.score_a1(sub, key)
print(json.dumps({k: v for k, v in res.items()}, indent=0))
k = key.groupby("record_key").issue_type.first()
fp = sub[~sub.record_key.isin(k.index)]
print("FP by type:\n", fp.groupby(["table", "issue_type"]).size())
fn = key[~key.record_key.isin(sub.record_key)]
print("FN:\n", fn[["record_key", "issue_type", "true_value", "observed_value"]].to_string())
wt = sub.merge(key[["record_key", "issue_type"]], on="record_key", suffixes=("", "_t"))
print("wrong type:\n", wt[wt.issue_type != wt.issue_type_t][["record_key", "issue_type", "issue_type_t"]])
if len(sys.argv) > 1:
    print(fp[["record_key", "issue_type", "explanation"]].to_string())
print(fnd[fnd.year == 2025].groupby(["table", "issue_type"]).size())
