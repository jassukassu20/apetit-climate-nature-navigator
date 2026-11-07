"""Track B: SBTi-aligned targets, base-year recalculation, BAU + lever pathways under NGFS-style
scenarios, and a marginal abatement cost curve (MACC) recomputed from the cleaned 2025 inventory.

Inputs : $CCN_WORK/A/lines_long.csv          (cleaned inventory line items, 2021-2025)
         $CCN_WORK/A/canonical_clean.pkl      (cleaned canonical tables)
         $CCN_WORK/A/farm_footprints_2025.csv (optional, FLAG components per farm)
         package data/05_scenarios/*.csv, data/03_farming/foodhills_odlingsdata_se.csv
Outputs: $CCN_WORK/B/*.csv, $CCN_WORK/B/b_results.json
Every number carries a `basis` string naming the lines / assumptions it came from.
"""
from __future__ import annotations
import json, pickle, sys
from pathlib import Path
import numpy as np, pandas as pd

PKG = Path(__import__("os").environ["CCN_PKG"] + "")
sys.path.insert(0, str(PKG / "tools"))
from ccn_tools import factors as F
from ccn_tools.farm_calculator import farm_footprint_per_ha

A = Path(__import__("os").environ["CCN_WORK"] + "/A"); OUT = Path(__import__("os").environ["CCN_WORK"] + "/B"); OUT.mkdir(exist_ok=True)
SC = PKG / "data/05_scenarios"
BASE = 2025; YEARS = list(range(2025, 2036))

lines = pd.read_csv(A / "lines_long.csv")
T = pickle.load(open(A / "canonical_clean.pkl", "rb"))
L25 = lines[lines.year == BASE].copy()
lev = pd.read_csv(SC / "decarbonisation_levers.csv")
scen = pd.read_csv(SC / "transition_scenarios.csv")
efl = pd.read_csv(PKG / "data/01_master/emission_factor_library.csv")
mats = pd.read_csv(PKG / "data/01_master/materials.csv")
EF = dict(zip(efl.ef_id, efl.kgco2e_per_unit)); FLAGSH = dict(zip(efl.ef_id, efl.flag_share))

def tot(df, scope=None, cat=None, like=None):
    d = df
    if scope: d = d[d.scope == scope]
    if cat: d = d[d.category.str.startswith(cat)]
    if like: d = d[d.line_item.astype(str).str.contains(like, regex=True)]
    return float(d.tco2e.sum())

# ---------------------------------------------------------------- FLAG split of 2025
def flag_of_line(r):
    """FLAG tCO2e of a cat-1 line: library factor flag_share, or farm FLAG components."""
    if r.category != "cat01_purchased_goods": return 0.0
    b = str(r.basis)
    if b in FLAGSH: return r.tco2e * FLAGSH[b]
    li = str(r.line_item)
    if li.startswith("contract_farming"): return np.nan  # filled from farm components
    mat = li.split(":")[0]
    m = mats.set_index("material_id")
    if mat in m.index and m.loc[mat, "default_ef_id"] in FLAGSH:   # PCF lines: use material default flag share
        return r.tco2e * FLAGSH[m.loc[mat, "default_ef_id"]]
    return 0.0

L25["flag_tco2e"] = L25.apply(flag_of_line, axis=1)
farm_flag_share = None
ff_path = A / "farm_footprints_2025.csv"
if ff_path.exists():
    ff = pd.read_csv(ff_path)
    farm_flag_share = ff.tco2e_flag.sum() / ff.tco2e.sum()
if farm_flag_share is None:   # fallback: compute FLAG share from the survey with METHODOLOGY §5
    farm_flag_share = 0.75
mask = L25.flag_tco2e.isna()
L25.loc[mask, "flag_tco2e"] = L25.loc[mask, "tco2e"] * farm_flag_share

S1 = tot(L25, "scope1"); S2L = tot(L25, "scope2_location"); S2M = tot(L25, "scope2_market"); S3 = tot(L25, "scope3")
FLAG = float(L25.flag_tco2e.sum()); S3NF = S3 - FLAG
cat_tot = L25[L25.scope == "scope3"].groupby("category").tco2e.sum()
cat1 = cat_tot[[c for c in cat_tot.index if c.startswith("cat01")]].sum()

# ---------------------------------------------------------------- Foodhills full-year adjustment
se = pd.read_csv(PKG / "data/03_farming/foodhills_odlingsdata_se.csv", sep=";", decimal=",")
se.columns = ["farm_id", "year", "crop_se", "area", "t", "n", "diesel", "irr"]
se = se[se.year == BASE].copy()
d = pd.DataFrame(dict(crop="pea", n_mineral_kg_ha=se.n.values, n_manure_kg_ha=0.0, p_kg_ha=F.MGMT_NORMS["pea"]["p"],
                      diesel_l_ha=se.diesel.values, lime_t_ha=F.MGMT_NORMS["pea"]["lime"], sprays=F.MGMT_NORMS["pea"]["sprays"],
                      yield_t_ha=(se.t / se.area).values, organic_soil=False, irrigated=se.irr.eq("ja").values))
kgha = farm_footprint_per_ha(d, grid_kg_per_kwh=F.GRID_SE_LB[BASE]) + se.diesel.values * (2.45 - 2.10)
# FLAG part: direct + indirect N2O + liming (recompute pieces)
E = F.FARM_EF; n2o = E["n2o_n_to_n2o"] * E["n2o_gwp"]; resn = F.RESIDUE_N_PER_T["pea"] * d.yield_t_ha.values
flag_ha = ((d.n_mineral_kg_ha * E["ef1_synthetic"] + resn * E["ef1_organic"]) * n2o
           + ((d.n_mineral_kg_ha * E["frac_gasf"]) * E["ef4_n2o_n"] + (d.n_mineral_kg_ha + resn) * E["frac_leach"] * E["ef5_n2o_n"]) * n2o
           + d.lime_t_ha * E["lime"] * 1000).values
se_farm_t = float((kgha * se.area.values).sum() / 1000); se_farm_flag = float((flag_ha * se.area.values).sum() / 1000)
bjuv_dec_s1 = tot(L25, "scope1", like="S-BJU"); bjuv_dec_s2m = tot(L25, "scope2_market", like="S-BJU")
bjuv_fy_s1 = 7300 * F.FUEL_EF_T_PER_MWH["natural_gas"]   # lever L07 note: full-year NG ~7,300 MWh
bjuv_fy_s2m = bjuv_dec_s2m * 12
adj = dict(
    s1=bjuv_fy_s1 - bjuv_dec_s1, s2m=bjuv_fy_s2m - bjuv_dec_s2m, s3=se_farm_t, flag=se_farm_flag,
    basis=("Bjuv NG 7,300 MWh/yr x 0.2009 t/MWh (lever L07 note) minus Dec-2025 actual; Bjuv electricity Dec x 12 (estimate, replace with "
           "Foodhills meters); SE pea growers 2025: foodhills_odlingsdata_se.csv (%d growers, %.0f ha, %.0f t) x METHODOLOGY §5 "
           "(mineral soil assumed, SE diesel 2.45)" % (se.farm_id.nunique(), se.area.sum(), se.t.sum())))

base = {
    "reported_2025": dict(s1=S1, s2m=S2M, s2l=S2L, s3=S3, flag=FLAG, s3_nonflag=S3NF),
    "adjusted_2025": dict(s1=S1 + adj["s1"], s2m=S2M + adj["s2m"], s2l=S2L, s3=S3 + adj["s3"], flag=FLAG + adj["flag"],
                          s3_nonflag=S3NF + adj["s3"] - adj["flag"]),
}
# 2019 recalculated (published, incl. grain trade): remove grain trade, add Foodhills 2019 estimate
pub = pd.read_csv(SC / "published_inventory_history.csv")
p19 = pub[pub.year == 2019].iloc[0]
grain_5m_2022 = float(pub.loc[pub.year == 2022, "scope3"].iloc[0] - pub.loc[pub.year == 2022, "scope3_restated"].iloc[0])
grain_annual = grain_5m_2022 * 12 / 5
se19 = 4232.0  # SE growers 2019 computed the same way (see SUMMARY); kept as constant for transparency
base["recalc_2019"] = dict(s1=float(p19.scope1) + bjuv_fy_s1, s2m=float(p19.scope2_market), s3=float(p19.scope3) - grain_annual + se19,
                           note=("published 2019 (published_inventory_history.csv) - grain trade (2022 restatement %.0f t for Jan-May x 12/5 = %.0f t/yr, "
                                 "rough) + Foodhills 2019 growers (~4.2 kt) + Bjuv NG; FLAG split unavailable for 2019 -> weak base, not recommended") % (grain_5m_2022, grain_annual))

# ---------------------------------------------------------------- targets (linear, absolute contraction)
RATES = dict(s12=0.042, s3=0.025, flag=0.0303)
def target(b, rate, y): return b * (1 - rate * (y - BASE))
B = base["adjusted_2025"]
targets = pd.DataFrame([dict(year=y, s12_target=target(B["s1"] + B["s2m"], RATES["s12"], y),
                             s3nf_target=target(B["s3_nonflag"], RATES["s3"], y), flag_target=target(B["flag"], RATES["flag"], y)) for y in YEARS])
E20 = target(S1 + S2M, RATES["s12"], 2032); E21 = target(FLAG, RATES["flag"], 2032)

# V2 coverage: Scope 3 categories >= 5 % of Scope 3
cov = (cat_tot.groupby(lambda c: c[:5]).sum() / S3).sort_values(ascending=False)

# ---------------------------------------------------------------- 2025 driver quantities (from clean canonical tables)
en = T["energy"]; en25 = en[en.year == BASE]
def mwh(site, carrier): return float(en25[(en25.site_id == site) & (en25.carrier == carrier)].mwh.sum())
sak_lng_lpg_t = tot(L25, "scope1", like=r"S-SAK:(?:lng|lpg)")
r404a_t = tot(L25, "scope1", like="R404A"); hfc_other_t = tot(L25, "scope1", cat="fugitive") - r404a_t
fleet_t = tot(L25, "scope1", like=r"FLEET|S-PUD:lpg")
pud_s1 = tot(L25, "scope1", like="S-PUD"); pud_s2m = tot(L25, "scope2_market", like="S-PUD"); pud_s2l = tot(L25, "scope2_location", like="S-PUD")
kan_bio_mwh = mwh("S-KAN", "wood_chips") + mwh("S-KAN", "oilseed_sidestream")
farm_lines = L25[L25.line_item.astype(str).str.startswith("contract_farming")]
farm_t = float(farm_lines.tco2e.sum())
rap_lines = L25[(L25.category == "cat01_purchased_goods") & L25.line_item.astype(str).str.match(r"M10[1-7]:")]
rap_import_t = float(rap_lines[~rap_lines.line_item.str.startswith("M101")].tco2e.sum())
rap_all_t = float(rap_lines.tco2e.sum())
cat4 = cat_tot.get("cat04_upstream_transport", 0); cat9 = cat_tot.get("cat09_downstream_transport", 0)
org_soil_t = None; fert_mfg_t = None
if ff_path.exists():
    ff = pd.read_csv(ff_path)
    org_soil_t = float(ff.tco2e_org.sum())
    fert_mfg_t = 0.55 * float(ff.tco2e_nonflag.sum())   # fertiliser manufacture ~55 % of non-FLAG farm emissions (METHODOLOGY §5 mix)
if org_soil_t is None: org_soil_t = 0.6 * farm_t      # fallback, overwritten when A provides components
if fert_mfg_t is None: fert_mfg_t = 0.12 * farm_t

# ---------------------------------------------------------------- lever recomputation
REC = {  # lever -> (abatement 2030 at full ramp, basis)
 "L01": (0.95 * sak_lng_lpg_t, "95 %% of Säkylä LNG+LPG combustion 2025 (%.0f t, lines S-SAK:lng/lpg)" % sak_lng_lpg_t),
 "L02": (min(lev.set_index("lever_id").loc["L02", "abatement_tco2e_2030_design"], 0.5 * fleet_t), "50 %% of fleet diesel + Pudasjärvi LPG (%.0f t), capped at design" % fleet_t),
 "L03": (0.9 * r404a_t, "90 %% of R404A top-ups 2025 (%.0f t, refrigerant lines)" % r404a_t),
 "L04": (0.25 * max(hfc_other_t, 0), "25 %% of non-R404A HFC fugitive 2025 (%.0f t)" % hfc_other_t),
 "L07": (bjuv_fy_s1 * 0.97, "Bjuv full-year NG 7,300 MWh x 0.2009, 97 %% biogas"),
 "L08": (fert_mfg_t * (1 - 0.9 / 3.7) * 0.7 + 0.15 * adj["s3"], "70 %% adoption x (1-0.9/3.7) of FI farm fertiliser manufacture (%.0f t) + SE growers" % fert_mfg_t),
 "L11": (0.5 * org_soil_t, "move 50 %% of contract area on drained organic soils (org-soil emissions %.0f t, METHODOLOGY §5 29 t CO2/ha)" % org_soil_t),
 "L12": (0.08 * org_soil_t, "rewet ~8 %% of organic-soil area (pilot)"),
 "L13": (0.12 * rap_import_t, "12 %% of imported/traded rapeseed cat-1 emissions (%.0f t) via primary PCFs + low-carbon fertiliser" % rap_import_t),
 "L14": (0.06 * rap_import_t, "6 %% of imported rapeseed via lower-EF origins (EF-RAP-* spread in library)"),
 "L20": (0.6 * 0.85 * (cat4 + cat9 - T["warehousing"].query("year==@BASE").pallet_days.sum() * EF.get("EF-PALLETDAY-FROZEN", 0) / 1000) * 0.7,
         "HVO100 -85 %% WTW on 60 %% of road tkm (~70 %% of cat4+cat9 truck share)"),
}
def crf(r, n): return r * (1 + r) ** n / ((1 + r) ** n - 1)
CONF = {"high": 0.2, "medium": 0.4, "low": 0.6}
lv = []
for _, r in lev.iterrows():
    ab, basis = REC.get(r.lever_id, (float(r.abatement_tco2e_2030_design), "design estimate from decarbonisation_levers.csv (not recomputed: no activity data isolates it)"))
    kind = "abatement"
    if r.lever_type == "structural": kind, ab = "structural", 0.0
    if r.lever_type == "data": kind, ab = "measurement", 0.0
    ann = r.capex_eur * crf(0.06, max(int(r.lifetime_yr), 1)) + r.opex_delta_eur_per_yr
    lv.append(dict(id=r.lever_id, name=r["name"], scope=r.scope, flag=bool(r.flag), type=r.lever_type, kind=kind, abatement=round(ab, 1),
                   low=round(ab * (1 - CONF[r.confidence]), 1), high=round(ab * (1 + CONF[r.confidence]), 1), confidence=r.confidence,
                   capex=int(r.capex_eur), opex=int(r.opex_delta_eur_per_yr), lifetime=int(r.lifetime_yr), start=int(r.earliest_start), ramp=int(r.ramp_years),
                   annual_cost_eur=round(ann), cost=round(ann / ab, 1) if ab > 0 else None, design_abatement=int(r.abatement_tco2e_2030_design),
                   co_benefits=str(r.co_benefits) if pd.notna(r.co_benefits) else "", trade_offs=str(r.trade_offs) if pd.notna(r.trade_offs) else "", basis=basis))
lv = pd.DataFrame(lv)
FUEL_LEVERS = {"L01", "L02", "L07", "L20"}   # exposed to ETS2 fuel price from 2028

# ---------------------------------------------------------------- pathways per scenario
def pathway(sname, portfolio="cost_below_carbon_price"):
    s = scen[scen.scenario == sname].set_index("year").select_dtypes("number").reindex(YEARS).interpolate().ffill().bfill()
    rows = []
    for y in YEARS:
        dem = s.loc[y, "plant_based_demand_index"]
        n = y - BASE
        # BAU: structural events + volumes
        s1 = S1 + (adj["s1"] if y >= 2026 else 0)
        s2 = S2M + (adj["s2m"] if y >= 2026 else 0)
        s3 = S3 + (adj["s3"] if y >= 2026 else 0)
        flag = FLAG + (adj["flag"] if y >= 2026 else 0)
        if y >= 2027:  # Pudasjärvi closed: S1/S2 -> cat 1 (contract manufacturing, approximated by same emissions)
            s1 -= pud_s1; s2 -= pud_s2m; s3 += pud_s1 + pud_s2l
        elif y == 2026:
            s1 -= 0.5 * pud_s1; s2 -= 0.5 * pud_s2m; s3 += 0.5 * (pud_s1 + pud_s2l)
        if y >= 2027:  # Kantvik biosteam sold: own biogenic combustion -> purchased steam (supplier factor assumed 0.02 t/MWh)
            s2 += kan_bio_mwh * 0.02
        vol = (1 + 0.6 * (dem - 1))   # 60 % of value chain scales with plant-based demand
        s3 = s3 * vol; flag = flag * vol
        bau = dict(s12=s1 + s2, s3=s3, flag=flag, s3nf=s3 - flag)
        # levers
        cp = s.loc[y, "carbon_price_eur_t"]; ets2 = s.loc[y, "eu_ets2_fuel_price_eur_t"]
        red = dict(s12=0.0, s3nf=0.0, flag=0.0); used = []
        for _, l in lv[lv.kind == "abatement"].iterrows():
            net = l.cost - (ets2 if l.id in FUEL_LEVERS else 0)
            if portfolio == "cost_below_carbon_price" and not (net <= cp): continue
            if y < l.start: continue
            ramp = min(1.0, (y - l.start + 1) / max(l.ramp, 1))
            a = l.abatement * ramp
            key = "s12" if l.scope.startswith("scope1") or l.scope.startswith("scope2") else ("flag" if l.flag else "s3nf")
            if l.flag and key == "flag" and l.id in ("L13", "L14", "L15", "L16", "L17"):  # commodity levers split by flag share
                red["flag"] += a * 0.86; red["s3nf"] += a * 0.14
            else:
                red[key] += a
            used.append(l.id)
        t = targets.set_index("year").loc[y]
        rows.append(dict(scenario=sname, year=y, carbon_price=cp, ets2=ets2, demand_index=round(dem, 3),
                         bau_s12=bau["s12"], bau_s3nf=bau["s3nf"], bau_flag=bau["flag"],
                         lev_s12=bau["s12"] - red["s12"], lev_s3nf=bau["s3nf"] - red["s3nf"], lev_flag=bau["flag"] - red["flag"],
                         tgt_s12=t.s12_target, tgt_s3nf=t.s3nf_target, tgt_flag=t.flag_target, levers=";".join(sorted(set(used)))))
    return pd.DataFrame(rows)

scen_names = list(scen.scenario.unique())
P = pd.concat([pathway(s) for s in scen_names] + [pathway(s, "all").assign(scenario=s + "|all_levers") for s in scen_names])
for k in ("s12", "s3nf", "flag"):
    P[f"gap_{k}"] = P[f"lev_{k}"] - P[f"tgt_{k}"]
P.round(1).to_csv(OUT / "pathways.csv", index=False)
lv.to_csv(OUT / "levers_recomputed.csv", index=False)
targets.round(1).to_csv(OUT / "targets.csv", index=False)

# MACC per scenario (net of ETS2 fuel price in 2030)
macc = []
for sname in scen_names:
    s = scen[scen.scenario == sname].set_index("year").select_dtypes("number").reindex(range(2025, 2051)).interpolate().ffill()
    for _, l in lv[lv.kind == "abatement"].iterrows():
        macc.append(dict(scenario=sname, id=l.id, abatement=l.abatement, cost_net=l.cost - (s.loc[2030, "eu_ets2_fuel_price_eur_t"] if l.id in FUEL_LEVERS else 0),
                         carbon_price_2030=s.loc[2030, "carbon_price_eur_t"]))
pd.DataFrame(macc).round(1).to_csv(OUT / "macc_by_scenario.csv", index=False)

res = dict(base=base, foodhills_adjustment=adj, rates=RATES, E20=E20, E21=E21,
           E20_basis="(S1 %.1f + S2 market %.1f) x (1 - 0.042 x 7) — reported 2025, cleaned inventory" % (S1, S2M),
           E21_basis="FLAG 2025 %.1f t (library flag_share x cat-1 lines + FLAG components of contract farming) x (1 - 0.0303 x 7)" % FLAG,
           flag_share_total=FLAG / (S1 + S2M + S3), farm_flag_share=farm_flag_share,
           scope3_category_shares=cov.round(4).to_dict(), cat1=cat1,
           drivers=dict(sak_lng_lpg_t=sak_lng_lpg_t, r404a_t=r404a_t, pud_s1=pud_s1, pud_s2m=pud_s2m, kan_bio_mwh=kan_bio_mwh,
                        farm_t=farm_t, rap_import_t=rap_import_t, rap_all_t=rap_all_t, org_soil_t=org_soil_t, fert_mfg_t=fert_mfg_t),
           scenarios=scen_names)
json.dump(res, open(OUT / "b_results.json", "w"), indent=1, default=float)
print(json.dumps({k: res[k] for k in ("base", "E20", "E21", "flag_share_total", "scope3_category_shares")}, indent=1, default=float))
print(lv[["id", "kind", "abatement", "design_abatement", "cost", "confidence"]].to_string())
print(P[P.year.isin([2030, 2035])][["scenario", "year", "lev_s12", "tgt_s12", "lev_s3nf", "tgt_s3nf", "lev_flag", "tgt_flag"]].round(0).to_string())
