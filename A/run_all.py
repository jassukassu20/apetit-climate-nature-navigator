"""Track A end to end: raw package -> DQ findings -> corrections -> canonical clean tables ->
reference calculator -> submissions + audit trail.     Run:  python $CCN_WORK/A/run_all.py"""
from __future__ import annotations

import json
import pickle
import sys
from pathlib import Path

sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/A")
import numpy as np
import pandas as pd

import clean as CL
import dq_agent as DQ
from ccn_tools import factors as F
from ccn_tools import reference_calculator as RC
from ccn_tools import score as SC
from ccn_tools.farm_calculator import farm_footprint_per_ha

OUT = Path(__import__("os").environ["CCN_WORK"] + "/A")
SUB = Path(__import__("os").environ["CCN_WORK"] + "/submissions")
SUB.mkdir(parents=True, exist_ok=True)
YEARS = [2021, 2022, 2023, 2024, 2025]

raw = DQ.load()
fnd = DQ.detect(raw)
T = CL.canonical(raw, fnd)

# ------------------------------------------------------------------ dev scores (self-check)
dev = {}
key1 = pd.read_csv(DQ.PKG / "tasks/dev/A1_dev_issue_labels_2023_2024.csv")
dev["A1_dev_2023_2024"] = SC.score_a1(DQ.submission(fnd, [2023, 2024]), key1)
for y in (2023, 2024):
    dev[f"A2_dev_{y}"] = SC.score_a2(RC.summarise(RC.compute_inventory(T, y)), pd.read_csv(DQ.PKG / f"tasks/dev/A2_dev_inventory_{y}.csv"))

# ------------------------------------------------------------------ A1 submission (2025 records)
s25 = DQ.submission(fnd, [2025])
s25[["table", "record_key", "issue_type", "confidence", "explanation"]].to_csv(SUB / "A1_issues_submission.csv", index=False)

# ------------------------------------------------------------------ corrections log (all years)
log = fnd.copy()
log["reason"] = log.explanation
log[["record_key", "table", "year", "issue_type", "field", "original_value", "corrected_value", "reason", "confidence",
     "needs_expert_review"]].to_csv(OUT / "corrections_log.csv", index=False)
if len(T["_recon"]):
    T["_recon"].to_csv(OUT / "goo_reconciliation_log.csv", index=False)

# ------------------------------------------------------------------ inventories
long, summ = [], []
for y in YEARS:
    inv = RC.compute_inventory(T, y)
    long.append(inv.assign(biogenic_memo_t=inv.attrs["biogenic_co2_t"]))
    summ.append(RC.summarise(inv).assign(year=y))
lines_long = pd.concat(long, ignore_index=True)
lines_long[["year", "scope", "category", "line_item", "tco2e", "basis"]].to_csv(OUT / "lines_long.csv", index=False)
pd.DataFrame([dict(year=y, biogenic_co2_t=l.biogenic_memo_t.iloc[0]) for y, l in zip(YEARS, long)]).to_csv(OUT / "biogenic_memo_by_year.csv", index=False)
by_year = pd.concat(summ, ignore_index=True).pivot_table(index=["scope", "category"], columns="year", values="tco2e").round(2)
by_year.to_csv(OUT / "inventory_by_year.csv")

inv25 = RC.compute_inventory(T, 2025)
s = RC.summarise(inv25)
tmpl = pd.read_csv(DQ.PKG / "tasks/templates/A2_inventory_2025_submission.csv")
NOTES = {
    "fugitive_refrigerants": "kg top-up x AR6 GWP100; gas-code and g/kg fixes applied",
    "stationary_and_mobile_combustion": "fuel MWh (NCV; deliveries - stock change) x fossil EF; m3/l fixes",
    "purchased_electricity": "meter MWh (kWh/spike/gap corrected) x grid avg (LB) | uncovered MWh x residual mix (MB), registry GoOs",
    "purchased_heat_steam": "MWh x national heat avg (LB) / supplier-specific EF (MB)",
    "cat01_purchased_goods_services": "ERP kg x valid PACT PCF or library EF; contract farms: survey footprint incl. organic soils (soil map, calibrated); spend x EEIO",
    "cat02_capital_goods": "capex spend x EEIO (SEK line reconciled to capex register)",
    "cat03_fuel_energy": "fuel MWh x WTT + electricity MWh x upstream/T&D + heat upstream",
    "cat04_upstream_transport": "inbound tkm x GLEC WTW; missing sea legs imputed",
    "cat05_waste": "waste t x treatment EF (t/kg fixes) + wastewater m3",
    "cat06_business_travel": "pkm x EF + hotel nights; re-imported bookings removed",
    "cat07_employee_commuting": "2025 survey mean (modes normalised, m->km fixed) x headcount",
    "cat09_downstream_transport": "outbound tkm x EF + frozen pallet-days",
    "cat11_use_of_sold_products": "freezer + cooking kWh x market grid (method choice; Apetit sample uses a different basis)",
    "cat12_end_of_life": "packaging put on market x Finnish treatment mix",
}
sv_ = s.set_index(["scope", "category"]).tco2e
tmpl["tco2e"] = [round(float(sv_.get((r.scope, r.category), np.nan)), 2) for r in tmpl.itertuples()]
tmpl["method_note"] = [NOTES.get(c, "sum of lines" if sc == "total" else "biogenic CO2 memo (not in Scope 1)") for sc, c in zip(tmpl.scope, tmpl.category)]
tmpl.to_csv(SUB / "A2_inventory_2025_submission.csv", index=False)

# inventory lines 2025 with provenance
ef_lib = raw["ef_library"].set_index("ef_id")
def src(b):
    if b in ef_lib.index:
        r = ef_lib.loc[b]
        return f"{b}: {r['name']} ({r.reference_source}; {r.value_status})"
    return b
inv25["factor_source"] = inv25.basis.map(src)
pur = T["purchases"][T["purchases"].year == 2025]
cnt = pur.groupby(["material_id", "supplier_id"]).size()
inv25["n_source_records"] = [int(cnt.get(tuple(li.split(":")), 0)) if c == "cat01_purchased_goods" and ":" in li and not li.startswith("contract") else np.nan
                             for c, li in zip(inv25.category, inv25.line_item)]
inv25.to_csv(OUT / "inventory_lines_2025.csv", index=False)

# ------------------------------------------------------------------ FLAG split 2025 (cat 1)
mm = raw["materials"].set_index("material_id")
flag_share = raw["ef_library"].set_index("ef_id").flag_share
rows = []
for _, r in inv25[inv25.category == "cat01_purchased_goods"].iterrows():
    if r.line_item.startswith("contract_farming"):
        crop = r.line_item.split(":")[-1]
        ff = T["farm_footprints"]
        g = ff[(ff.year == 2025) & (ff.crop == crop)]
        fl = g.tco2e_flag.sum()
        rows.append(dict(line_item=r.line_item, tco2e=r.tco2e, flag_tco2e=fl, nonflag_tco2e=r.tco2e - fl, basis="farm calc: N2O, liming, organic soils = FLAG"))
    else:
        mat = r.line_item.split(":")[0]
        fs = float(flag_share.get(mm.loc[mat, "default_ef_id"], 0) or 0)
        rows.append(dict(line_item=r.line_item, tco2e=r.tco2e, flag_tco2e=r.tco2e * fs, nonflag_tco2e=r.tco2e * (1 - fs), basis=f"library flag_share {fs}"))
for _, r in inv25[inv25.category == "cat01_purchased_services"].iterrows():
    rows.append(dict(line_item=r.line_item, tco2e=r.tco2e, flag_tco2e=0.0, nonflag_tco2e=r.tco2e, basis="services: non-FLAG"))
flag = pd.DataFrame(rows)
flag.to_csv(OUT / "flag_split_2025.csv", index=False)

# ------------------------------------------------------------------ farm footprints 2025 & organic-soil impact
ff = T["farm_footprints"]
ff25 = ff[ff.year == 2025].copy()
ff25["tco2e_nonflag"] = ff25.tco2e - ff25.tco2e_flag
ff25[["farm_id", "crop", "year", "qty_kg", "source", "org_share", "kg_per_kg", "tco2e", "tco2e_flag", "tco2e_nonflag", "tco2e_org"]].round(4).to_csv(OUT / "farm_footprints_2025.csv", index=False)
cur = raw["current_fp"]
oi = ff.merge(cur[["farm_id", "crop", "year", "carbon_footprint_kgco2e_per_kg"]], on=["farm_id", "crop", "year"], how="left")
oi["tco2e_current_calc"] = oi.qty_kg * oi.carbon_footprint_kgco2e_per_kg / 1000
org_imp = oi.groupby(["year", "crop"]).agg(delivered_t=("qty_kg", lambda x: x.sum() / 1000), tco2e_current_calculator=("tco2e_current_calc", "sum"),
                                         tco2e_corrected=("tco2e", "sum"), tco2e_organic_soil=("tco2e_org", "sum")).reset_index()
org_imp["kg_per_kg_current"] = org_imp.tco2e_current_calculator / org_imp.delivered_t
org_imp["kg_per_kg_corrected"] = org_imp.tco2e_corrected / org_imp.delivered_t
org_imp["organic_share_of_emissions_pct"] = 100 * org_imp.tco2e_organic_soil / org_imp.tco2e_corrected
org_imp.round(3).to_csv(OUT / "organic_soil_impact.csv", index=False)

# ------------------------------------------------------------------ canonical pickle
with open(OUT / "canonical_clean.pkl", "wb") as fh:
    pickle.dump({k: v for k, v in T.items()}, fh)

# ------------------------------------------------------------------ E numeric inputs
E = {}
def ev(q, v, evid):
    E[q] = dict(value=round(float(v), 3), evidence=evid)
L = inv25
def lsum(mask):
    return float(L[mask].tco2e.sum())
ev("E01", lsum((L.scope == "scope1") & L.line_item.isin(["S-SAK:lng", "S-SAK:lpg"])),
   "lines_long.csv 2025 scope1 S-SAK:lng + S-SAK:lpg; fuel_deliveries (t) x NCV 13.5/12.8 MWh/t - stock change; EF 0.1991/0.2336 t/MWh")
ev("E02", s.set_index("category").tco2e["scope2_market_total"],
   "Registry GoOs (goo_registry_statement.csv; internal log goo:S-PUD:2025 vintage 2023 and goo:S-BJU:2025 4460 MWh rejected). Residual mix FI 0.406, SE 0.035; S-HQ uncovered (landlord contract)")
ev("E03", lsum((L.scope == "scope2_location") & (L.line_item == "S-KAN")), "lines_long.csv 2025 scope2_location S-KAN (electricity x FI grid 0.026)")
imp_mats = ["M102", "M103", "M104", "M105", "M106", "M107"]
ev("E04", lsum((L.category == "cat01_purchased_goods") & L.line_item.str.split(":").str[0].isin(imp_mats)),
   "cat01 lines M102-M107 (rapeseed imports EE/LV/LT/SE/DK/PL); valid PCF else library EF; stale PCFs SUP022/SUP023_M107_2025 rejected")
c1 = L[L.category.str.startswith("cat01")].tco2e.sum()
rap = lsum((L.category == "cat01_purchased_goods") & (L.line_item.str.split(":").str[0].isin(["M101"] + imp_mats) | (L.line_item == "contract_farming:FI_SW:turnip_rape")))
ev("E05", 100 * rap / c1, f"(M101-M107 lines + contract_farming:FI_SW:turnip_rape) / cat01 goods+services total {c1:,.0f} t")
tot = s.set_index("category").tco2e
total_mb = tot["scope1_total"] + tot["scope2_market_total"] + tot["scope3_total"]
ev("E06", 100 * flag.flag_tco2e.sum() / total_mb, f"flag_split_2025.csv FLAG {flag.flag_tco2e.sum():,.0f} t / S1+S2MB+S3 {total_mb:,.0f} t (only cat 1 carries FLAG)")
ev("E07", 100 * ff25.tco2e_org.sum() / ff25.tco2e.sum(), "farm_footprints_2025.csv sum(tco2e_org)/sum(tco2e); organic share from soil map x calibrated recall 1.17")
ch = raw["crop_history"].merge(raw["parcels"][["parcel_id", "area_ha", "soil_class_soilmap"]], on="parcel_id")
ch = ch[(ch.year == 2025) & ch.crop.isin(["pea", "potato", "carrot", "spinach", "turnip_rape"]) & ch.farm_id.str.startswith("F")]
ch["org"] = (ch.soil_class_soilmap == "organic") * ch.area_ha
fs_ = ch.groupby("farm_id")[["org", "area_ha"]].sum()
ev("E08", int((fs_.org / fs_.area_ha >= 0.3).sum()), "parcels.csv soil_class_soilmap x parcel_crop_history 2025 contract crops; farms with organic area/contract area >= 0.30 (soil map, ~88 % accurate)")
en = T["energy"]
kan = en[(en.year == 2025) & (en.site_id == "S-KAN")]
bio = sum(g.mwh.sum() * F.FUEL_BIOGENIC_T_PER_MWH.get(c, 0) for c, g in kan.groupby("carrier"))
ev("E09", bio, "S-KAN 2025 wood_chips x 0.4032 + oilseed_sidestream x 0.45 t/MWh (+diesel bio share if any); gap-filled months included")
sak = en[(en.year == 2025) & (en.site_id == "S-SAK")]
sak_el = sak[sak.carrier == "electricity"].mwh.sum()
ev("E10", sak_el, "energy_meter_readings S-SAK 2025 electricity after corrections (corrections_log.csv)")
goo25 = T["goo"]; gsak = goo25[(goo25.year == 2025) & (goo25.site_id == "S-SAK") & (goo25.vintage_year == 2025)].mwh_cancelled.sum()
fuels = sak[sak.carrier != "electricity"]
ren = fuels[fuels.carrier.isin(F.FUEL_RENEWABLE)].mwh.sum() + min(gsak, sak_el)
ev("E11", 100 * ren / (fuels.mwh.sum() + sak_el), f"S-SAK 2025: renewable fuels {fuels[fuels.carrier.isin(F.FUEL_RENEWABLE)].mwh.sum():,.0f} MWh + GoO elec {min(gsak, sak_el):,.0f} / (fuels {fuels.mwh.sum():,.0f} + elec {sak_el:,.0f})")
w = raw["water"]; w24 = w[w.year == 2024]
wd = w24[(w24.flow == "withdrawal") & (w24.source_or_destination != "reused_water")].m3.sum(); dc = w24[w24.flow == "discharge"].m3.sum()
ev("E12", wd - dc, f"water_balance.csv 2024: withdrawals excl. reused_water {wd:,} - discharges incl. runoff {dc:,}")
ev("E13", lsum((L.category == "fugitive_refrigerants") & L.line_item.str.startswith("S-SAK")), "lines_long 2025 fugitive_refrigerants S-SAK:*; R717 GWP 0")
ev("E14", lsum((L.category == "cat04_upstream_transport") & L.line_item.isin(["inbound:EF-TKM-SHIP-BULK", "inbound:EF-TKM-SHIP-REEFER"])),
   "cat04 lines inbound:EF-TKM-SHIP-BULK + SHIP-REEFER 2025, incl. imputed missing legs (corrections_log missing_leg)")
ev("E15", pur[pur.material_id == "M130"].qty_kg.sum() / 1000, "ERP 2025 M130 soy protein isolate, receipts minus 122 returns, after corrections")
for q, crop in (("E16", "pea"), ("E17", "turnip_rape")):
    g = ff25[ff25.crop == crop]
    ev(q, g.tco2e.sum() * 1000 / g.qty_kg.sum(), f"farm_footprints_2025.csv {crop}: sum(tco2e)/sum(delivered kg), {len(g)} farms; organic soils included")
# E18: FI pea production 2025 -> 2026 (register area x survey yield, crop-year median for non-respondents)
chp = raw["crop_history"].merge(raw["parcels"][["parcel_id", "area_ha"]], on="parcel_id")
chp = chp[(chp.crop == "pea") & chp.farm_id.str.startswith("F") & chp.year.isin([2025, 2026])]
ar = chp.groupby(["farm_id", "year"]).area_ha.sum().reset_index()
svp = raw["farm_survey"]; svp = svp[(svp.crop == "pea") & svp.year.isin([2025, 2026])]
cl = fnd[(fnd.table == "farm_survey") & (fnd.field == "yield_t_ha")]
ar = ar.merge(svp[["farm_id", "year", "yield_t_ha"]], on=["farm_id", "year"], how="left")
ar["yield_t_ha"] = ar.yield_t_ha.fillna(ar.groupby("year").yield_t_ha.transform("median"))
prod = (ar.area_ha * ar.yield_t_ha).groupby(ar.year).sum()
ev("E18", 100 * (prod[2026] / prod[2025] - 1), f"Estimate: register pea area x survey yield (median for non-respondents): {prod[2025]:,.0f} t -> {prod[2026]:,.0f} t. ERP has no 2026 lines.")
fh = raw["foodhills"].groupby("skördeår").levererad_mängd_ton.sum()
ev("E19", 100 * (fh[2026] / fh[2025] - 1), f"foodhills_odlingsdata_se.csv levererad_mängd_ton: {fh[2025]:,.1f} t (2025) -> {fh[2026]:,.1f} t (2026)")
s12 = tot["scope1_total"] + tot["scope2_market_total"]
ev("E20", s12 * (1 - 0.042 * 7), f"2025 S1+S2MB {s12:,.1f} t x (1 - 0.042 x 7)")
ev("E21", flag.flag_tco2e.sum() * (1 - 0.0303 * 7), f"2025 FLAG {flag.flag_tco2e.sum():,.1f} t x (1 - 0.0303 x 7)")
s24 = RC.summarise(RC.compute_inventory(T, 2024)).set_index("category").tco2e
ev("E90", s24["scope1_total"], "2024 scope1_total"); ev("E91", s24["scope2_market_total"], "2024 scope2_market_total")
ev("E92", s24["cat01_purchased_goods_services"], "2024 cat01 goods+services")
json.dump(E, open(OUT / "e_numeric_inputs.json", "w"), indent=1, ensure_ascii=False)
json.dump(dev, open(OUT / "dev_scores.json", "w"), indent=1, default=str)

print(json.dumps({"A1_dev": dev["A1_dev_2023_2024"]["score"], "A2_dev_2023": dev["A2_dev_2023"]["score"], "A2_dev_2024": dev["A2_dev_2024"]["score"],
                  "A1_2025_flags": len(s25)}, indent=1))
print(tmpl.to_string(index=False))
print(json.dumps({k: v["value"] for k, v in E.items()}, indent=0))
