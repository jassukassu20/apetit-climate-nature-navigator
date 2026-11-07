"""Data-quality agent for the Apetit Climate & Nature Navigator package.

detect(raw) -> DataFrame of findings. Each finding carries:
  table, record_key, issue_type, year, confidence, explanation,
  field, original_value, corrected_value, needs_expert_review
Corrections are *proposals*: clean.py applies them, and anything with
needs_expert_review=True is routed to a human before publication.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

PKG = Path(__import__("os").environ["CCN_PKG"] + "")
sys.path.insert(0, str(PKG / "tools"))
from ccn_tools import io as IO          # noqa: E402
from ccn_tools import factors as F      # noqa: E402

FX = F.FX_PER_EUR


def load():
    raw = IO.load_raw(PKG)
    d = PKG / "data"
    raw["goo_registry"] = pd.read_csv(d / "02_raw_feeds" / "goo_registry_statement.csv")
    raw["draft_report"] = pd.read_csv(d / "05_scenarios" / "draft_report_summary_2025.csv")
    raw["current_fp"] = pd.read_csv(d / "03_farming" / "current_calculator_footprints.csv")
    raw["capex"] = pd.read_csv(d / "02_raw_feeds" / "capex_projects.csv")
    raw["foodhills"] = pd.read_csv(d / "03_farming" / "foodhills_odlingsdata_se.csv", sep=";", decimal=",")
    return raw


class Findings:
    def __init__(self):
        self.rows = []

    def add(self, table, key, itype, year, conf, expl, field=None, orig=None, corr=None, review=False):
        self.rows.append(dict(table=table, record_key=key, issue_type=itype, year=year, confidence=round(float(conf), 2),
                              explanation=expl, field=field, original_value=orig, corrected_value=corr,
                              needs_expert_review=bool(review)))

    def df(self):
        d = pd.DataFrame(self.rows)
        # keep the highest-confidence finding per record for the submission; all kept in the log
        return d


# ----------------------------------------------------------------------------- ERP
def erp_checks(raw, f: Findings):
    e = raw["erp"].copy()
    e["year"] = e.posting_date.str[:4].astype(int)
    e["key"] = "erp:" + e.doc_no + ":" + e.line_no.astype(str)
    sup = raw["suppliers"].set_index("supplier_id")
    mats = raw["materials"].set_index("material_id")
    # supplier's usual invoicing currency (mode over all lines)
    usual_cur = e.groupby("supplier_id").currency.agg(lambda s: s.value_counts().index[0])
    flagged = set()

    # 1) duplicates: identical supplier/material/quantity/amount posted again within 10 days
    e["pdate"] = pd.to_datetime(e.posting_date)
    rec = e[e.movement_type == 101].sort_values(["pdate", "doc_no"])
    grp = rec.groupby(["supplier_id", "material_id", "quantity", "net_amount"])
    for _, g in grp:
        if len(g) < 2:
            continue
        first = g.iloc[0]
        for _, r in g.iloc[1:].iterrows():
            if (r.pdate - first.pdate).days <= 10:
                f.add("erp_purchase_lines", r.key, "duplicate_record", r.year, 0.95,
                      f"Same supplier {r.supplier_id}, material {r.material_id}, quantity {r.quantity} {r.uom} and amount "
                      f"{r.net_amount} {r.currency} as doc {first.doc_no} posted {(r.pdate - first.pdate).days} d earlier; "
                      f"duplicate posting -> excluded.", "*", "row", "drop")
                flagged.add(r.key)

    # 2) material mismatch: material differs from the supplier master's material
    for _, r in e[~e.key.isin(flagged)].iterrows():
        if r.supplier_id in sup.index and r.material_id != sup.loc[r.supplier_id, "material_id"] and not str(r.supplier_id).startswith(("F", "S0")):
            true_m = sup.loc[r.supplier_id, "material_id"]
            f.add("erp_purchase_lines", r.key, "material_mismatch", r.year, 0.85,
                  f"Supplier {r.supplier_id} only supplies {true_m} ({mats.loc[true_m, 'name_en']}) per supplier master, "
                  f"but line is coded {r.material_id} ({mats.loc[r.material_id, 'name_en']}). Recoded to {true_m}.",
                  "material_id", r.material_id, true_m)
            flagged.add(r.key)

    # 3) currency: line currency differs from the supplier's usual currency (goods)
    goods = e[(e.uom != "EUR")]
    for _, r in goods[~goods.key.isin(flagged)].iterrows():
        uc = usual_cur.get(r.supplier_id, "EUR")
        if r.currency != uc:
            f.add("erp_purchase_lines", r.key, "currency_error", r.year, 0.8,
                  f"Supplier {r.supplier_id} invoices in {uc} on all other lines; this line says {r.currency}. "
                  f"Amount reinterpreted as {uc}.", "currency", r.currency, uc)
            flagged.add(r.key)

    # 4) unit price outliers on goods (receipts) -> unit_error (t keyed as kg) / decimal shift
    g = e[(e.uom != "EUR") & (e.movement_type == 101) & (e.quantity > 0) & ~e.key.isin(flagged)].copy()
    g["qty_kg"] = np.where(g.uom == "TO", g.quantity * 1000, g.quantity)
    g["cur"] = g.supplier_id.map(usual_cur).fillna(g.currency)
    g["eur"] = g.net_amount / g.cur.map(FX)
    g["up"] = g.eur / g.qty_kg
    g["ref"] = g.groupby(["material_id", "year"]).up.transform("median")
    g["r"] = g.up / g.ref
    for _, r in g.iterrows():
        lr = np.log10(r.r)
        if 2.4 < lr < 3.6:
            corr = r.quantity * 1000
            f.add("erp_purchase_lines", r.key, "unit_error", r.year, 0.95,
                  f"Unit price {r.up:.2f} EUR/kg is {r.r:.0f}x the {r.material_id} median for {r.year}; tonnes keyed with uom KG. "
                  f"Quantity {r.quantity} -> {corr:.1f} kg.", "quantity", r.quantity, corr)
        elif 0.75 < abs(lr) < 1.3:
            fac = 10 ** round(lr)
            corr = r.quantity * fac
            f.add("erp_purchase_lines", r.key, "decimal_shift", r.year, 0.85,
                  f"Unit price is {r.r:.2f}x the {r.material_id} median; decimal point shifted. Quantity {r.quantity} -> {corr:.1f}.",
                  "quantity", r.quantity, corr)
        elif abs(lr) >= 1.3:
            f.add("erp_purchase_lines", r.key, "outlier_implausible", r.year, 0.5,
                  f"Unit price {r.r:.1f}x material median; cause unknown -> expert review.", "quantity", r.quantity, None, True)

    # 5) spend lines (uom EUR): amount vs material/year median -> SEK keyed as EUR (x11.4) or decimal shift
    s = e[(e.uom == "EUR") & (e.movement_type == 101) & ~e.key.isin(flagged)].copy()
    s["ref"] = s.groupby(["material_id", s.wbs_element.fillna("-")]).net_amount.transform("median")
    s["r"] = s.net_amount / s.ref
    done = set()
    # capex lines: reconcile ERP spend per WBS element and year with the capex project register
    cp = raw["capex"].copy() if "capex" in raw else None
    if cp is not None:
        for (wbs, y), g in s[s.wbs_element.notna()].groupby(["wbs_element", "year"]):
            reg = cp[(cp.project == wbs) & (cp.year == y)].capex_eur.sum()
            if wbs.startswith("Maintenance"):
                reg = cp[(cp.site_id == "ALL") & (cp.year == y)].capex_eur.sum()
            tot = g.net_amount.sum()
            if reg > 0 and tot > 1.5 * reg:
                for _, r in g.iterrows():
                    alt = tot - r.net_amount + r.net_amount / FX["SEK"]
                    if abs(alt / reg - 1) < 0.1:
                        corr = r.net_amount / FX["SEK"]
                        done.add(r.key)
                        f.add("erp_purchase_lines", r.key, "currency_error", r.year, 0.8,
                              f"WBS '{wbs}' {y}: ERP spend {tot:,.0f} EUR vs capex register {reg:,.0f} EUR. Reading this line "
                              f"({r.net_amount:,.0f}) as SEK reconciles the project ({alt:,.0f}). Converted to {corr:,.0f} EUR.",
                              "net_amount", r.net_amount, corr)
    s = s[~s.key.isin(done)]
    for _, r in s.iterrows():
        if 7 < r.r < 18:
            corr = r.net_amount / FX["SEK"]
            done.add(r.key)
            f.add("erp_purchase_lines", r.key, "currency_error", r.year, 0.75,
                  f"Spend {r.net_amount:,.0f} is {r.r:.1f}x the {r.material_id} median; consistent with SEK booked as EUR "
                  f"(x{FX['SEK']}). Converted to {corr:,.0f} EUR.", "net_amount", r.net_amount, corr)
    return e


# ----------------------------------------------------------------------------- energy
def energy_checks(raw, f: Findings):
    em = raw["energy_meter"].copy()
    em["key"] = "energy:" + em.site_id + ":" + em.year.astype(str) + "-" + em.month.map("{:02d}".format) + ":" + em.carrier
    for (site, carrier), g in em.groupby(["site_id", "carrier"]):
        g = g.sort_values(["year", "month"])
        med_m = g.groupby("month").value.median()   # seasonal profile across years
        for _, r in g.iterrows():
            same_month = g[(g.month == r.month) & (g.year != r.year)].value
            ref = same_month.median() if len(same_month) >= 2 else g.value.median()
            yr = g[g.year == r.year].value
            yref = yr[yr != r.value].median() if len(yr) > 1 else ref
            if ref <= 0 or np.isnan(ref):
                continue
            ratio = r.value / ref
            if ratio > 300 and r.value / max(yref, 1e-9) > 300:
                corr = r.value / 1000
                f.add("energy_meter_readings", r.key, "unit_error", r.year, 0.95,
                      f"{r.value:,.0f} is {ratio:.0f}x the usual {carrier} reading for month {r.month}; kWh entered in MWh column. "
                      f"-> {corr:.3f} MWh.", "value", r.value, corr)
                if corr / ref > 2.6:
                    f.add("energy_meter_readings", r.key, "meter_spike", r.year, 0.6,
                          f"After kWh->MWh conversion the reading ({corr:,.1f} MWh) is still {corr / ref:.1f}x the same month "
                          f"in other years; also treated as a spike and re-estimated.", "value", corr, None, True)
            elif ratio > 2.6:
                # seasonal peak check: compare with the same month in other years
                f.add("energy_meter_readings", r.key, "meter_spike", r.year, 0.8,
                      f"{r.value:,.1f} MWh is {ratio:.1f}x the same month in other years (median {ref:,.1f}); meter spike. "
                      f"Replaced with same-month median scaled to the year level.", "value", r.value, None)
        # missing months
        for y, gy in g.groupby("year"):
            if len(gy) >= 9:   # partial years (start-up / shutdown) are legitimate, not gaps
                for m in sorted(set(range(1, 13)) - set(gy.month)):
                    f.add("energy_meter_readings", f"energy:{site}:{y}-{m:02d}:{carrier}", "missing_record", y, 0.9,
                          f"No {carrier} reading for {site} {y}-{m:02d} while {len(gy)} other months exist; gap-filled "
                          f"from the seasonal profile.", "value", None, None)
    return em


def fuel_checks(raw, f: Findings):
    fd = raw["fuel_deliveries"].copy()
    for (site, carrier), g in fd.groupby(["site_id", "carrier"]):
        med = g.quantity.median()
        for _, r in g.iterrows():
            if r.unit == "l" and med > 0 and r.quantity < med / 200:
                corr = r.quantity * 1000
                f.add("fuel_deliveries", f"fuel:{r.delivery_id}", "unit_error", r.year, 0.9,
                      f"{r.quantity} l is {med / r.quantity:.0f}x below the median {carrier} delivery ({med:,.0f} l); "
                      f"m3 keyed as litres -> {corr:,.0f} l.", "quantity", r.quantity, corr)
            elif r.unit == "t" and med > 0 and r.quantity > med * 200:
                corr = r.quantity / 1000
                f.add("fuel_deliveries", f"fuel:{r.delivery_id}", "unit_error", r.year, 0.9,
                      f"{r.quantity} t is far above the median; kg keyed as t -> {corr} t.", "quantity", r.quantity, corr)
    return fd


def refrigerant_checks(raw, f: Findings):
    rf = raw["refrigerants"].copy()
    # gas code consistency per system: a system's gas is its modal gas
    mode_gas = rf.groupby(["site_id", "system"]).refrigerant.agg(lambda s: s.value_counts().index[0])
    for _, r in rf.iterrows():
        mg = mode_gas[(r.site_id, r.system)]
        sys_lc = r.system.lower()
        if r.refrigerant != mg:
            f.add("refrigerant_service_log", f"refrigerant:{r.event_id}", "wrong_gas_code", r.year, 0.85,
                  f"System '{r.system}' at {r.site_id} is serviced with {mg} in all other events; this event says "
                  f"{r.refrigerant}. Recoded to {mg} (GWP {F.REFRIGERANT_GWP.get(mg)}).", "refrigerant", r.refrigerant, mg)
        med = rf[(rf.site_id == r.site_id) & (rf.system == r.system)].kg_added.median()
        if r.kg_added > 500 and r.kg_added > 50 * med:
            corr = r.kg_added / 1000
            f.add("refrigerant_service_log", f"refrigerant:{r.event_id}", "unit_error", r.year, 0.9,
                  f"{r.kg_added} kg added is {r.kg_added / med:.0f}x the system median ({med:.1f} kg); grams in kg column -> {corr} kg.",
                  "kg_added", r.kg_added, corr)
    return rf


def waste_checks(raw, f: Findings):
    w = raw["waste"].copy()
    for (site, stream), g in w.groupby(["site_id", "waste_stream"]):
        med = g.quantity.median()
        for _, r in g.iterrows():
            if med > 0 and r.quantity < med / 200:
                corr = r.quantity * 1000
                f.add("waste_transfer_notes", f"waste:{r.transfer_note}", "unit_error", r.year, 0.9,
                      f"{r.quantity} kg of {stream} is {med / r.quantity:.0f}x below the monthly median ({med:,.0f} kg); "
                      f"tonnes keyed as kg -> {corr:,.1f} kg.", "quantity", r.quantity, corr)
            elif med > 0 and r.quantity > med * 200:
                corr = r.quantity / 1000
                f.add("waste_transfer_notes", f"waste:{r.transfer_note}", "unit_error", r.year, 0.8,
                      f"{r.quantity} kg is {r.quantity / med:.0f}x above the monthly median; grams keyed as kg -> {corr}.",
                      "quantity", r.quantity, corr)
    return w


def goo_checks(raw, f: Findings):
    g = raw["goo"]
    reg = raw["goo_registry"].copy()
    reg["vintage"] = reg.production_period_start.str[:4].astype(int)
    for _, r in g.iterrows():
        rr = reg[(reg.consumption_year == r.year) & (reg.beneficiary_site == r.site_id)]
        if not len(rr):
            f.add("goo_cancellations", f"goo:{r.site_id}:{r.year}", "certificate_mismatch", r.year, 0.8,
                  "Internal GoO log entry has no matching cancellation in the national registry.", "mwh_cancelled", r.mwh_cancelled, 0)
            continue
        vint = sorted(rr.vintage.unique())
        mwh_reg = rr.mwh.sum()
        msg = []
        if r.vintage_year not in vint or len(vint) > 1:
            msg.append(f"log vintage {r.vintage_year} vs registry production period(s) {vint}")
        if abs(mwh_reg - r.mwh_cancelled) > 0.02 * max(mwh_reg, 1):
            msg.append(f"log {r.mwh_cancelled:,.0f} MWh vs registry {mwh_reg:,.0f} MWh")
        if msg:
            f.add("goo_cancellations", f"goo:{r.site_id}:{r.year}", "certificate_mismatch", r.year, 0.9,
                  "Internal GoO log disagrees with the authoritative registry statement: " + "; ".join(msg) +
                  ". Registry values used.", "vintage_year/mwh", f"{r.vintage_year}/{r.mwh_cancelled}", f"{vint}/{mwh_reg:.0f}")


def travel_checks(raw, f: Findings):
    t = raw["travel"]
    d = t[t.duplicated(["traveller_id", "travel_date", "route", "pkm", "nights"], keep="first")]
    for _, r in d.iterrows():
        f.add("travel_bookings", f"travel:{r.booking_id}", "duplicate_record", r.year, 0.95,
              f"Same traveller {r.traveller_id}, date {r.travel_date}, route {r.route}, {r.pkm} pkm, {r.nights} nights as an "
              f"earlier booking; re-imported row -> excluded.", "*", "row", "drop")


MODE_CANON = {"car": "car", "Car": "car", "auto": "car", "henkilöauto": "car", "linja-auto": "bus", "bus": "bus",
              "carpool": "carpool", "train": "train", "juna": "train", "bike_walk": "bike_walk", "ev_car": "ev_car",
              "pyörä": "bike_walk", "sähköauto": "ev_car", "kimppakyyti": "carpool"}


def commuting_checks(raw, f: Findings):
    c = raw["commuting"]
    for _, r in c.iterrows():
        canon = MODE_CANON.get(r["mode"], MODE_CANON.get(str(r["mode"]).strip().lower()))
        if r["mode"] not in ("car", "carpool", "bus", "train", "bike_walk", "ev_car"):
            f.add("commuting_survey", f"commute:{r.response_id}", "mode_mislabel", 2025, 0.85,
                  f"Mode '{r['mode']}' is not a canonical code; mapped to '{canon}'.", "mode", r["mode"], canon)
        if r.one_way_km > 150:
            corr = r.one_way_km / 1000
            f.add("commuting_survey", f"commute:{r.response_id}", "unit_error", 2025, 0.8,
                  f"One-way distance {r.one_way_km} km is implausible for a daily commute; metres entered as km -> {corr} km.",
                  "one_way_km", r.one_way_km, corr)


def shipment_checks(raw, f: Findings, erp_clean: pd.DataFrame | None = None):
    sh = raw["shipments"]
    ib = sh[sh.direction == "inbound"]
    e = raw["erp"] if erp_clean is None else erp_clean
    legs = ib.groupby("ref_doc").ef_id.apply(set)
    e = e[(e.movement_type == 101) & (e.uom != "EUR")].copy()
    e["legs"] = e.doc_no.map(legs)
    e = e[e.legs.notna()]
    sea = {"EF-TKM-SHIP-BULK", "EF-TKM-SHIP-REEFER", "EF-TKM-ROPAX"}
    # expected sea leg per material (modal across docs)
    exp = {}
    for m, g in e.groupby("material_id"):
        s = g.legs.apply(lambda x: next(iter(x & sea), None))
        vc = s.value_counts(dropna=False)
        top = vc.index[0]
        if top is not None and not (isinstance(top, float) and np.isnan(top)) and vc.iloc[0] / len(g) > 0.6:
            exp[m] = top
    stats = ib.groupby("ef_id").km.median()
    for _, r in e.iterrows():
        ef = exp.get(r.material_id)
        if ef and not (r.legs & sea):
            km = ib[(ib.ef_id == ef) & ib.ref_doc.isin(e[e.material_id == r.material_id].doc_no)].km.median()
            t_ = ib[ib.ref_doc == r.doc_no].t.max()
            f.add("shipments", f"ship:{r.doc_no}:{ef}", "missing_leg", int(r.posting_date[:4]), 0.85,
                  f"Import lot {r.doc_no} ({r.material_id}, origin {r.origin_country}) has only a road leg; all other lots of this "
                  f"material also have a {ef} leg. Imputed {t_:.1f} t x {km:,.0f} km = {t_ * km:,.0f} tkm.",
                  "tkm", None, float(t_ * km))


# ----------------------------------------------------------------------------- farming
def farm_checks(raw, f: Findings, soil_th=0.30):
    sv = raw["farm_survey"].copy()
    ch = raw["crop_history"]
    par = raw["parcels"]
    ch = ch.merge(par[["parcel_id", "area_ha", "soil_class_soilmap"]], on="parcel_id")
    ch["org"] = (ch.soil_class_soilmap == "organic") * ch.area_ha
    a = ch.groupby(["farm_id", "crop", "year"])[["org", "area_ha"]].sum()
    a["share"] = a.org / a.area_ha
    sv = sv.join(a.rename(columns={"area_ha": "parcel_area"}), on=["farm_id", "crop", "year"])
    norms = {c: v["n"] for c, v in F.MGMT_NORMS.items()}
    med_y = sv.groupby("crop").yield_t_ha.transform("median")
    farm_org = sv.groupby("farm_id").soil_type_reported.apply(lambda s: (s == "Organic soil").any())
    for _, r in sv.iterrows():
        key = f"farm_survey:{r.survey_id}"
        if pd.notna(r.parcel_area) and r.parcel_area > 0 and abs(r.area_ha / r.parcel_area - 1) > 0.05:
            f.add("farm_survey", key, "area_mismatch", r.year, 0.9,
                  f"Reported {r.area_ha} ha of {r.crop}, but the parcel register's declared {r.crop} parcels sum to "
                  f"{r.parcel_area:.2f} ha ({r.area_ha / r.parcel_area:.2f}x). Register area used.", "area_ha", r.area_ha, round(r.parcel_area, 2))
        if r.yield_t_ha > 3 * med_y[_] or r.yield_t_ha < med_y[_] / 6:
            fac = 0.1 if r.yield_t_ha > 3 * med_y[_] else 10
            f.add("farm_survey", key, "outlier_implausible", r.year, 0.85,
                  f"Yield {r.yield_t_ha} t/ha is {r.yield_t_ha / med_y[_]:.1f}x the {r.crop} median ({med_y[_]:.2f}); "
                  f"likely decimal slip -> {r.yield_t_ha * fac:.2f}. Expert to confirm.", "yield_t_ha", r.yield_t_ha,
                  round(r.yield_t_ha * fac, 3), True)
        nm = norms.get(r.crop, 0)
        if nm >= 20 and pd.notna(r.n_mineral_kg_ha) and r.n_mineral_kg_ha > 0:
            ratio = r.n_mineral_kg_ha / nm
            if ratio > 5 or ratio < 0.15:
                fac = 0.1 if ratio > 5 else 10
                f.add("farm_survey", key, "decimal_shift", r.year, 0.8,
                      f"Mineral N {r.n_mineral_kg_ha} kg/ha is {ratio:.2f}x the {r.crop} norm ({nm}); decimal shift -> "
                      f"{r.n_mineral_kg_ha * fac:.1f}.", "n_mineral_kg_ha", r.n_mineral_kg_ha, round(r.n_mineral_kg_ha * fac, 2))
        if r.soil_type_reported == "Mineral soil" and pd.notna(r.share) and r.share >= soil_th:
            f.add("farm_survey", key, "soil_misreport", r.year, round(min(0.95, 0.5 + r.share / 2), 2),
                  f"Survey says 'Mineral soil', but {r.share:.0%} of the farm's {r.crop} area in {r.year} lies on organic soil "
                  f"in the soil map (88 % accurate). Drained organic soil adds ~29 t CO2/ha/yr. Expert to confirm with farmer.",
                  "soil_type_reported", "Mineral soil", f"organic share {r.share:.2f}", True)
    return sv


def registry_checks(raw, f: Findings):
    fr = raw["farm_registry"]
    box = {"FI_SW": ((59.5, 63.5), (19.0, 26.0)), "SE_SKANE": ((55.0, 57.5), (11.5, 15.0))}
    for _, r in fr.iterrows():
        (la, lo) = box[r.region]
        if not (la[0] <= r.lat <= la[1] and lo[0] <= r.lon <= lo[1]):
            swapped = la[0] <= r.lon <= la[1] and lo[0] <= r.lat <= lo[1]
            f.add("farm_registry", f"farm:{r.farm_id}", "coordinate_swap" if swapped else "outlier_implausible", 2025, 0.9,
                  f"Farm centre ({r.lat}, {r.lon}) lies outside the {r.region} sourcing area; latitude and longitude swapped.",
                  "lat/lon", f"{r.lat}/{r.lon}", f"{r.lon}/{r.lat}")


def pcf_checks(raw, f: Findings):
    p = raw["pcfs"].copy()
    ef = raw["ef_library"].set_index("ef_id").kgco2e_per_unit
    mats = raw["materials"].set_index("material_id")
    for _, r in p.iterrows():
        key = f"pcf:{r.supplier_id}:{r.material_id}:{r.year}"
        dflt = ef.get(mats.loc[r.material_id, "default_ef_id"], np.nan)
        if r.value > 50 or (pd.notna(dflt) and r.value > 100 * dflt):
            f.add("supplier_pcfs", key, "pcf_unit_error", r.year, 0.95,
                  f"PCF {r.value} declared per '{r.declared_unit}' is ~1000x the material default ({dflt}); value is per tonne. "
                  f"PCF rejected (not per declared unit); default factor used. Ask supplier to reissue.", "pCfExcludingBiogenic",
                  r.value, None, True)
        ys, ye = int(r.ref_start[:4]), r.ref_end
        if not (r.ref_start <= f"{r.year}-01-01" and r.ref_end >= f"{r.year}-12-31"):
            f.add("supplier_pcfs", key, "pcf_stale_period", r.year, 0.95,
                  f"PCF filed for {r.year} covers reference period {r.ref_start}..{r.ref_end}; it does not cover {r.year}. "
                  f"Rejected; default factor used. Request an updated PCF.", "referencePeriod", f"{r.ref_start}..{r.ref_end}", None, True)


def report_checks(raw, f: Findings):
    d = raw["draft_report"].set_index("line").tco2e
    for y, g in raw["draft_report"].groupby("year"):
        dd = g.set_index("line").tco2e
        if {"scope1", "scope2_market", "scope3", "total_market_based"} <= set(dd.index):
            s = dd.scope1 + dd.scope2_market + dd.scope3
            if abs(s - dd.total_market_based) > 0.005 * s:
                f.add("draft_report_summary", f"report:{y}:total_market_based", "total_mismatch", y, 0.95,
                      f"Total {dd.total_market_based:,.0f} != scope1+scope2_market+scope3 = {s:,.0f}. "
                      f"Replace draft with the pipeline inventory.", "tco2e", dd.total_market_based, s, True)


def detect(raw) -> pd.DataFrame:
    f = Findings()
    erp_checks(raw, f)
    energy_checks(raw, f)
    fuel_checks(raw, f)
    refrigerant_checks(raw, f)
    waste_checks(raw, f)
    goo_checks(raw, f)
    travel_checks(raw, f)
    commuting_checks(raw, f)
    shipment_checks(raw, f)
    farm_checks(raw, f)
    registry_checks(raw, f)
    pcf_checks(raw, f)
    report_checks(raw, f)
    return f.df()


def submission(findings: pd.DataFrame, years=None) -> pd.DataFrame:
    s = findings.sort_values("confidence", ascending=False).drop_duplicates("record_key")
    if years is not None:
        s = s[s.year.isin(years)]
    return s[["table", "record_key", "issue_type", "confidence", "explanation", "year"]]
