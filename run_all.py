"""Reproduce everything from the unzipped Since AI package.

    python run_all.py /path/to/APETIT_CLIMATE_NATURE_NAVIGATOR_2026

Steps: A (DQ agent + inventory) -> D (nature) -> C (climate yields, ~3 min) -> B (pathways)
-> E (answers) -> app/index.html.  Outputs land in ./submissions and ./{A,B,C,D,E}.
Requires: pandas, numpy, pyarrow, scikit-learn, lightgbm.
"""
import os, sys, subprocess, pathlib
here = pathlib.Path(__file__).resolve().parent
pkg = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else os.environ.get("CCN_PKG", "")).resolve()
assert (pkg / "data").exists(), "pass the path of the unzipped APETIT_CLIMATE_NATURE_NAVIGATOR_2026 package"
env = dict(os.environ, CCN_PKG=str(pkg), CCN_WORK=str(here), PYTHONPATH=str(pkg / "tools"))
steps = [["A/run_all.py"], ["D/run_all.py"], ["C/run_all.py"], ["B/pathways.py"], ["E/rubric_answers.py", str(here / "E/rubric_answers.csv")], ["E/build_e.py"], ["app/build.py"]]
for s in steps:
    print(f"\n=== {s[0]} ===", flush=True)
    subprocess.run([sys.executable, str(here / s[0]), *s[1:]], check=True, env=env, cwd=str(here / pathlib.Path(s[0]).parent))
print("\nDone. Open app/index.html; CSVs for the auto-scored tasks are in submissions/.")
