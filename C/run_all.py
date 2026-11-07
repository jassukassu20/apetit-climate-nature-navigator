"""Reproduce Track C end to end: python -I $CCN_WORK/C/run_all.py  (~3 min on 2 CPUs)"""
import subprocess, sys
for s in ["features.py", "model.py", "predict.py", "c3.py", "mc.py"]:
    print(">>", s, flush=True)
    subprocess.run([sys.executable, "-I", __import__("os").environ["CCN_WORK"] + f"/C/{s}"], check=True)
