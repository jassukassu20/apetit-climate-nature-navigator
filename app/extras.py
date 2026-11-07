"""Extra data for the v2 app: farm visit plan (peat), data-check cards with impact, map points, route.
Called from build.py: DATA.update(extras(W, PKG))."""
import json, math
from pathlib import Path
import numpy as np, pandas as pd

CROPS = ["pea", "turnip_rape", "spinach", "potato", "carrot"]


def _route(points, depot):
    """Nearest-neighbour + 2-opt round trip; returns order and straight-line km."""
    def hv(a, b):
        p1, p2 = math.radians(a[0]), math.radians(b[0]); dl = math.radians(b[1] - a[1])
        return 2 * 6371 * math.asin(math.sqrt(math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2))
    pts = [depot] + points; n = len(pts)
    M = [[hv(pts[i], pts[j]) for j in range(n)] for i in range(n)]
    tour, left = [0], set(range(1, n))
    while left:
        j = min(left, key=lambda k: M[tour[-1]][k]); tour.append(j); left.remove(j)
    tour.append(0)
    L = lambda t: sum(M[t[i]][t[i + 1]] for i in range(len(t) - 1))
    better = True
    while better:
        better = False
        for i in range(1, len(tour) - 2):
            for k in range(i + 1, len(tour) - 1):
                nt = tour[:i] + tour[i:k + 1][::-1] + tour[k + 1:]
                if L(nt) < L(tour) - 1e-6:
                    tour, better = nt, True
    return [t - 1 for t in tour], L(tour)


def extras(W, PKG):
    D = PKG / "data"; A = W / "A"
    out = {}
    # ---------------------------------------------------------------- farms & peat
    ff = pd.read_csv(A / "farm_footprints_2025.csv")
    reg = pd.read_csv(D / "01_master/farm_registry.csv")
    swap = reg.lat < 40
    reg.loc[swap, ["lat", "lon"]] = reg.loc[swap, ["lon", "lat"]].values
    ff = ff.merge(reg[["farm_id", "region", "lat", "lon", "joined_year"]], on="farm_id")
    fi = ff[ff.region == "FI_SW"]
    g = fi.groupby("farm_id").agg(t=("tco2e", "sum"), org=("tco2e_org", "sum"), flag=("tco2e_flag", "sum"),
                                  src=("source", lambda s: "survey" if (s == "survey").any() else "imputed")).sort_values("t", ascending=False)
    g["cum"] = g.t.cumsum() / g.t.sum()
    half_n = int((g.cum < 0.5).sum() + 1)
    parcels = pd.read_csv(D / "01_master/parcels.csv")
    hist = pd.read_csv(D / "03_farming/parcel_crop_history_and_plan.csv")
    h25 = hist[(hist.year == 2025) & hist.crop.isin(CROPS)].merge(parcels, on=["parcel_id", "farm_id"])
    survey = pd.read_csv(D / "03_farming/farm_survey_fi.csv")
    s25 = survey[survey.year == 2025]
    a1 = pd.read_csv(W / "submissions/A1_issues_submission.csv")
    soil_keys = set(a1[a1.issue_type == "soil_misreport"].record_key)
    # weather: June–July rain and hot days, 2025 vs 1991–2020, nearest grid cell
    cells = pd.read_csv(D / "01_master/climate_grid_cells.csv"); cells = cells[cells.region == "FI_SW"]
    wm = pd.read_csv(D / "04_climate/weather_monthly_1991_2060.csv")
    wm = wm[(wm.scenario == "historical") & wm.month.isin([6, 7])]
    wy = wm.groupby(["cell_id", "year"]).agg(p=("precip_mm", "sum"), hot=("hot_days_tmax_ge_27", "sum")).reset_index()
    norm = wy[wy.year.between(1991, 2020)].groupby("cell_id")[["p", "hot"]].mean(); w25 = wy[wy.year == 2025].set_index("cell_id")
    med_y = survey[survey.year.between(2016, 2025)].groupby("crop").yield_t_ha.median()
    regi = reg.set_index("farm_id")
    farms = []
    for rank, (fid, r) in enumerate(g.iterrows(), start=1):
        p = h25[h25.farm_id == fid]
        sv = s25[s25.farm_id == fid]
        rec = {"id": fid, "rank": rank, "t": round(r.t, 1), "org": round(r.org, 1), "flag": round(r.flag, 1), "cum": round(r.cum, 4),
               "lat": float(regi.loc[fid, "lat"]), "lon": float(regi.loc[fid, "lon"]), "src": r.src}
        if rank <= 60:
            d = (cells.lat - rec["lat"]) ** 2 + ((cells.lon - rec["lon"]) * math.cos(math.radians(rec["lat"]))) ** 2
            cell = cells.cell_id.iloc[int(np.argmin(d.values))]
            crops = p.groupby("crop").area_ha.sum().round(1).to_dict()
            main = max(crops, key=crops.get) if crops else None
            yv = sv[sv.crop == main].yield_t_ha
            y25 = None if yv.empty else float(yv.iloc[0] / 10 if yv.iloc[0] > 3 * med_y.get(main, 99) else yv.iloc[0])
            yh = survey[(survey.farm_id == fid) & (survey.crop == main) & survey.year.between(2016, 2024)].yield_t_ha
            yh = yh[yh <= 3 * med_y.get(main, 99)]
            reported = None if sv.empty else ("organic" if (sv.soil_type_reported == "Organic soil").any() else "mineral")
            flagged = sorted(k for k in (f"farm_survey:{s}" for s in sv.survey_id) if k in soil_keys)
            org_p = p[p.soil_class_soilmap == "organic"]
            rec.update({"joined": int(regi.loc[fid, "joined_year"]), "crops": crops, "main": main, "reported": reported, "soil_flags": flagged,
                        "area": round(float(p.area_ha.sum()), 1), "peat_ha_map": round(float(org_p.area_ha.sum()), 1),
                        "peat_parcels": [{"id": x.parcel_id, "ha": round(x.area_ha, 1), "crop": x.crop} for x in org_p.itertuples()],
                        "parcels": [{"id": x.parcel_id, "lat": x.lat, "lon": x.lon, "ha": round(x.area_ha, 1), "soil": x.soil_class_soilmap,
                                     "water": int(x.dist_to_water_m), "buffer": bool(x.buffer_strip)} for x in p.itertuples()],
                        "wx": {"cell": cell, "p25": round(float(w25.loc[cell, "p"])), "pn": round(float(norm.loc[cell, "p"])),
                               "h25": int(w25.loc[cell, "hot"]), "hn": round(float(norm.loc[cell, "hot"]), 1),
                               "y25": None if y25 is None else round(y25, 2), "yavg": None if yh.empty else round(float(yh.median()), 2)}})
        farms.append(rec)
    top = farms[:half_n]
    order, km = _route([(f["lat"], f["lon"]) for f in top], (61.078744, 22.253773))
    peat_grass_cut = (29.0 - 20.9)  # t CO2/ha/yr, METHODOLOGY §5 (N2O unchanged)
    out["farms"] = {"list": farms, "half_n": half_n, "n": len(farms), "total_t": round(float(g.t.sum())), "org_t": round(float(g.org.sum())),
                    "top_t": round(sum(f["t"] for f in top)), "top_org_t": round(sum(f["org"] for f in top)),
                    "top_peat_ha": round(sum(f.get("peat_ha_map", 0) for f in top), 1),
                    "grass_cut_t_ha": peat_grass_cut, "org_scale": 1.17,
                    "route": {"order": [top[i]["id"] if i >= 0 else "SAKYLA" for i in order], "km_road": round(km * 1.3), "days": math.ceil(half_n / 3)},
                    "swapped": sorted(reg[swap].farm_id), "depot": {"lat": 61.078744, "lon": 22.253773}}
    # ---------------------------------------------------------------- data-check cards (2025)
    cl = pd.read_csv(A / "corrections_log.csv"); cl = cl[cl.year == 2025].copy()
    erp = pd.read_csv(D / "02_raw_feeds/erp_purchase_lines_2021_2025.csv", dtype={"doc_no": str})
    erp["key"] = "erp:" + erp.doc_no + ":" + erp.line_no.astype(str)
    mat = pd.read_csv(D / "01_master/materials.csv"); ef = pd.read_csv(D / "01_master/emission_factor_library.csv").set_index("ef_id")
    mef = {r.material_id: (float(ef.loc[r.default_ef_id, "kgco2e_per_unit"]), ef.loc[r.default_ef_id, "unit"]) for r in mat.itertuples() if r.default_ef_id in ef.index}
    mname = mat.set_index("material_id").name_en.to_dict()
    fx = {"SEK": 11.22, "USD": 1.01}
    E = erp.set_index("key")
    farm_org = g.org.to_dict()
    survey_farm = survey.set_index("survey_id").farm_id.to_dict()
    cards = []
    for r in cl.itertuples():
        c = {"key": r.record_key, "table": r.table, "type": r.issue_type, "field": r.field, "was": str(r.original_value), "is": str(r.corrected_value),
             "why": r.reason, "conf": float(r.confidence), "review": bool(r.needs_expert_review), "dt": None, "eur": None, "label": None}
        if r.table == "erp_purchase_lines" and r.record_key in E.index:
            x = E.loc[r.record_key]; m = mef.get(x.material_id); c["label"] = mname.get(x.material_id, x.material_id)
            kg = x.quantity * (1000 if x.uom == "TO" else 1) if x.uom in ("KG", "TO") else None
            if r.issue_type in ("unit_error", "decimal_shift") and kg and m and m[1] == "kg":
                try: c["dt"] = (float(r.corrected_value) - float(r.original_value)) * (1000 if x.uom == "TO" else 1) * m[0] / 1000
                except ValueError: pass
            if r.issue_type == "duplicate_record":
                c["eur"] = -float(x.net_amount)
                if kg and m and m[1] == "kg": c["dt"] = -kg * m[0] / 1000
                elif m and m[1] == "EUR": c["dt"] = -x.net_amount * m[0] / 1000
            if r.issue_type == "currency_error" and r.field == "net_amount":
                c["eur"] = float(r.corrected_value) - float(r.original_value)
                c["was"], c["is"] = f"€{float(r.original_value):,.0f}", f"€{float(r.corrected_value):,.0f}"
                if m and m[1] == "EUR": c["dt"] = c["eur"] * m[0] / 1000
            elif r.issue_type == "currency_error":
                rate = fx.get(str(r.corrected_value), 1)
                c["eur"] = -(x.net_amount - x.net_amount / rate)
                if m and m[1] == "EUR" and x.uom == "EUR": c["dt"] = c["eur"] * m[0] / 1000
        if r.issue_type == "soil_misreport":
            fid = survey_farm.get(r.record_key.split(":")[1]); c["label"] = f"Farm {fid}"; c["farm"] = fid
            c["dt"] = farm_org.get(fid)  # emissions added by counting the organic soil
        for k in ("dt", "eur"):
            if c[k] is not None and (isinstance(c[k], float) and math.isnan(c[k])): c[k] = None
            elif c[k] is not None: c[k] = round(c[k], 1)
        cards.append(c)
    out["cards"] = cards
    out["mapfarms"] = [{"id": f["id"], "lat": f["lat"], "lon": f["lon"], "t": f["t"], "rank": f["rank"], "org": f["org"]} for f in farms]
    out["fi_geo"] = {"type": "FeatureCollection", "features": [f for f in json.load(open(W / "D/catchments_web.geojson"))["features"] if f["properties"].get("region") == "FI_SW"]}
    # ERP rows + master for the in-browser number check (own-file upload)
    cols = ["doc_no", "line_no", "posting_date", "material_id", "supplier_id", "quantity", "uom", "net_amount", "currency", "movement_type"]
    # reference statistics for single-entry checks (Add data)
    e = erp.copy(); e["kg"] = np.where(e.uom == "TO", e.quantity * 1000, np.where(e.uom == "KG", e.quantity, np.nan))
    e["credit"] = (e.quantity < 0) | (e.net_amount < 0) | e.movement_type.isin([102, 122])
    clean = e[~e.credit & (e.kg > 0) & (e.currency == "EUR")]
    clean = clean[~clean.key.isin(cl.record_key)]
    ppk = (clean.net_amount / clean.kg).groupby(clean.material_id).median()
    qmed = clean.groupby(["supplier_id", "material_id"]).kg.median()
    supc = e.groupby("supplier_id").currency.agg(lambda s: s.mode().iloc[0])
    sups = pd.read_csv(D / "01_master/suppliers.csv")
    kgmats = [m for m, v in mef.items() if v[1] == "kg" and m in ppk.index]
    out["ref"] = {"ppk": {m: round(float(ppk[m]), 4) for m in kgmats},
                  "qmed": {f"{a}|{b}": round(float(v), 1) for (a, b), v in qmed.items()},
                  "supcur": supc.to_dict(), "sek": 11.22, "usd": 1.01,
                  "materials": [{"id": m, "n": mname.get(m, m), "ef": mef[m][0]} for m in sorted(kgmats, key=lambda m: mname.get(m, m))],
                  "suppliers": [{"id": r.supplier_id, "mat": r.material_id, "country": r.country} for r in sups.itertuples() if r.material_id in kgmats],
                  "yield_med": survey[survey.year.between(2016, 2025)].groupby("crop").yield_t_ha.median().round(2).to_dict()}
    allf = h25.groupby("farm_id").agg(area=("area_ha", "sum")).join(h25[h25.soil_class_soilmap == "organic"].groupby("farm_id").area_ha.sum().rename("peat"))
    allf = allf.fillna(0)
    cropA = h25.groupby(["farm_id", "crop"]).area_ha.sum().round(1)
    out["ref"]["farms"] = {fid: {"area": round(float(r.area), 1), "peat": round(float(r.peat), 1), "org": round(float(farm_org.get(fid, 0)), 1),
                                 "crops": {c: float(a) for c, a in cropA.loc[fid].items()} if fid in cropA.index.get_level_values(0) else {}}
                           for fid, r in allf.iterrows() if fid in farm_org}
    out["erp_master"] = {"mat": {k: {"n": mname.get(k, k), "ef": v[0], "u": v[1]} for k, v in mef.items()},
                         "sup": pd.read_csv(D / "01_master/suppliers.csv").set_index("supplier_id").material_id.to_dict()}
    return out
