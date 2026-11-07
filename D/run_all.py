"""Track D end-to-end: D1 nutrient loads + priority, parcel hotspots + measures, web geojson, D2 screening.
Run: python -I $CCN_WORK/D/run_all.py
"""
import json, sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/D")
from model import ROOT, D, STATE_W, load, build_parcels, field_losses, catchment_sums  # noqa: E402

sys.path.insert(0, str(ROOT / "tools"))
from ccn_tools import score as SC  # noqa: E402

OUT = Path(__import__("os").environ["CCN_WORK"] + "/D"); SUB = Path(__import__("os").environ["CCN_WORK"] + "/submissions"); SUB.mkdir(parents=True, exist_ok=True)
L_P, L_N = 400.0, 300.0           # delivery-decay lengths (m), chosen by leave-one-out CV on dev catchments
YEAR = 2025

data = load()
par, ch, cat, sv, fh, cells, wm, loads = data
p = build_parcels(YEAR, data)
fl = field_losses(p, L_P, L_N)

# Regional N factor for Skåne from monitored outlet loads (independent of dev keys):
l = loads[loads.year.between(2019, 2025)].merge(cat, on="catchment_id")
l["n_ha"] = l.total_n_load_kg / l.field_area_total_ha / (1 - l.nutrient_retention_frac_estimate)
se_n_factor = float(l[l.region == "SE_SKANE"].n_ha.median() / l[l.region == "FI_SW"].n_ha.median())
fl["n_water"] = fl["n_water"] * np.where(p.region == "SE", se_n_factor, 1.0)

dev = pd.read_csv(ROOT / "tasks/dev/D1_dev_catchments_2025.csv").set_index("catchment_id")
raw = catchment_sums(p, fl)


def scales(excl=None):
    m = raw.join(dev, how="inner")
    if excl is not None:
        m = m.drop(index=excl)
    return (float(np.exp(np.mean(np.log(m.apetit_p_to_water_kg / m.P)))),
            float(np.exp(np.mean(np.log(m.apetit_n_to_water_kg / m.N)))))


def make_sub(sp, sn):
    c = cat.set_index("catchment_id")
    P = (raw.P * sp).reindex(c.index).fillna(0.0)
    N = (raw.N * sn).reindex(c.index).fillna(0.0)
    pr = (P / P[P > 0].median() + 0.5 * N / N[N > 0].median()) * c.ecological_status_class.map(STATE_W) * c.p_sensitivity
    s = pd.DataFrame(dict(catchment_id=c.index, region=c.region.values, apetit_p_to_water_kg=P.round(2).values,
                          apetit_n_to_water_kg=N.round(1).values, priority_score=pr.round(3).values))
    s["priority_rank"] = s.priority_score.rank(ascending=False, method="first").astype(int)
    return s


SP, SN = scales()
sub = make_sub(SP, SN)
in_sample = SC.score_d1(sub, dev.reset_index())
# Leave-one-out: each dev catchment predicted with scales fitted on the other five
loo_rows = []
for cid in dev.index:
    sp, sn = scales(excl=cid)
    loo_rows.append(make_sub(sp, sn).set_index("catchment_id").loc[cid])
loo = sub.set_index("catchment_id").copy()
for r in loo_rows:
    loo.loc[r.name, ["apetit_p_to_water_kg", "apetit_n_to_water_kg"]] = r[["apetit_p_to_water_kg", "apetit_n_to_water_kg"]].values
loo_score = SC.score_d1(loo.reset_index(), dev.reset_index())
base = pd.read_csv(ROOT / "outputs/D1_baseline.csv") if (ROOT / "outputs/D1_baseline.csv").exists() else None
base_score = SC.score_d1(base, dev.reset_index()) if base is not None else None

sub[["catchment_id", "region", "apetit_p_to_water_kg", "apetit_n_to_water_kg", "priority_rank"]].to_csv(
    SUB / "D1_catchment_priority_submission.csv", index=False)
sub.to_csv(OUT / "d1_catchments_full.csv", index=False)

# ---------------- parcel losses + drivers ----------------
p["p_kg"] = (fl["p_water"] * SP).round(3)
p["n_kg"] = (fl["n_water"] * SN).round(2)
p["p_kg_ha"] = (p.p_kg / p.area_ha).round(3)
p["n_kg_ha"] = (p.n_kg / p.area_ha).round(2)


def drivers(r):
    d = []
    if r.soil_class_soilmap in ("clay", "silt"): d.append(f"erodible {r.soil_class_soilmap} soil")
    if r.slope_pct > 3: d.append(f"slope {r.slope_pct:.1f}%")
    if r.p_test > 20: d.append(f"high soil-P {r.p_test:.0f} mg/l" + (" (imputed)" if r.p_test_imputed else ""))
    if r.dist_to_water_m < 150: d.append(f"{r.dist_to_water_m} m to water")
    if not r.buffer_strip and r.dist_to_water_m < 250: d.append("no buffer strip")
    if not r.catch_crop: d.append("no catch crop")
    if r.crop in ("potato", "carrot", "spinach"): d.append(f"row crop ({r.crop})")
    if r.n_surplus > 60: d.append(f"N surplus {r.n_surplus:.0f} kg/ha")
    if r.rain_factor > 1.15: d.append(f"wet year ({r.rain_factor:.2f}x normal)")
    if r.soil_class_soilmap == "organic": d.append("organic (peat) soil")
    return "; ".join(d[:4])


p["main_drivers"] = p.apply(drivers, axis=1)
cols = ["parcel_id", "farm_id", "catchment_id", "region", "lat", "lon", "area_ha", "crop", "soil_class_soilmap", "slope_pct",
        "dist_to_water_m", "buffer_strip", "catch_crop", "p_test", "p_test_imputed", "n_surplus", "p_kg", "n_kg", "p_kg_ha", "n_kg_ha", "main_drivers"]
p[cols].round(3).to_csv(OUT / "parcel_losses_2025.csv", index=False)

# ---------------- measures for hotspots ----------------
# Measure effects use the same model factors (so avoided kg is internally consistent); costs are stated assumptions.
MEAS = [
    # id, lever, applies(r), P reduction share, N reduction share, cost EUR/ha/yr, note
    ("buffer_strip", "L09/L24 (agri-env)", lambda r: (not r.buffer_strip) and r.dist_to_water_m < 300, 0.30, 0.10, 45,
     "15 m grassed buffer; cost = foregone margin on strip area, spread per field ha"),
    ("catch_crop", "L10", lambda r: (not r.catch_crop) and r.crop in ("pea", "spinach", "potato", "carrot"), 0.15, 0.30, 80,
     "catch crop after early harvest; ~EUR 80/ha/yr seed+work (cf. FI agri-env payment)"),
    ("gypsum", "L09 (SAVE-type gypsum)", lambda r: r.soil_class_soilmap in ("clay", "silt") and r.slope_pct < 6, 0.40, 0.0, 45,
     "gypsum 4 t/ha; ~EUR 200/ha one-off, effect ~4.5 yr"),
    ("p_drawdown", "L09", lambda r: r.p_test > 20, 0.10, 0.0, -10,
     "stop/reduce P fertilisation on high soil-P fields (saves fertiliser)"),
    ("precision_n", "L09", lambda r: r.n_surplus > 60, 0.0, 0.20, 20, "variable-rate N + soil testing"),
    ("retire_peat", "L11/L12", lambda r: r.soil_class_soilmap == "organic", 0.20, 0.40, 300,
     "shift contract area off drained peat; also ~29 tCO2/ha/yr FLAG abatement"),
]
hot = p.sort_values("p_kg", ascending=False).head(50).copy()
recs = []
for _, r in hot.iterrows():
    ms = []
    for mid, lever, ok, rp, rn, cost, note in MEAS:
        if ok(r):
            kgp = r.p_kg * rp; kgn = r.n_kg * rn; eur = cost * r.area_ha
            ms.append(dict(measure=mid, lever=lever, kg_p_avoided=kgp, kg_n_avoided=kgn, eur_yr=eur,
                           eur_per_kg_p=(eur / kgp if kgp > 0 else np.nan), note=note))
    ms = sorted(ms, key=lambda m: (np.inf if np.isnan(m["eur_per_kg_p"]) else m["eur_per_kg_p"]))
    best = ms[:2]
    rem_p = 1.0; rem_n = 1.0; eur = 0.0
    for mid, lever, ok, rp, rn, cost, note in MEAS:
        if any(b["measure"] == mid for b in best):
            rem_p *= (1 - rp); rem_n *= (1 - rn); eur += cost * r.area_ha
    kgp = r.p_kg * (1 - rem_p); kgn = r.n_kg * (1 - rem_n)
    recs.append(dict(parcel_id=r.parcel_id, farm_id=r.farm_id, catchment_id=r.catchment_id, lat=r.lat, lon=r.lon,
                     crop=r.crop, area_ha=r.area_ha, p_kg=r.p_kg, n_kg=r.n_kg, main_drivers=r.main_drivers,
                     recommended=" + ".join(f"{b['measure']} ({b['lever']})" for b in best),
                     kg_p_avoided=round(kgp, 2), kg_n_avoided=round(kgn, 1), eur_per_yr=round(eur, 0),
                     eur_per_kg_p=round(eur / kgp, 0) if kgp > 0 else None,
                     review_status="pending_expert_review"))
hs = pd.DataFrame(recs)
hs.to_csv(OUT / "hotspots_top50.csv", index=False)

# Catchment-level programme: apply cheapest-per-kg-P measures to all parcels in top-5 priority catchments
top5 = sub.nsmallest(5, "priority_rank").catchment_id.tolist()
prog = []
for cid in top5:
    q = p[p.catchment_id == cid]
    tot_p = q.p_kg.sum(); av = 0; eur = 0
    for _, r in q.iterrows():
        rem = 1; c = 0
        for mid, lever, ok, rp, rn, cost, note in MEAS[:3]:
            if ok(r): rem *= (1 - rp); c += cost * r.area_ha
        av += r.p_kg * (1 - rem); eur += c
    prog.append(dict(catchment_id=cid, contract_parcels=len(q), contract_ha=round(q.area_ha.sum(), 1),
                     p_kg=round(tot_p, 1), p_avoided_kg=round(av, 1), share=round(av / tot_p, 3), eur_yr=round(eur),
                     eur_per_kg_p=round(eur / av) if av else None))
pd.DataFrame(prog).to_csv(OUT / "catchment_programme_top5.csv", index=False)

# ---------------- web geojson ----------------
gj = json.loads((D / "06_nature/catchments.geojson").read_text())
si = sub.set_index("catchment_id"); ci = cat.set_index("catchment_id")


def rnd(c):
    return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 4), round(c[1], 4)]


for f in gj["features"]:
    cid = f["properties"].get("catchment_id")
    f["geometry"]["coordinates"] = rnd(f["geometry"]["coordinates"])
    if cid in si.index:
        s = si.loc[cid]
        f["properties"].update(dict(apetit_p_to_water_kg=float(s.apetit_p_to_water_kg), apetit_n_to_water_kg=float(s.apetit_n_to_water_kg),
                                    priority_score=float(s.priority_score), priority_rank=int(s.priority_rank),
                                    ecological_status_class=ci.loc[cid, "ecological_status_class"], receiving_water_type=ci.loc[cid, "receiving_water_type"],
                                    p_sensitivity=float(ci.loc[cid, "p_sensitivity"])))
(OUT / "catchments_web.geojson").write_text(json.dumps(gj, separators=(",", ":")))
# compact parcel points for maps
p[["parcel_id", "catchment_id", "lat", "lon", "area_ha", "crop", "p_kg", "n_kg"]].round(4).to_csv(OUT / "parcel_points_web.csv", index=False)

# ---------------- D2 materiality screening ----------------
mat = pd.read_csv(D / "01_master/materials.csv")
mat["sbtn_high_impact_commodity"] = mat.sbtn_high_impact_commodity.fillna(False).astype(bool)
ef = pd.read_csv(D / "01_master/emission_factor_library.csv").set_index("ef_id")
erp = pd.read_csv(D / "02_raw_feeds/erp_purchase_lines_2021_2025.csv")
erp = erp[erp.posting_date.str[:4] == "2025"]
erp["qty_kg"] = np.where(erp.uom == "TO", erp.quantity * 1000, np.where(erp.uom == "KG", erp.quantity, np.nan))
vol = erp.groupby(["material_id", "origin_country"]).qty_kg.sum().reset_index()
org = pd.read_csv(D / "06_nature/origin_state_of_nature_indicative.csv").set_index("origin_country")
LV = {"low": 0, "medium": 1, "medium (marine)": 1, "high": 2, "high (soy supply chains incl. imports)": 3, "very high": 3}


def nutr(s):
    s = str(s)
    return 3 if s.startswith("poor") else 2 if s.startswith("moderate-poor") else 1 if s.startswith("moderate") else 0


PEST = {"vegetable_bought": 2, "vegetable_contract": 2, "oilseed": 2, "legume": 1, "protein": 2, "sauce": 2, "cereal": 1,
        "oil": 2, "spice": 1, "sugar": 2, "dairy": 1, "meat": 1, "fish": 0}
LAND = {"vegetable_bought": 1, "vegetable_contract": 1, "oilseed": 2, "legume": 1, "protein": 3, "sauce": 1, "cereal": 2,
        "oil": 2, "spice": 1, "sugar": 1, "dairy": 3, "meat": 3, "fish": 0}
cc = pd.read_csv(D / "03_farming/current_calculator_footprints.csv")
FARM_KG = cc[cc.year == 2025].groupby("crop").carbon_footprint_kgco2e_per_kg.median().to_dict()  # current calculator (mineral soil assumed)
FARM_CROP = {"M100": "turnip_rape", "M110": "pea", "M114": "pea", "M111": "potato", "M112": "carrot", "M113": "spinach"}
rows = []
for _, m in mat.iterrows():
    if m.base_uom != "kg" or m.material_group in ("packaging", "chemical"):
        continue
    v = vol[vol.material_id == m.material_id]
    if v.empty:
        v = pd.DataFrame(dict(origin_country=[m.origin_countries.split(";")[0]], qty_kg=[0.0]))
    for _, o in v.iterrows():
        oc = o.origin_country
        f = ef.loc[m.default_ef_id] if m.default_ef_id in ef.index else None
        kg_ef = float(f.kgco2e_per_unit) if f is not None else float(FARM_KG.get(FARM_CROP.get(m.material_id), 0.3))
        flag = float(f.flag_share) if f is not None else 0.6
        t_co2 = o.qty_kg * kg_ef / 1000
        og = org.loc[oc] if oc in org.index else None
        water = int(og.baseline_water_stress_cat_indicative) if og is not None else 1
        defo = LV.get(str(og.deforestation_conversion_risk_indicative), 1) if og is not None else 1
        bio = LV.get(str(og.biodiversity_sensitivity_indicative), 1) if og is not None else 1
        nut = nutr(og.freshwater_nutrient_status_indicative) if og is not None else 1
        if m.sbtn_high_impact_commodity: defo = max(defo, 2)
        rows.append(dict(material_id=m.material_id, name_en=m.name_en, group=m.material_group, origin=oc,
                         t_2025=round(o.qty_kg / 1000, 1), kgco2e_per_kg=kg_ef, flag_share=flag, tco2e=round(t_co2, 1),
                         flag_tco2e=round(t_co2 * flag, 1), p_ghg=0, p_land=LAND.get(m.material_group, 1), p_water=water,
                         p_nutrients=nut, p_pesticides=PEST.get(m.material_group, 1), p_deforestation=defo, p_biodiversity=bio,
                         eudr=bool(m.eudr_commodity) if str(m.eudr_commodity) in ("True", "False") else False,
                         sbtn_hic=bool(m.sbtn_high_impact_commodity)))
d2 = pd.DataFrame(rows)
d2["p_ghg"] = pd.cut(d2.tco2e, [-1, 500, 3000, 15000, 1e12], labels=[0, 1, 2, 3]).astype(int)
vol_w = np.log10(1 + d2.t_2025) / np.log10(1 + d2.t_2025.max())
d2["pressure_index"] = (d2.p_ghg + d2.p_land + d2.p_water + d2.p_nutrients + d2.p_pesticides + d2.p_deforestation + d2.p_biodiversity) / 21
d2["materiality_score"] = (100 * (0.5 * d2.pressure_index + 0.5 * vol_w) * np.where(d2.sbtn_hic, 1.2, 1.0)).round(1)


def rationale(r):
    t = []
    if r.sbtn_hic: t.append("SBTN High Impact Commodity")
    if r.material_id == "M130": t.append("soy protein isolate (HS 3504) is NOT in EUDR Annex I, but soy is high-risk: do voluntary DCF due diligence")
    if r.p_water >= 3: t.append(f"high water stress in {r.origin}")
    if r.p_deforestation >= 2: t.append("deforestation/conversion risk")
    if r.p_nutrients >= 3: t.append("receiving waters poor/nitrate-vulnerable")
    if r.p_ghg >= 2: t.append(f"{r.tco2e:,.0f} tCO2e ({r.flag_share:.0%} FLAG)")
    if r.group == "vegetable_contract": t.append("own contract parcels -> catchment-level D1 assessment")
    return "; ".join(t)


d2["rationale"] = d2.apply(rationale, axis=1)
d2 = d2.sort_values("materiality_score", ascending=False)
d2["rank"] = range(1, len(d2) + 1)
d2.to_csv(OUT / "d2_materiality.csv", index=False)

res = dict(dev_in_sample=in_sample, dev_leave_one_out=loo_score, dev_baseline=base_score, scale_p=SP, scale_n=SN,
           se_n_factor=se_n_factor, L_P=L_P, L_N=L_N, n_parcels=len(p), total_p_kg=float(sub.apetit_p_to_water_kg.sum()),
           total_n_kg=float(sub.apetit_n_to_water_kg.sum()))
(OUT / "d1_metrics.json").write_text(json.dumps(res, indent=1, default=float))
print(json.dumps(res, indent=1, default=float))
print(sub.sort_values("priority_rank").head(10).to_string(index=False))
print(pd.DataFrame(prog).to_string(index=False))
print(hs.head(8)[["parcel_id", "catchment_id", "p_kg", "recommended", "kg_p_avoided", "eur_per_kg_p"]].to_string(index=False))
print(d2.head(12)[["rank", "name_en", "origin", "t_2025", "tco2e", "materiality_score", "rationale"]].to_string(index=False))
