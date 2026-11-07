"""C3: translate climate yield risk into EUR and t CO2e, and value adaptation options.

Method (all assumptions logged in c3_assumptions.csv):
  * contracted volume = expected production of the 2025 contract-parcel mix under 1991-2020 climate (model, tech frozen 2025)
  * annual shortfall_t = max(0, contracted - simulated production)  (surpluses are not monetised)
  * extra cost = shortfall_t x contract price 2026 x replacement-import premium  (contract_prices_and_replacement_premiums.csv)
  * extra emissions = shortfall_t x (import factor + import transport - domestic farm-gate factor - domestic processing)
  * 1-in-10 loss = 90th percentile of annual extra cost over the 20-year window
"""
import sys; sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/C")
import numpy as np
import pandas as pd
import model as M
import features as FE
from predict import management_table, attach_mgmt

ROOT, OUT = M.ROOT, M.OUT
price = pd.read_csv(ROOT / "05_scenarios/contract_prices_and_replacement_premiums.csv")
p26 = price[price.year == 2026].set_index("item")
EF = pd.read_csv(ROOT / "01_master/emission_factor_library.csv").set_index("ef_id").kgco2e_per_unit

# ---- assumptions (kg CO2e / kg product) ----
TRUCK_R, ROPAX, TRUCK, SHIP = EF["EF-TKM-TRUCK-REEFER"], EF["EF-TKM-ROPAX"], EF["EF-TKM-TRUCK"], EF["EF-TKM-SHIP-BULK"]
veg_import = EF["EF-FROZ-CAUL-NL"] + (1600 * TRUCK_R + 300 * ROPAX) / 1000  # frozen veg from NL/BE (proxy), reefer road + Ro-Pax
DOM_PROC = 0.05  # domestic freezing avoided when importing a frozen product (assumption; Apetit S1+S2 are low)
dom = {"pea": EF["EF-VEG-PEA-FI"], "potato": EF["EF-VEG-POT-FI"], "carrot": EF["EF-VEG-CAR-FI"], "spinach": EF["EF-VEG-SPI-FI"],
       "turnip_rape": EF["EF-RAP-FI"], "pea_SE": EF["EF-VEG-PEA-SE"]}
imp = {"pea": veg_import, "potato": veg_import, "carrot": veg_import, "spinach": veg_import, "pea_SE": veg_import,
       "turnip_rape": EF["EF-RAP-LT"] + (700 * SHIP + 200 * TRUCK) / 1000}
d_ef = {k: imp[k] - dom[k] - (DOM_PROC if k != "turnip_rape" else 0) for k in imp}
assump = pd.DataFrame([
    ("contracted volume", "expected production, 2025 parcel mix, 1991-2020 climate, technology/management frozen at 2025", "model"),
    ("price", "contract_price_eur_t 2026 per crop (pea_SE for Sweden)", "contract_prices_and_replacement_premiums.csv"),
    ("premium", "replacement_import_premium_frac 2026", "contract_prices_and_replacement_premiums.csv"),
    ("veg import factor", f"{veg_import:.3f} kg/kg = EF-FROZ-CAUL-NL proxy + 1600 km reefer truck + 300 km Ro-Pax", "emission_factor_library.csv"),
    ("rapeseed import factor", f"{imp['turnip_rape']:.3f} kg/kg = EF-RAP-LT + 700 km bulk ship + 200 km truck", "emission_factor_library.csv"),
    ("domestic processing avoided", f"{DOM_PROC} kg/kg for frozen veg (assumption)", "assumption"),
    ("irrigation cost", "EUR 250 /ha/yr annualised (equipment, water, energy) - assumption to be replaced by Apetit agronomy data; cf. lever L24", "assumption / decarbonisation_levers.csv L24"),
    ("surplus", "surplus years not monetised (conservative); shortfall of one region may be covered by the other in the hedge case", "assumption"),
], columns=["item", "value", "source"])
assump.to_csv(OUT / "c3_assumptions.csv", index=False)


def item(region, crop):
    return "pea_SE" if region == "SE_SKANE" else crop


def risk_table(sim, label="baseline"):
    sim = sim.copy(); sim["prod"] = sim.y * sim.area_ha
    reg = sim.groupby(["region", "crop", "scenario", "year"]).agg(prod=("prod", "sum"), area=("area_ha", "sum")).reset_index()
    return reg


def euro(reg, contracted):
    r = reg.merge(contracted, on=["region", "crop"])
    r["item"] = [item(a, b) for a, b in zip(r.region, r.crop)]
    r["price"] = r["item"].map(p26.contract_price_eur_t); r["prem"] = r["item"].map(p26.replacement_import_premium_frac)
    r["shortfall_t"] = (r.contracted_t - r["prod"]).clip(lower=0)
    r["extra_cost_eur"] = r.shortfall_t * r.price * r.prem
    r["replacement_spend_eur"] = r.shortfall_t * r.price * (1 + r.prem)
    r["extra_tco2e"] = r.shortfall_t * r["item"].map(d_ef)
    r["prod_value_eur"] = r["prod"] * r.price
    return r


def window(r):
    r = r.copy()
    r["period"] = np.select([(r.scenario == "historical") & r.year.between(1991, 2020), r.year.between(2041, 2060)],
                            ["1991-2020", "2041-2060"], "other")
    r = r[r.period != "other"]
    g = r.groupby(["region", "crop", "scenario", "period"])
    return g.agg(contracted_t=("contracted_t", "first"), mean_prod_t=("prod", "mean"),
                 exp_shortfall_t=("shortfall_t", "mean"), exp_extra_cost_eur=("extra_cost_eur", "mean"),
                 p90_extra_cost_eur=("extra_cost_eur", lambda x: np.quantile(x, 0.9)),
                 worst_year_extra_cost_eur=("extra_cost_eur", "max"),
                 exp_replacement_spend_eur=("replacement_spend_eur", "mean"), exp_extra_tco2e=("extra_tco2e", "mean"),
                 mean_prod_value_eur=("prod_value_eur", "mean")).reset_index()


def main():
    sim = pd.read_parquet(OUT / "sim_2025mix.parquet")
    reg = risk_table(sim)
    contracted = reg[(reg.scenario == "historical") & reg.year.between(1991, 2020)].groupby(["region", "crop"])["prod"].mean().rename("contracted_t").reset_index()
    r = euro(reg, contracted)
    w = window(r)
    w = w[~((w.scenario != "historical") & (w.period == "1991-2020"))]
    num = [c for c in w.columns if c.endswith(("_t", "_eur", "_tco2e"))]
    w[num] = w[num].round(0)
    w.to_csv(OUT / "c3_euro_risk.csv", index=False)
    print(w.to_string())

    # ---------- hedge: FI vs SE peas ----------
    pe = r[(r.crop == "pea")].pivot_table(index=["scenario", "year"], columns="region", values="prod").dropna()
    hist = pe.loc["historical"]
    an = hist / hist.loc[1991:2020].mean() - 1
    corr_sim = float(an.corr().iloc[0, 1])
    obs = pd.read_parquet(OUT / "training.parquet"); obs = obs[obs.crop == "pea"]
    oy = obs.groupby(["region", "year"]).yield_t_ha.mean().unstack(0).dropna()
    corr_obs = float((oy / oy.mean() - 1).corr().iloc[0, 1])
    c2026 = (oy.loc[2026] / oy.drop(2026).mean() - 1).round(3).to_dict()
    hedge = []
    for scen, yrs in [("historical", range(1991, 2021)), ("ssp245", range(2041, 2061)), ("ssp585", range(2041, 2061))]:
        x = pe.loc[scen].loc[list(yrs)]
        cfi, cse = contracted.set_index(["region", "crop"]).contracted_t[("FI_SW", "pea")], contracted.set_index(["region", "crop"]).contracted_t[("SE_SKANE", "pea")]
        pr = p26.contract_price_eur_t["pea"]; pm = p26.replacement_import_premium_frac["pea"]
        sep = ((cfi - x.FI_SW).clip(lower=0) + (cse - x.SE_SKANE).clip(lower=0)) * pr * pm
        pooled = ((cfi + cse) - (x.FI_SW + x.SE_SKANE)).clip(lower=0) * pr * pm
        # single-region counterfactual: same total contracted volume, all from FI (scaled FI anomaly)
        fi_only = ((cfi + cse) - x.FI_SW * (cfi + cse) / cfi).clip(lower=0) * pr * pm
        se_only = ((cfi + cse) - x.SE_SKANE * (cfi + cse) / cse).clip(lower=0) * pr * pm
        hedge.append(dict(scenario=scen, window=f"{min(yrs)}-{max(yrs)}", corr_FI_SE_sim=round(float((x / x.mean() - 1).corr().iloc[0, 1]), 3),
                          exp_cost_fi_only_eur=round(fi_only.mean()), exp_cost_se_only_eur=round(se_only.mean()),
                          exp_cost_two_regions_pooled_eur=round(pooled.mean()), exp_cost_two_regions_separate_eur=round(sep.mean()),
                          p90_fi_only_eur=round(np.quantile(fi_only, .9)), p90_two_regions_pooled_eur=round(np.quantile(pooled, .9))))
    hedge = pd.DataFrame(hedge)
    hedge.to_csv(OUT / "c3_hedge_fi_se.csv", index=False)
    print("corr sim 1991-2026", round(corr_sim, 3), "corr observed 2018-2026", round(corr_obs, 3), "2026 anomaly", c2026)
    print(hedge.to_string())

    # ---------- adaptation options (2041-2060, ssp245 & ssp585) ----------
    parcels = M.load_static()
    feats = pd.read_parquet(OUT / "features.parquet")
    d = pd.read_parquet(OUT / "training.parquet")
    model = M.YieldModel().fit(d)
    last, cmed = management_table(d)
    ch = pd.read_csv(ROOT / "03_farming/parcel_crop_history_and_plan.csv")
    mix = ch[(ch.year == 2025) & ch.crop.isin(M.CROPS5)][["parcel_id", "crop"]]

    # earlier sowing: recompute features with sowing threshold lowered by 1.5 C (earlier drilling, cold-tolerant seed)
    w = pd.read_parquet(ROOT / "04_climate/weather_daily_1991_2060.parquet")
    w["date"] = pd.to_datetime(w.date); w["year"] = w.date.dt.year; w["doy"] = w.date.dt.dayofyear - 1
    w = w[w.year.between(2041, 2060) & w.scenario.isin(["ssp245", "ssp585"]) & (w.doy < 365)]
    orig = {c: dict(v) for c, v in FE.CROPS.items()}
    for c in FE.CROPS: FE.CROPS[c]["sow_t"] -= 1.5
    early = []
    for (scen, yr), g in w.groupby(["scenario", "year"]):
        cells = np.sort(g.cell_id.unique())
        pv = {v: g.pivot(index="cell_id", columns="doy", values=v).loc[cells].to_numpy(float) for v in ("tmean_c", "tmax_c", "precip_mm", "pet_mm")}
        for (crop, s), rr in FE.year_features(pv["tmean_c"], pv["tmax_c"], pv["precip_mm"], pv["pet_mm"], None).items():
            df = pd.DataFrame({kk: (vv if np.ndim(vv) else [vv] * len(cells)) for kk, vv in rr.items()})
            df["cell_id"] = cells; df["scenario"] = scen; df["year"] = yr; early.append(df)
    FE.CROPS.update(orig)
    early = pd.concat(early, ignore_index=True)

    kk = mix.assign(key=1).merge(pd.DataFrame({"year": range(2041, 2061), "key": 1}), on="key").drop(columns="key")
    kk = pd.concat([kk.assign(scenario=s) for s in ("ssp245", "ssp585")], ignore_index=True)
    base = attach_mgmt(M.parcel_features(parcels, feats, kk), last, cmed)
    opts = {"no_adaptation": base}
    irr = base.copy(); can = irr.crop.isin(["potato", "carrot", "spinach"]) | ((irr.crop == "pea") & (irr.region == "SE_SKANE"))
    irr.loc[can, "irrigated"] = 1.0; opts["irrigation_all_vegetable_parcels"] = irr
    heat = base.copy(); heat["hot_flw"] *= 0.5; heat["hot25_flw"] *= 0.5; heat["tmax_flw"] -= 0.5
    opts["heat_tolerant_variety"] = heat
    opts["earlier_sowing_-1.5C_threshold"] = attach_mgmt(M.parcel_features(parcels, early, kk), last, cmed)
    res = []
    for name, df in opts.items():
        df = df.copy(); df["y"] = model.predict(df, year_for_trend=2025)
        rr = euro(risk_table(df), contracted)
        g = rr.groupby(["region", "crop", "scenario"]).agg(mean_prod_t=("prod", "mean"), exp_extra_cost_eur=("extra_cost_eur", "mean"),
                                                           p90_extra_cost_eur=("extra_cost_eur", lambda x: np.quantile(x, .9)),
                                                           mean_prod_value_eur=("prod_value_eur", "mean"), exp_extra_tco2e=("extra_tco2e", "mean"),
                                                           area_ha=("area", "first")).reset_index()
        g["option"] = name; res.append(g)
    res = pd.concat(res)
    cols = ["mean_prod_t", "exp_extra_cost_eur", "p90_extra_cost_eur", "mean_prod_value_eur", "exp_extra_tco2e"]
    b = res[res.option == "no_adaptation"][["region", "crop", "scenario"] + cols].rename(columns={c: "b_" + c for c in cols})
    res = res.merge(b, on=["region", "crop", "scenario"])
    for c in cols:
        res["delta_" + c] = res[c] - res["b_" + c]
    # benefit = avoided replacement cost + extra production value; cost only modelled for irrigation
    res["annual_benefit_eur"] = -res.delta_exp_extra_cost_eur + res.delta_mean_prod_value_eur.clip(lower=0) * 0  # conservative: avoided shortfall cost only
    res["annual_benefit_incl_volume_eur"] = -res.delta_exp_extra_cost_eur + res.delta_mean_prod_value_eur
    irr_area = irr[can].drop_duplicates("parcel_id").groupby(["region", "crop"]).area_ha.sum()
    irr_already = base[can].drop_duplicates("parcel_id").assign(a=lambda x: x.area_ha * x.irrigated).groupby(["region", "crop"]).a.sum()
    add_ha = (irr_area - irr_already).rename("added_irrigated_ha")
    res = res.merge(add_ha.reset_index(), on=["region", "crop"], how="left")
    res["annual_cost_eur"] = np.where(res.option == "irrigation_all_vegetable_parcels", res.added_irrigated_ha.fillna(0) * 250, np.nan)
    res.loc[res.option != "irrigation_all_vegetable_parcels", "added_irrigated_ha"] = np.nan
    res["net_benefit_eur"] = res.annual_benefit_incl_volume_eur - res.annual_cost_eur.fillna(0)
    keep = ["option", "region", "crop", "scenario", "area_ha", "added_irrigated_ha", "mean_prod_t", "delta_mean_prod_t", "exp_extra_cost_eur",
            "delta_exp_extra_cost_eur", "delta_p90_extra_cost_eur", "delta_mean_prod_value_eur", "delta_exp_extra_tco2e",
            "annual_benefit_incl_volume_eur", "annual_cost_eur", "net_benefit_eur"]
    res = res[keep].round(1)
    res.to_csv(OUT / "c3_adaptation.csv", index=False)
    print(res[res.option != "no_adaptation"].to_string())
    pd.DataFrame([dict(corr_FI_SE_sim_1991_2026=round(corr_sim, 3), corr_FI_SE_observed_2018_2026=round(corr_obs, 3),
                       anomaly_2026_FI=c2026.get("FI_SW"), anomaly_2026_SE=c2026.get("SE_SKANE"))]).to_csv(OUT / "c3_hedge_stats.csv", index=False)


if __name__ == "__main__":
    main()
