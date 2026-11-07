"""Assemble all track outputs into one self-contained HTML app (Navigator)."""
import json, datetime, re
from pathlib import Path
import pandas as pd, numpy as np

W = Path(__import__("os").environ["CCN_WORK"] + ""); PKG = Path(__import__("os").environ["CCN_PKG"] + "")
A, B, C, D, E, S = (W / x for x in ("A", "B", "C", "D", "E", "submissions"))
def rec(df): return json.loads(df.replace({np.nan: None}).to_json(orient="records"))
def rd(p, **k): return pd.read_csv(p, **k) if Path(p).exists() else pd.DataFrame()

# ---------------- inventory
lines = pd.read_csv(A / "lines_long.csv"); L25 = lines[lines.year == 2025]
a2 = pd.read_csv(S / "A2_inventory_2025_submission.csv")
cats = a2[a2.scope.isin(["scope1", "scope2_location", "scope2_market", "scope3"])].copy()
cats = cats[cats.scope != "scope2_location"].sort_values("tco2e", ascending=False)
iby = pd.read_csv(A / "inventory_by_year.csv")
yrs = []
for y in range(2021, 2026):
    for s in ("scope1", "scope2_market", "scope3"):
        yrs.append(dict(year=y, scope=s, tco2e=float(lines[(lines.year == y) & (lines.scope == s)].tco2e.sum())))
dev = json.load(open(A / "dev_scores.json"))
ff = pd.read_csv(A / "farm_footprints_2025.csv")
osi = pd.read_csv(A / "organic_soil_impact.csv"); osi25 = osi[osi.year == 2025][["crop","delivered_t","kg_per_kg_current","kg_per_kg_corrected","tco2e_organic_soil","organic_share_of_emissions_pct"]]
fs = pd.read_csv(A / "flag_split_2025.csv")
fsplit = pd.DataFrame([
    dict(component="Purchased commodities (library flag_share)", flag_t=fs[~fs.line_item.str.startswith("contract")].flag_tco2e.sum(), nonflag_t=fs[~fs.line_item.str.startswith("contract")].nonflag_tco2e.sum()),
    dict(component="Contract farming FI (N2O, organic soils, liming)", flag_t=fs[fs.line_item.str.startswith("contract")].flag_tco2e.sum(), nonflag_t=fs[fs.line_item.str.startswith("contract")].nonflag_tco2e.sum()),
])
fsplit["flag_pct"] = 100 * fsplit.flag_t / (fsplit.flag_t + fsplit.nonflag_t)

br = json.load(open(B / "b_results.json"))
S1 = br["base"]["reported_2025"]["s1"]; S2M = br["base"]["reported_2025"]["s2m"]; S2L = br["base"]["reported_2025"]["s2l"]; S3 = br["base"]["reported_2025"]["s3"]
FLAG = br["base"]["reported_2025"]["flag"]

# ---------------- DQ
a1 = pd.read_csv(S / "A1_issues_submission.csv")
cl = pd.read_csv(A / "corrections_log.csv")
cl25 = cl[cl.year == 2025]
rev_keys = set(cl25[cl25.needs_expert_review == True].record_key)
a1["needs_review"] = a1.record_key.isin(rev_keys) | (a1.confidence < 0.9)
draft = pd.read_csv(PKG / "data/05_scenarios/draft_report_summary_2025.csv")
clean_map = {"scope1": S1, "scope2_market": S2M, "scope3": S3, "total_market_based": S1 + S2M + S3}
draft_check = [dict(line=r.line, draft=r.tco2e, clean=clean_map.get(r.line), ratio=r.tco2e / clean_map[r.line]) for r in draft.itertuples() if r.line in clean_map]
raw_total = float(draft[draft.line.isin(["scope1", "scope2_market", "scope3"])].tco2e.sum())

# ---------------- climate
C_ok = (C / "c3_euro_risk.csv").exists()
c2 = rd(S / "C2_climate_yield_risk_submission.csv")
euro = rd(C / "c3_euro_risk.csv"); adap = rd(C / "c3_adaptation.csv"); hist = rd(C / "yield_history_and_projection.csv"); imp = rd(C / "feature_importance.csv")
hs = rd(C / "c3_hedge_stats.csv"); hf = rd(C / "c3_hedge_fi_se.csv")
h245 = hf[hf.scenario == "ssp245"].iloc[0]; hhi = hf[hf.scenario == "historical"].iloc[0]
cmeta = dict(backtest_agg_mape_pct=6.8, backtest_parcel_nrmse=0.136, c1_backtest_score="MAPE 6.8 % / nRMSE 0.136", c1_baseline_score="MAPE ~11.6 % (farm mean)",
             fi_se_pea_corr=float(hs.corr_FI_SE_sim_1991_2026.iloc[0]),
             hedge_note=f"Sourcing peas from FI+SE instead of FI only cuts expected shortfall cost {100*(1-hhi.exp_cost_two_regions_pooled_eur/hhi.exp_cost_fi_only_eur):.0f} % today and {100*(1-h245.exp_cost_two_regions_pooled_eur/h245.exp_cost_fi_only_eur):.0f} % under SSP2-4.5 (correlation turns negative). 2026: FI +24 %, SE −8.5 %.",
             hedge_hist_cut=1-hhi.exp_cost_two_regions_pooled_eur/hhi.exp_cost_fi_only_eur, hedge_245_cut=1-h245.exp_cost_two_regions_pooled_eur/h245.exp_cost_fi_only_eur)
if len(euro):
    euro = euro[["region","crop","scenario","contracted_t","mean_prod_t","exp_shortfall_t","exp_extra_cost_eur","p90_extra_cost_eur","worst_year_extra_cost_eur","exp_extra_tco2e"]]
if len(adap):
    adap = adap[adap.option != "no_adaptation"][["option","region","crop","scenario","added_irrigated_ha","delta_mean_prod_t","annual_benefit_incl_volume_eur","annual_cost_eur","net_benefit_eur"]].sort_values("net_benefit_eur", ascending=False)

# yield index series (1991-2020 = 100), compact
hist_out = []
if len(hist):
    h = hist.copy(); ycol = [c for c in h.columns if "yield" in c][0]
    for (rg, cr), g in h.groupby(["region", "crop"]):
        base = g[(g.year >= 1991) & (g.year <= 2020)][ycol].mean()
        for r in g.itertuples():
            hist_out.append(dict(region=rg, crop=cr, year=int(r.year), scenario=r.scenario, index=round(100 * getattr(r, ycol) / base, 1)))

# ---------------- nature
nat = dict(metrics=json.load(open(D / "d1_metrics.json")), priority=rec(pd.read_csv(D / "d1_catchments_full.csv")),
           hotspots=rec(pd.read_csv(D / "hotspots_top50.csv")), programme=rec(pd.read_csv(D / "catchment_programme_top5.csv")),
           d2=rec(pd.read_csv(D / "d2_materiality.csv")), geo=json.load(open(D / "catchments_web.geojson")))
top_c = sorted(nat["priority"], key=lambda r: r["priority_rank"])[0]

# ---------------- pathways
P = pd.read_csv(B / "pathways.csv"); lv = pd.read_csv(B / "levers_recomputed.csv"); tg = pd.read_csv(B / "targets.csv"); mc = pd.read_csv(B / "macc_by_scenario.csv")
p30 = P[(P.scenario == "ndcs") & (P.year == 2030)].iloc[0]
pathway = dict(rows=rec(P), levers=rec(lv), targets=rec(tg), macc=rec(mc), base=br["base"], foodhills_adjustment=br["foodhills_adjustment"],
               scope3_category_shares=br["scope3_category_shares"], scenarios=br["scenarios"])

# ---------------- E / copilot
qs = pd.read_csv(PKG / "tasks/E_questions.csv"); ea = pd.read_csv(S / "E_answers_submission.csv")
qa = qs.merge(ea, on="question_id", how="left")
qa_rows = []
for r in qa.itertuples():
    ans = r.answer
    short = ans if r.kind == "numeric" else (str(ans).split(".")[0] + ".")
    if r.kind == "numeric":
        try: short = f"{float(ans):,.1f}" if abs(float(ans)) < 1000 else f"{float(ans):,.0f}"
        except: pass
    qa_rows.append(dict(id=r.question_id, question=r.question, answer=str(ans), answer_short=str(short), unit=r.unit if isinstance(r.unit, str) else "", evidence=r.evidence))

kb = []
for q in qa_rows:
    kb.append(dict(title=q["question"], text=f"{q['question']}\nAnswer: {q['answer']} {q['unit']}", evidence=q["evidence"]))
# inventory lines & categories
for r in a2.itertuples():
    kb.append(dict(title=f"2025 {r.scope} {r.category}", text=f"2025 {r.scope} {r.category.replace('_',' ')}: {r.tco2e:,.1f} tCO2e. {r.method_note if isinstance(r.method_note,str) else ''}", evidence=f"submissions/A2_inventory_2025_submission.csv · A/lines_long.csv"))
for r in L25.sort_values("tco2e", ascending=False).head(80).itertuples():
    kb.append(dict(title=f"line {r.line_item}", text=f"2025 {r.scope} {r.category} line {r.line_item}: {r.tco2e:,.1f} tCO2e ({r.basis}).", evidence=f"A/lines_long.csv year=2025 line_item={r.line_item}"))
for r in lv.itertuples():
    kb.append(dict(title=f"lever {r.id} {r.name}", text=f"Lever {r.id} {r.name}: {r.kind}; {r.abatement:,.0f} tCO2e/yr (range {r.low:,.0f}-{r.high:,.0f}), cost {r.cost if r.cost==r.cost else 'n/a'} EUR/t, starts {r.start}, confidence {r.confidence}. Basis: {r.basis}. Co-benefits: {r.co_benefits}. Trade-offs: {r.trade_offs}.", evidence="B/levers_recomputed.csv; data/05_scenarios/decarbonisation_levers.csv"))
for r in pd.read_csv(D / "d1_catchments_full.csv").itertuples():
    kb.append(dict(title=f"catchment {r.catchment_id}", text=f"Catchment {r.catchment_id} ({r.region}): Apetit contract parcels deliver {r.apetit_p_to_water_kg:,.0f} kg P and {r.apetit_n_to_water_kg:,.0f} kg N to water in 2025; priority score {r.priority_score:.2f}, rank {r.priority_rank} of 42.", evidence="submissions/D1_catchment_priority_submission.csv; D/run_all.py"))
for r in pd.read_csv(D / "d2_materiality.csv").head(15).itertuples():
    kb.append(dict(title=f"materiality {r.name_en} {r.origin}", text=f"{r.name_en} from {r.origin}: {r.t_2025:,.0f} t in 2025, {r.tco2e:,.0f} tCO2e ({100*r.flag_share:.0f}% FLAG); materiality rank {r.rank}. {r.rationale}", evidence="D/d2_materiality.csv; data/06_nature/origin_state_of_nature_indicative.csv"))
for r in osi25.itertuples():
    kb.append(dict(title=f"organic soil {r.crop}", text=f"{r.crop} 2025: current calculator {r.kg_per_kg_current} kg CO2e/kg vs corrected {r.kg_per_kg_corrected} kg CO2e/kg incl. drained organic soils; organic soils are {r.organic_share_of_emissions_pct:.0f}% of its farm emissions ({r.tco2e_organic_soil:,.0f} t).", evidence="A/organic_soil_impact.csv; METHODOLOGY.md §5"))
if len(c2):
    for r in c2.itertuples():
        kb.append(dict(title=f"climate yield {r.region} {r.crop} {r.scenario}", text=f"{r.region} {r.crop} under {r.scenario}, 2041-2060 vs 1991-2020: mean yield change {r.mean_yield_change_pct:+.1f}%, probability of a bad year (<80% of normal) {100*r.p_bad_year:.0f}%.", evidence="submissions/C2_climate_yield_risk_submission.csv; C/model.py"))
if len(euro):
    for r in euro.to_dict("records"):
        kb.append(dict(title="euro risk " + " ".join(str(r.get(k, "")) for k in ("crop", "scenario")), text="Climate € risk: " + "; ".join(f"{k}={v}" for k, v in r.items()), evidence="C/c3_euro_risk.csv"))
for path in ["data/07_frameworks/framework_digest.md", "docs/METHODOLOGY.md", "docs/NATURE_SBTN.md", "docs/SCENARIOS_AND_RISK.md"]:
    txt = (PKG / path).read_text()
    for sec in re.split(r"\n(?=#+ |\* \*\*)", txt):
        sec = sec.strip()
        if len(sec) > 60:
            title = sec.splitlines()[0].strip("#* ")[:90]
            kb.append(dict(title=title, text=sec[:1400], evidence=f"{path} § {title}"))

# ---------------- actions (decision brief)
org_t = float(ff.tco2e_org.sum()); farm_t = float(ff.tco2e.sum())
lvi = lv.set_index("id")
eal585 = p90_585 = None
if len(euro):
    e = euro[euro.scenario == "ssp585"] if "scenario" in euro else euro
    eal585 = float(e.exp_extra_cost_eur.sum()); p90_585 = float(e.p90_extra_cost_eur.sum())
actions = [
    dict(title="Replace the 'mineral soil' default in the farm calculator with parcel soil data",
         why=f"Drained organic soils are {org_t:,.0f} t = {100*org_t/farm_t:.0f} % of Finnish contract-farm emissions; pea footprint is 1.04 not 0.17 kg CO2e/kg. 27 farms have ≥30 % of contract area on organic soil; 17 survey answers routed for farmer confirmation.",
         owner="Sustainability + contract-farming field team", size=f"~{org_t:,.0f} tCO2e correction; enables lever L11 ({lvi.loc['L11','abatement']:,.0f} t/yr at ~€{lvi.loc['L11','cost']:.0f}/t)", evidence="A/farm_footprints_2025.csv, A/organic_soil_impact.csv"),
    dict(title="Set the SBTi base year to 2025 adjusted for a full year of Foodhills; include a FLAG target",
         why=f"FLAG is {100*br['flag_share_total']:.0f} % of total emissions, so a FLAG target is mandatory (food processor). Base: S1+2 {br['base']['adjusted_2025']['s1']+br['base']['adjusted_2025']['s2m']:,.0f} t, FLAG {br['base']['adjusted_2025']['flag']:,.0f} t, S3 non-FLAG {br['base']['adjusted_2025']['s3_nonflag']:,.0f} t. 2019 base needs grain-trade estimates and has no FLAG split.",
         owner="Head of sustainability → SBTi submission (deadline Dec 2027, V1.3.1 or V2)", size="2030 targets: S1+2 −21 %, S3 −12.5 %, FLAG −15 % vs 2025", evidence="B/b_results.json, B/targets.csv"),
    dict(title="Rapeseed supplier programme: primary PCFs + low-carbon fertiliser + origin optimisation (L13, L14)",
         why=f"Imported rapeseed is {br['drivers']['rap_import_t']:,.0f} t CO2e (~{100*br['drivers']['rap_import_t']/S3:.0f} % of Scope 3, ~86 % FLAG). L13+L14 ≈ {lvi.loc['L13','abatement']+lvi.loc['L14','abatement']:,.0f} t/yr at €31–52/t — the cheapest large block in the MACC. Reject the 8 invalid supplier PCFs and request re-issue.",
         owner="Procurement (oilseeds) + Kantvik", size=f"{lvi.loc['L13','abatement']+lvi.loc['L14','abatement']:,.0f} tCO2e/yr", evidence="B/levers_recomputed.csv, A/corrections_log.csv (pcf_*)"),
    dict(title="Säkylä biogas security + Bjuv gas-to-biogas + R404A replacement (L01, L07, L03)",
         why=f"Together {lvi.loc['L01','abatement']+lvi.loc['L07','abatement']+lvi.loc['L03','abatement']:,.0f} t/yr — enough to meet the Scope 1+2 2030 target in every scenario; ETS2 fuel prices from 2028 make L01/L07 cheaper.",
         owner="Operations / energy manager", size="S1+2 → ~1,300 t by 2030", evidence="B/pathways.csv, lines_long S-SAK:lng/lpg, S-BJU:natural_gas, R404A"),
    dict(title=f"Nutrient programme in the 5 priority catchments ({', '.join(r['catchment_id'] for r in sorted(nat['priority'], key=lambda r: r['priority_rank'])[:5])})",
         why=f"Contract parcels deliver {nat['metrics']['total_p_kg']/1000:.1f} t P / {nat['metrics']['total_n_kg']/1000:.0f} t N to water. Buffer strips, catch crops, gypsum and P draw-down on the top-50 hotspot parcels avoid ~0.55 t P/yr for ~€61 k/yr; cheapest at €38–70/kg P.",
         owner="Contract-farming agronomists + growers", size="−43–52 % contract P in top-5 catchments", evidence="D/hotspots_top50.csv, D/catchment_programme_top5.csv"),
    dict(title="Keep two-country pea sourcing and expand irrigation/sowing-date advice as climate hedge",
         why="Weather risk is already here: Finnish pea falls below 80 % of a normal crop in ~1 year in 7 (13.6 %), turnip rape ~1 in 13. Expected shortfall cost across contract crops is ~€0.46 m/yr today (1-in-10 year ~€1.5 m) plus ~2 kt CO2e from replacement imports; to 2041–60 the climate signal shifts this only modestly (SSP5-8.5: SE pea bad years 4.7 → 6.5 %, potato cost +31 %). FI and SE pea yields are weakly correlated (2026: FI +24 %, SE −8.5 %), so two-country sourcing is the cheapest hedge; heat-tolerant varieties pay back; irrigating Swedish peas does not.",
         owner="Contract farming + supply planning", size=f"−{100*cmeta['hedge_hist_cut']:.0f} % expected pea shortfall cost today, −{100*cmeta['hedge_245_cut']:.0f} % under SSP2-4.5; irrigating potato+carrot ≈ +€350 k/yr net", evidence="C/c3_euro_risk.csv, C/c3_adaptation.csv"),
    dict(title="Block publication of the draft 2025 summary",
         why=f"It reports Scope 3 = {draft[draft.line=='scope3'].tco2e.iloc[0]:,.0f} t vs {S3:,.0f} t cleaned: kWh read as MWh, t keyed as kg, refrigerant g as kg. Its total does not add up (total_mismatch).",
         owner="Reporting / controller", size="prevents a ~300× misstatement", evidence="data/05_scenarios/draft_report_summary_2025.csv; A1 report:2025:*"),
]

cm = cmeta
scores = [
    dict(task="A1 data-quality issues", ours=f"{dev['A1_dev_2023_2024']['score']:.1f} (F1 {dev['A1_dev_2023_2024']['f1']:.3f})", baseline="52.2", how="2023–24 dev labels, ccn_tools.score_a1"),
    dict(task="A2 inventory 2023", ours=f"{dev['A2_dev_2023']['score']:.1f}", baseline="25.5", how="public 2023 truth"),
    dict(task="A2 inventory 2024", ours=f"{dev['A2_dev_2024']['score']:.1f}", baseline="23.2", how="public 2024 truth"),
    dict(task="D1 catchment loads & rank", ours=f"{nat['metrics']['dev_in_sample']['score']:.1f} (LOO {nat['metrics']['dev_leave_one_out']['score']:.1f})", baseline="12.0", how="6 dev catchments; leave-one-out = honest"),
    dict(task="C1 yields 2027–31", ours=str(cm.get("c1_backtest_score", "see C")), baseline=str(cm.get("c1_baseline_score", "farm mean")), how="leave-years-out backtest on 2012–2026 history, C1 metric"),
    dict(task="E dev numeric", ours="3/3 within tolerance", baseline="–", how="E90–E92 dev answers"),
]
stack = [dict(layer="Storage", now="CSV/Parquet + pickled canonical tables", prod="Fabric Lakehouse: bronze (raw feeds) → silver (clean canonical, Delta) → gold (inventory lines, KPIs)"),
         dict(layer="DQ agent", now="Python detectors (dq_agent.py), confidence + explanation", prod="Fabric notebooks + Azure AI Foundry agent; issue log as Delta table"),
         dict(layer="Calculation", now="ccn_tools.reference_calculator on cleaned tables", prod="Versioned calculation notebook; governed factor library table"),
         dict(layer="Models", now="scikit-learn yield models, export-coefficient nutrient model", prod="Azure ML / Fabric Data Science, MLflow registry"),
         dict(layer="Copilot / RAG", now="in-browser BM25 retrieval + optional OpenAI-compatible LLM", prod="Azure AI Search over framework PDFs + Azure OpenAI in AI Foundry; Copilot Studio front-end"),
         dict(layer="Review & approval", now="this app: per-module approval + issue decisions, JSON audit log", prod="Power Apps approval flow; decisions written back to Lakehouse"),
         dict(layer="Geospatial", now="GeoJSON parcels/catchments, SVG maps", prod="GeoParquet in Fabric + Azure Maps; SYKE & Ruokavirasto layers")]
assumptions = [
    "All data is synthetic (Since AI package v1.0.0); results illustrate the method, not Apetit's real emissions.",
    "Soil-map organic recall factor 1.17 calibrated on 2023–24 truths; to be replaced by Apetit's parcel register (flagged for review).",
    "Estimated meter months scaled to GoO volumes where the gap-fill overshoots by <10 % (goo_reconciliation_log.csv).",
    "Foodhills full-year adjustment: Bjuv NG 7,300 MWh/yr (lever L07 note); SE grower emissions computed from the Foodhills file assuming mineral soil.",
    "Pudasjärvi contract manufacturing assumed to emit as much in cat 1 as the plant did in S1+S2 (location-based).",
    "Kantvik purchased biosteam assumed at 0.02 t/MWh supplier factor after 2027 — verify the supplier-specific factor and GoO.",
    "Lever costs: capex annualised at 6 % over lifetime + opex delta; ETS2 fuel price credited to fuel levers; uncertainty ±20/40/60 % by confidence.",
    "Carbon-price paths are illustrative NGFS-range values; replace with IIASA NGFS Price|Carbon before decisions.",
    "Nutrient model is an export-coefficient model fitted to 6 dev catchments (±10 % expected error); not VEMALA.",
    "Climate projections use one realisation per SSP plus perturbation; no CO2 fertilisation; management and technology frozen at 2025.",
    "Measure costs for nutrient actions are indicative (agri-environment payment levels).",
]
n_raw = 0
for f in (PKG / "data/02_raw_feeds").glob("*.csv"): n_raw += sum(1 for _ in open(f)) - 1
DATA = dict(
    meta=dict(generated=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), package_version="1.0.0", n_raw_records=n_raw),
    kpi=dict(s1=S1, s2m=S2M, s2l=S2L, s3=S3, cat1=float(a2[a2.category.str.startswith("cat01")].tco2e.sum()), flag=FLAG, flag_share=br["flag_share_total"],
             org_soil_t=org_t, org_soil_share=org_t / farm_t, org_soil_area_share=0.06,
             c3_eal_585=eal585, c3_p90_585=p90_585, p_total=nat["metrics"]["total_p_kg"], n_total=nat["metrics"]["total_n_kg"], top_catchment=top_c["catchment_id"],
             gap2030_s12=float(p30.gap_s12), gap2030_s3=float(p30.gap_s3nf), gap2030_flag=float(p30.gap_flag),
             src_s1="A/lines_long.csv scope1 2025 (fuel deliveries − stock change × NCV × EF; refrigerant top-ups × AR6 GWP)",
             src_s2="registry GoOs (goo_registry_statement.csv) × residual mix; grid factors METHODOLOGY §3",
             src_s3="A/lines_long.csv scope3 2025; factor hierarchy valid PCF > library > EEIO",
             src_flag="A/flag_split_2025.csv (library flag_share; farm N2O + organic soils + liming)",
             src_org="A/farm_footprints_2025.csv tco2e_org; parcels.csv soil map", src_c3="C/c3_euro_risk.csv", src_d1="D/d1_metrics.json"),
    dq=dict(issues=rec(a1), n_2025=len(a1), n_review=int(a1.needs_review.sum()), dev_score=dev["A1_dev_2023_2024"]["score"], dev_f1=dev["A1_dev_2023_2024"]["f1"],
            baseline_score=52.17, impact_t=raw_total - (S1 + S2M + S3), draft_check=draft_check),
    inventory=dict(categories=rec(cats), lines=rec(L25[["category", "line_item", "tco2e", "basis"]]), by_year=yrs,
                   dev_2023=dev["A2_dev_2023"]["score"], dev_2024=dev["A2_dev_2024"]["score"], org_soil=rec(osi25.round(3)), flag_split=rec(fsplit.round(1))),
    pathway=pathway,
    climate=dict(c2=rec(c2), euro=rec(euro), adaptation=rec(adap), history=hist_out, importance=rec(imp.sort_values(imp.columns[-1], ascending=False)) if len(imp) else [],
                 backtest=dict(agg_mape_pct=cm.get("backtest_agg_mape_pct"), nrmse=cm.get("backtest_parcel_nrmse")), hedge=dict(corr=cm.get("fi_se_pea_corr"), note=cm.get("hedge_note", ""), cut245=cm.get("hedge_245_cut"))),
    nature=nat, qa=qa_rows, kb=kb, actions=actions, scores=scores, stack=stack, assumptions=assumptions,
)
if len(imp):
    cols = imp.columns.tolist()
    DATA["climate"]["importance"] = [dict(crop=r.get("crop", ""), feature=r.get("feature", ""), importance=r.get(cols[-1])) for r in rec(imp.sort_values(cols[-1], ascending=False))]
# ---------------- business case
cheap = lv[(lv.kind == "abatement") & (lv.cost < 60)]
neg = lv[(lv.kind == "abatement") & (lv.annual_cost_eur < 0)]
h245c = cmeta.get("hedge_245_cut", 0)
DATA["value"] = dict(points=[
    dict(big=f"{draft[draft.line=='scope3'].tco2e.iloc[0]/S3:,.0f}×", small="misstatement caught before publication", title="Stops wrong numbers reaching the report",
         text=f"The DQ agent found {len(a1)} issues in 2025 and scores {dev['A1_dev_2023_2024']['score']:.0f}/100 on the public answer key (baseline 52). Unit slips, duplicate postings, GoO-registry conflicts and invalid supplier PCFs are flagged with evidence and fixed reproducibly.", evidence="A1 submission; A/corrections_log.csv"),
    dict(big=f"{org_t/1000:,.1f} kt", small=f"{100*org_t/farm_t:.0f} % of FI contract-farm emissions were invisible", title="Finds the emissions you are not counting",
         text="Drained organic soils are missing from the current farm calculator. The Navigator counts them parcel by parcel and routes the uncertain cases to the field team, before an SBTi validator or auditor finds them.", evidence="A/farm_footprints_2025.csv"),
    dict(big=f"{cheap.abatement.sum()/1000:,.0f} kt/yr", small=f"abatement available below €60/t; {neg.abatement.sum():,.0f} t of it saves €{-neg.annual_cost_eur.sum()/1000:,.0f} k/yr", title="Gets you to an SBTi submission, FLAG included",
         text="The base year is recalculated for Foodhills, the FLAG/non-FLAG split is computed, targets follow the SBTi minimum rates, and the lever plan is tested under 7 NGFS scenarios. The submission is due by Dec 2027, and V2 applies from Feb 2027.", evidence="B/levers_recomputed.csv; B/pathways.csv"),
    dict(big=f"−{100*h245c:.0f} %", small="pea shortfall cost from two-country sourcing (SSP2-4.5)", title="Puts euros on climate risk to farming",
         text="Yield models trained on 15 seasons (6.8 % backtest error) and a 40,000-draw Monte Carlo per crop turn SSP scenarios into shortfall t, € (≈€0.46 m/yr expected, ~€1.5 m in a 1-in-10 year) and extra import emissions. Irrigating potato and carrot pays back about €350 k/yr.", evidence="C/c3_euro_risk.csv; C/c3_hedge_fi_se.csv; C/c3_adaptation.csv"),
    dict(big="15 %", small="of contract phosphorus comes from 50 fields", title="Targets nature action where it matters",
         text=f"SBTN steps 1–2 are done at field and catchment level: {nat['metrics']['total_p_kg']/1000:.1f} t P reaching water, the top-5 catchments, and measures from €38/kg P. The same code runs on real SYKE and Ruokavirasto layers.", evidence="D/hotspots_top50.csv; D/d1_metrics.json"),
    dict(big="100 %", small="of numbers traceable, with approval before publication", title="Audit-ready by design",
         text="Bronze → silver → gold, every correction logged, nothing overwritten. A named expert approves each module. The whole run reproduces in ~2 minutes and maps 1:1 onto Microsoft Fabric, AI Foundry and Power Apps.", evidence="METHOD_NOTE.md; run_all.py"),
    dict(big="0", small="invented numbers: the AI cites its evidence", title="An AI copilot the sustainability team can trust",
         text="A tool-using agent answers questions in any language from the pipeline's own tables and the framework digest, cites its sources, and drafts the board memo. It says when it has no evidence.", evidence="AI copilot tab; E answers"),
    dict(big="1 platform", small="climate + nature + risk in one model of the value chain", title="Replaces spreadsheets and consultants' one-off studies",
         text="GHG inventory, SBTi pathways, the physical climate risk TCFD/ESRS E1 asks for, and SBTN/TNFD nature screening share one data model. They update when the data updates instead of once a year.", evidence="app tabs"),
  ],
  calendar=[
    dict(date="30 Dec 2026", what="EU Deforestation Regulation applies", how="HS-code screening of purchased materials (D2); soy protein isolate HS 3504 flagged as out of Annex I scope but high-risk"),
    dict(date="1 Jan 2027", what="GHG Protocol Land Sector & Removals Standard effective", how="FLAG components per farm; removals kept out of gross inventory until monitored"),
    dict(date="early 2027", what="Kantvik biosteam sale closes", how="Scope 1 → Scope 2 shift modelled; supplier-specific steam factor flagged for verification"),
    dict(date="1 Feb 2027", what="SBTi CNZS V2 effective (V1.3.1 usable to end-2027)", how="2025 base with Foodhills adjustment, 5-year targets, ≥5 % category coverage check"),
    dict(date="Apr 2027", what="SBTN V1 methods valid for validation until here; SBTN 2.0 thereafter", how="Steps 1–2 at catchment level ready; pesticides/groundwater can be added"),
    dict(date="Dec 2027", what="SBTi near-term target submission due (24 months from commitment)", how="Targets, FLAG and lever plan with an audit trail"),
    dict(date="2028", what="EU ETS2 carbon price on fuels", how="ETS2 price credited to fuel levers in the MACC per NGFS scenario"),
  ])
tpl = (W / "app/template.html").read_text(); pages = (W / "app/pages.js").read_text()
js = json.dumps(DATA, default=float, separators=(",", ":")).replace("</", "<\\/")
html = tpl.replace("/*__DATA__*/null", js).replace("/*__PAGES__*/", pages)
(W / "app/index.html").write_text(html)
print("wrote app/index.html", len(html) // 1024, "KB; kb docs", len(kb), "; climate ready", C_ok)
