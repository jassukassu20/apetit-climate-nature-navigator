"""Apply DQ-agent corrections to the raw feeds and build canonical clean tables
for the reference calculator. Every applied correction is written to the corrections log."""
from __future__ import annotations

import sys
sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/A")

import numpy as np
import pandas as pd

import dq_agent as DQ
from ccn_tools import factors as F
from ccn_tools import io as IO
from ccn_tools.farm_calculator import farm_footprint_per_ha

CROP_MAT = {"M100": "turnip_rape", "M110": "pea", "M111": "potato", "M112": "carrot", "M113": "spinach"}


def _fmap(fnd, table, itype=None):
    d = fnd[fnd.table == table]
    if itype:
        d = d[d.issue_type == itype]
    return d


def clean_erp(raw, fnd):
    e = raw["erp"].copy()
    e["key"] = "erp:" + e.doc_no + ":" + e.line_no.astype(str)
    e["year"] = e.posting_date.str[:4].astype(int)
    f = _fmap(fnd, "erp_purchase_lines")
    drop = set(f[f.issue_type == "duplicate_record"].record_key)
    e = e[~e.key.isin(drop)].copy()
    for _, r in f[f.issue_type == "material_mismatch"].iterrows():
        e.loc[e.key == r.record_key, "material_id"] = r.corrected_value
    for _, r in f[f.issue_type.isin(["unit_error", "decimal_shift"])].iterrows():
        e.loc[e.key == r.record_key, "quantity"] = float(r.corrected_value)
    for _, r in f[f.issue_type == "currency_error"].iterrows():
        if r.field == "currency":
            e.loc[e.key == r.record_key, "currency"] = r.corrected_value
        else:
            e.loc[e.key == r.record_key, "net_amount"] = float(r.corrected_value)
    e["qty_kg"] = np.where(e.uom == "TO", e.quantity * 1000, np.where(e.uom == "KG", e.quantity, 0.0))
    e["amount_eur"] = e.net_amount / e.currency.map(F.FX_PER_EUR).fillna(1.0)
    return e


def clean_energy(raw, fnd):
    em = raw["energy_meter"].copy()
    em["key"] = "energy:" + em.site_id + ":" + em.year.astype(str) + "-" + em.month.map("{:02d}".format) + ":" + em.carrier
    f = _fmap(fnd, "energy_meter_readings")
    for _, r in f[f.issue_type == "unit_error"].iterrows():
        em.loc[em.key == r.record_key, "value"] = float(r.corrected_value)
    spikes = set(f[f.issue_type == "meter_spike"].record_key)
    # spikes and gaps: estimate from same-month share of the annual profile in clean years
    em["bad"] = em.key.isin(spikes)
    miss = f[f.issue_type == "missing_record"]
    add = []
    for _, r in miss.iterrows():
        _, site, ym, carrier = r.record_key.split(":")
        y, m = int(ym[:4]), int(ym[5:])
        add.append(dict(site_id=site, year=y, month=m, carrier=carrier, value=np.nan, unit="MWh", key=r.record_key, bad=True))
    em = pd.concat([em, pd.DataFrame(add)], ignore_index=True)
    for i, r in em[em.bad].iterrows():
        g = em[(em.site_id == r.site_id) & (em.carrier == r.carrier) & ~em.bad]
        yr = g[g.year == r.year]
        ests = []
        for y2, g2 in g[g.year != r.year].groupby("year"):
            g2 = g2.set_index("month").value
            common = [m for m in yr.month if m in g2.index]
            if r.month in g2.index and len(common) >= 6:
                ests.append(g2[r.month] / g2[common].sum() * yr.set_index("month").value[common].sum())
        est = float(np.median(ests)) if ests else yr.value.median()
        em.loc[i, "value"] = est
        em.loc[i, "est"] = est
    em["mwh"] = np.where(em.unit == "kWh", em.value / 1000, em.value)
    fd = raw["fuel_deliveries"].copy()
    ff = _fmap(fnd, "fuel_deliveries")
    for _, r in ff.iterrows():
        fd.loc["fuel:" + fd.delivery_id == r.record_key, "quantity"] = float(r.corrected_value)
    ncv = {"lng": F.NCV["lng_t"], "lpg": F.NCV["lpg_t"], "light_fuel_oil": F.NCV["lfo_l"], "diesel": F.NCV["diesel_l"]}
    fdy = fd.groupby(["site_id", "carrier", "year"]).quantity.sum().reset_index()
    fdy = fdy.merge(raw["fuel_stock"][["site_id", "carrier", "year", "stock_change"]], on=["site_id", "carrier", "year"], how="left").fillna({"stock_change": 0})
    fdy["mwh"] = (fdy.quantity - fdy.stock_change) * fdy.carrier.map(ncv)
    fdy["month"] = 0
    return pd.concat([em[["site_id", "year", "month", "carrier", "mwh"]], fdy[["site_id", "year", "month", "carrier", "mwh"]]], ignore_index=True), em


def reconcile_estimates_to_goo(energy, meter, goo):
    """Sites buy GoOs for 100 % of consumption. Where a site total contains *estimated* months and exceeds the
    registry GoO volume by less than 10 % of the estimated MWh, the gap is estimation error, not uncovered
    consumption: estimated months are scaled so the total equals the GoO volume. Logged for expert review."""
    log = []
    en = energy.copy()
    est = meter[meter.get("est").notna()] if "est" in meter else meter.iloc[:0]
    for (site, y), g in est[est.carrier == "electricity"].groupby(["site_id", "year"]):
        gv = goo[(goo.site_id == site) & (goo.year == y) & (goo.vintage_year == y)].mwh_cancelled.sum()
        m = (en.site_id == site) & (en.year == y) & (en.carrier == "electricity")
        tot = en[m].mwh.sum()
        e_mwh = g.est.sum()
        if gv > 0 and 0 < tot - gv < 0.1 * e_mwh:
            fac = (e_mwh - (tot - gv)) / e_mwh
            for mo in g.month:
                mm = m & (en.month == mo)
                en.loc[mm, "mwh"] *= fac
            log.append(dict(site_id=site, year=y, estimated_mwh=e_mwh, gap_mwh=tot - gv, factor=fac))
    return en, pd.DataFrame(log)


def clean_refrigerants(raw, fnd):
    rf = raw["refrigerants"].copy()
    f = _fmap(fnd, "refrigerant_service_log")
    for _, r in f.iterrows():
        m = "refrigerant:" + rf.event_id == r.record_key
        if r.issue_type == "wrong_gas_code":
            rf.loc[m, "refrigerant"] = r.corrected_value
        else:
            rf.loc[m, "kg_added"] = float(r.corrected_value)
    return rf[["site_id", "year", "refrigerant", "kg_added"]]


def clean_goo(raw, energy):
    reg = raw["goo_registry"].copy()
    reg["vintage_year"] = reg.production_period_start.str[:4].astype(int)
    g = reg.rename(columns={"consumption_year": "year", "beneficiary_site": "site_id", "mwh": "mwh_cancelled"})
    g = g.groupby(["year", "site_id", "vintage_year"]).mwh_cancelled.sum().reset_index()
    return g


def clean_waste(raw, fnd):
    w = raw["waste"].copy()
    for _, r in _fmap(fnd, "waste_transfer_notes").iterrows():
        w.loc["waste:" + w.transfer_note == r.record_key, "quantity"] = float(r.corrected_value)
    w["t"] = w.quantity / 1000
    efmap = {"anaerobic_digestion": "EF-WASTE-BIO-AD", "composting": "EF-WASTE-BIO-COMPOST", "incineration": "EF-WASTE-MIXED-INC",
             "recycling": "EF-WASTE-RECYCLE", "landfill_codigestion": "EF-WASTE-SPENTEARTH"}
    w["ef_id"] = w.treatment.map(efmap)
    w.loc[w.waste_stream == "plastic_waste", "ef_id"] = "EF-WASTE-PLASTIC-INC"
    return w


def clean_travel(raw, fnd):
    t = raw["travel"]
    drop = set(_fmap(fnd, "travel_bookings").record_key)
    return t[~("travel:" + t.booking_id).isin(drop)]


def clean_commuting(raw, fnd):
    c = raw["commuting"].copy()
    for _, r in _fmap(fnd, "commuting_survey").iterrows():
        m = "commute:" + c.response_id == r.record_key
        if r.issue_type == "mode_mislabel":
            c.loc[m, "mode"] = r.corrected_value
        else:
            c.loc[m, "one_way_km"] = float(r.corrected_value)
    return c


def clean_shipments(raw, fnd):
    sh = raw["shipments"].copy()
    add = []
    for _, r in _fmap(fnd, "shipments").iterrows():
        _, doc, ef = r.record_key.split(":")
        add.append(dict(shipment_id="IMPUTED", year=int(r.year), direction="inbound", ref_doc=doc, ef_id=ef, tkm=float(r.corrected_value)))
    return pd.concat([sh, pd.DataFrame(add)], ignore_index=True)


def clean_pcfs(raw, fnd):
    p = raw["pcfs"].copy()
    p["key"] = "pcf:" + p.supplier_id + ":" + p.material_id + ":" + p.year.astype(str)
    bad = set(_fmap(fnd, "supplier_pcfs").record_key)
    p = p[~p.key.isin(bad)]
    return p.rename(columns={"value": "kgco2e_per_kg"})[["year", "supplier_id", "material_id", "kgco2e_per_kg"]]


# ----------------------------------------------------------------------------- farms
def farm_inputs(raw, fnd):
    """Clean survey: area from register, decimal fixes, organic-soil share from soil map."""
    sv = raw["farm_survey"].copy()
    sv["key"] = "farm_survey:" + sv.survey_id
    f = _fmap(fnd, "farm_survey")
    for _, r in f[f.issue_type.isin(["decimal_shift", "outlier_implausible", "area_mismatch"])].iterrows():
        sv.loc[sv.key == r.record_key, r.field] = float(r.corrected_value)
    ch = raw["crop_history"].merge(raw["parcels"][["parcel_id", "area_ha", "soil_class_soilmap"]], on="parcel_id")
    ch["org"] = (ch.soil_class_soilmap == "organic") * ch.area_ha
    a = ch.groupby(["farm_id", "crop", "year"])[["org", "area_ha"]].sum()
    a["org_share"] = a.org / a.area_ha
    sv = sv.join(a[["org_share"]], on=["farm_id", "crop", "year"])
    sv["org_share"] = np.where(sv.soil_type_reported == "Organic soil", np.maximum(sv.org_share.fillna(1), 0.0), sv.org_share.fillna(0))
    return sv, a


def footprint_components(df):
    """Per-ha components (kg CO2e/ha), split FLAG / non-FLAG, with organic soil as a share."""
    base = df.copy()
    base["organic_soil"] = False
    tot_min = farm_footprint_per_ha(base)
    org = base.copy(); org["organic_soil"] = True
    tot_org = farm_footprint_per_ha(org)
    org_add = tot_org - tot_min
    E = F.FARM_EF
    n2o = E["n2o_n_to_n2o"] * E["n2o_gwp"]
    nmin = base.n_mineral_kg_ha.fillna(0).values; nman = base.n_manure_kg_ha.fillna(0).values
    res_n = base.crop.map(F.RESIDUE_N_PER_T).values * base.yield_t_ha.values
    c_dir = (nmin * E["ef1_synthetic"] + (nman + res_n) * E["ef1_organic"]) * n2o
    c_ind = ((nmin * E["frac_gasf"] + nman * E["frac_gasm"]) * E["ef4_n2o_n"] + (nmin + nman + res_n) * E["frac_leach"] * E["ef5_n2o_n"]) * n2o
    c_lime = base.lime_t_ha.fillna(0).values * E["lime"] * 1000
    share = base.org_share.values if "org_share" in base else 0
    flag = c_dir + c_ind + c_lime + share * org_add
    nonflag = tot_min - (c_dir + c_ind + c_lime)
    return flag, nonflag, share * org_add


ORG_SCALE = 1.17   # calibrated on 2023-2024 verified inventories (see SUMMARY.md)


def farm_footprints(raw, fnd, erp, org_scale=None):
    org_scale = ORG_SCALE if org_scale is None else org_scale
    sv, area = farm_inputs(raw, fnd)
    flag, nonflag, orgc = footprint_components(sv)
    sv["kg_ha"] = flag + nonflag
    sv["kg_ha_flag"] = flag
    sv["kg_ha_org"] = orgc
    sv["kg_per_kg"] = sv.kg_ha / (sv.yield_t_ha * 1000)
    sv["flag_per_kg"] = sv.kg_ha_flag / (sv.yield_t_ha * 1000)
    d = erp[erp.material_id.isin(CROP_MAT) & erp.supplier_id.str.startswith("F")].copy()
    d["crop"] = d.material_id.map(CROP_MAT)
    d = d.groupby(["supplier_id", "crop", "year"]).qty_kg.sum().reset_index().rename(columns={"supplier_id": "farm_id"})
    d = d.merge(sv[["farm_id", "crop", "year", "kg_per_kg", "flag_per_kg", "org_share", "kg_ha", "yield_t_ha", "area_ha"]],
                on=["farm_id", "crop", "year"], how="left")
    d["source"] = np.where(d.kg_per_kg.notna(), "survey", "imputed")
    # non-respondents: crop-year median for mineral-soil part + organic share from the soil map
    min_sv = sv.copy(); min_sv["org_share"] = 0
    fl0, nf0, _ = footprint_components(min_sv)
    sv["kgkg_min"] = (fl0 + nf0) / (sv.yield_t_ha * 1000)
    sv["flagkg_min"] = fl0 / (sv.yield_t_ha * 1000)
    med = sv.groupby(["crop", "year"])[["kgkg_min", "flagkg_min", "yield_t_ha"]].median()
    imp = d.kg_per_kg.isna()
    m = med.reindex(list(zip(d.crop, d.year)))
    sh = area.org_share.reindex(list(zip(d.farm_id, d.crop, d.year))).fillna(0).values
    org_ha = (F.FARM_EF["org_soil_co2_t_ha"] * 1000 + F.FARM_EF["org_soil_n2o_n_kg_ha"] * F.FARM_EF["n2o_n_to_n2o"] * F.FARM_EF["n2o_gwp"])
    org_kg = sh * org_ha / (m.yield_t_ha.values * 1000)
    d.loc[imp, "kg_per_kg"] = m.kgkg_min.values[imp] + org_kg[imp]
    d.loc[imp, "flag_per_kg"] = m.flagkg_min.values[imp] + org_kg[imp]
    d.loc[imp, "org_share"] = sh[imp]
    # soil-map recall calibration: the 88 %-accurate map misses organic fields; scale the organic-soil
    # term of mineral-reported rows by a factor calibrated on the verified 2023-2024 inventories
    rep = d[["farm_id", "crop", "year"]].merge(sv[["farm_id", "crop", "year", "soil_type_reported"]], how="left")
    mineral = (rep.soil_type_reported != "Organic soil").values
    yld = d.yield_t_ha.fillna(pd.Series(list(zip(d.crop, d.year))).map(med.yield_t_ha)).values
    org_term = d.org_share.values * org_ha / (yld * 1000)
    d["org_kg_per_kg"] = org_term * np.where(mineral, org_scale, 1.0)
    d["kg_per_kg"] = d.kg_per_kg + np.where(mineral, (org_scale - 1) * org_term, 0)
    d["flag_per_kg"] = d.flag_per_kg + np.where(mineral, (org_scale - 1) * org_term, 0)
    d["tco2e"] = d.qty_kg * d.kg_per_kg / 1000
    d["tco2e_org"] = d.qty_kg * d.org_kg_per_kg / 1000
    d["tco2e_flag"] = d.qty_kg * d.flag_per_kg / 1000
    d["region"] = "FI_SW"
    return d


def canonical(raw, fnd):
    T = {k: raw[k] for k in ("sites", "materials", "ef_library", "heat_suppliers", "headcount", "warehousing", "wastewater")}
    erp = clean_erp(raw, fnd)
    T["purchases"] = erp
    T["energy"], T["_meter"] = clean_energy(raw, fnd)
    T["refrigerants"] = clean_refrigerants(raw, fnd)
    T["goo"] = clean_goo(raw, T["energy"])
    T["energy"], T["_recon"] = reconcile_estimates_to_goo(T["energy"], T["_meter"], T["goo"])
    T["waste"] = clean_waste(raw, fnd)
    T["travel"] = clean_travel(raw, fnd)
    T["commuting_survey"] = clean_commuting(raw, fnd)
    T["shipments"] = clean_shipments(raw, fnd)
    T["sales"] = raw["sales"]
    T["pcf_used"] = clean_pcfs(raw, fnd)
    T["farm_footprints"] = farm_footprints(raw, fnd, erp)
    return T
