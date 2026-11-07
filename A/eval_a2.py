import sys
sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/A")
import pandas as pd
import dq_agent as DQ
import clean as CL
from ccn_tools import reference_calculator as RC, score as SC

raw = DQ.load()
fnd = DQ.detect(raw)
T = CL.canonical(raw, fnd)
for y in (2023, 2024):
    s = RC.summarise(RC.compute_inventory(T, y))
    key = pd.read_csv(DQ.PKG / f"tasks/dev/A2_dev_inventory_{y}.csv")
    r = SC.score_a2(s, key)
    m = key.merge(s, on="category", suffixes=("_true", "_pred"))
    m["err%"] = (100 * (m.tco2e_pred / m.tco2e_true - 1)).round(2)
    print(y, r["score"]); print(m[["category", "tco2e_true", "tco2e_pred", "err%"]].to_string(index=False))
