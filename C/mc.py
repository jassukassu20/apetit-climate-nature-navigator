"""C2 Monte Carlo (v2): climate yield risk 2041-2060 vs 1991-2020 for the 2025 contract-parcel mix.

Weather samples per SSP (future):
  (a) delta method: each 1991-2020 year (all 84 cells, daily) shifted by climate_change_signals.csv monthly deltas
      (T and Tmax += delta_tmean; precip *= precip_factor; Hargreaves PET scaled by (T+dT+17.8)/(T+17.8))  -> 30 years
  (b) the supplied SSP realisation 2041-2060                                                                -> 20 years
  Base: the 30 historical years 1991-2020.
Yields: trained YieldModel (technology & management frozen at 2025), area-weighted over the 2025 parcel mix.
Calibration (per region x crop, from the leave-one-year-out backtest 2014-2026, detrended):
  observed anomaly = k * predicted anomaly + e,  e ~ N(0, s)   -> k corrects GBM damping, s adds the non-weather /
  unexplained year-to-year variance, so simulated variance matches the observed aggregate variance.
Monte Carlo: N draws per region x crop x period: pick a weather year uniformly, Y = 1 + k*a_w + e.
  mean_yield_change_pct = 100 * (E[Y_fut]/E[Y_base] - 1);  p_bad_year = P(Y_fut < 0.8 * E[Y_base]).
Outputs: submissions/C2 (v2), C/C2_v1 backup, C/c2_mc_detail.csv, C/c3_euro_risk.csv (MC-based, same columns + p_bad_year).
"""
import sys; sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/C")
import shutil
import numpy as np
import pandas as pd
import model as M
import features as FE
from predict import management_table, attach_mgmt

ROOT, OUT = M.ROOT, M.OUT
SUB = OUT.parent / "submissions"; TPL = ROOT.parent / "tasks/templates"
SSPS = ["ssp126", "ssp245", "ssp585"]
N = 40000
rng = np.random.default_rng(20261107)


def delta_features():
    p = OUT / "mc_features.parquet"
    if p.exists():
        return pd.read_parquet(p)
    sig = pd.read_csv(ROOT / "04_climate/climate_change_signals.csv")
    w = pd.read_parquet(ROOT / "04_climate/weather_daily_1991_2060.parquet")
    w = w[(w.scenario == "historical")]
    w["date"] = pd.to_datetime(w.date); w["year"] = w.date.dt.year; w["doy"] = w.date.dt.dayofyear - 1; w["month"] = w.date.dt.month
    w = w[w.year.between(1991, 2020) & (w.doy < 365)]
    out = []
    for ssp in SSPS:
        s = sig[sig.scenario == ssp].set_index("month")
        dT = w.month.map(s.delta_tmean_c).values; pf = w.month.map(s.precip_factor).values
        ww = w.assign(tmean_c=w.tmean_c + dT, tmax_c=w.tmax_c + dT, precip_mm=w.precip_mm * pf,
                      pet_mm=w.pet_mm * np.clip((w.tmean_c + dT + 17.8) / np.maximum(w.tmean_c + 17.8, 0.5), 0, 3))
        for yr, g in ww.groupby("year"):
            cells = np.sort(g.cell_id.unique())
            pv = {v: g.pivot(index="cell_id", columns="doy", values=v).loc[cells].to_numpy(float) for v in ("tmean_c", "tmax_c", "precip_mm", "pet_mm")}
            for (crop, soil), r in FE.year_features(pv["tmean_c"], pv["tmax_c"], pv["precip_mm"], pv["pet_mm"], None).items():
                df = pd.DataFrame({kk: (vv if np.ndim(vv) else [vv] * len(cells)) for kk, vv in r.items()})
                df["cell_id"] = cells; df["scenario"] = "delta_" + ssp; df["year"] = yr
                out.append(df)
        print("delta features", ssp, flush=True)
    f = pd.concat(out, ignore_index=True); f.to_parquet(p)
    return f


def calibration():
    bt = pd.read_parquet(OUT / "backtest.parquet")
    a = bt.assign(po=bt.yield_t_ha * bt.survey_area, pp=bt.pred * bt.survey_area, A=bt.survey_area).groupby(["region", "crop", "year"])[["po", "pp", "A"]].sum()
    a["yo"], a["yp"] = a.po / a.A, a.pp / a.A
    rows = []
    for (rg, cr), g in a.groupby(level=[0, 1]):
        yrs = g.index.get_level_values(2).values.astype(float)
        def anom(v):
            c = np.polyfit(yrs, np.log(v), 1); return np.exp(np.log(v) - np.polyval(c, yrs)) - 1
        o, pr = anom(g.yo.values), anom(g.yp.values)
        k = float(np.clip(np.cov(o, pr)[0, 1] / np.var(pr, ddof=1), 0.8, 1.6))
        s = float(np.std(o - k * pr, ddof=2))
        rows.append(dict(region=rg, crop=cr, k=k, s=s, sd_obs=float(np.std(o, ddof=1)), sd_pred=float(np.std(pr, ddof=1)), n_years=len(o)))
    return pd.DataFrame(rows)


def main():
    parcels = M.load_static()
    feats = pd.read_parquet(OUT / "features.parquet")
    dfe = delta_features()
    allf = pd.concat([feats[(feats.scenario == "historical") & feats.year.between(1991, 2020)],
                      feats[feats.scenario.isin(SSPS) & feats.year.between(2041, 2060)], dfe], ignore_index=True)
    d = pd.read_parquet(OUT / "training.parquet")
    model = M.YieldModel().fit(d)
    last, cmed = management_table(d)
    ch = pd.read_csv(ROOT / "03_farming/parcel_crop_history_and_plan.csv")
    mix = ch[(ch.year == 2025) & ch.crop.isin(M.CROPS5)][["parcel_id", "crop"]]
    sy = allf[["scenario", "year"]].drop_duplicates()
    kk = mix.assign(key=1).merge(sy.assign(key=1), on="key").drop(columns="key")
    pf = attach_mgmt(M.parcel_features(parcels, allf, kk), last, cmed)
    pf["y"] = model.predict(pf, year_for_trend=2025)
    pf["prod"] = pf.y * pf.area_ha
    reg = pf.groupby(["region", "crop", "scenario", "year"]).agg(prod=("prod", "sum"), area=("area_ha", "sum")).reset_index()
    reg["Y"] = reg["prod"] / reg.area
    base = reg[reg.scenario == "historical"].groupby(["region", "crop"]).Y.mean().rename("B").reset_index()
    reg = reg.merge(base, on=["region", "crop"]); reg["a"] = reg.Y / reg.B - 1
    cal = calibration(); cal.to_csv(OUT / "c2_mc_calibration.csv", index=False)
    reg = reg.merge(cal[["region", "crop", "k", "s"]], on=["region", "crop"])
    reg.to_csv(OUT / "c2_mc_weather_years.csv", index=False)

    price = pd.read_csv(ROOT / "05_scenarios/contract_prices_and_replacement_premiums.csv")
    p26 = price[price.year == 2026].set_index("item")
    import c3 as C3  # reuse emission deltas
    det, eur = [], []
    for (rg, cr), g in reg.groupby(["region", "crop"]):
        k, s = g.k.iloc[0], g.s.iloc[0]
        it = "pea_SE" if rg == "SE_SKANE" else cr
        price_t, prem = p26.contract_price_eur_t[it], p26.replacement_import_premium_frac[it]
        contracted = float(g.B.iloc[0] * g.area.iloc[0])
        def draws(a):
            w = rng.integers(0, len(a), N)
            return 1 + k * a[w] + rng.normal(0, s, N)
        hb = draws(g[g.scenario == "historical"].a.values)
        thr = 0.8 * hb.mean()
        rec = dict(region=rg, crop=cr, k=k, s=s, p_bad_1991_2020=float((hb < thr).mean()))
        sets = {"historical": hb}
        for ssp in SSPS:
            fa = np.concatenate([g[g.scenario == "delta_" + ssp].a.values, g[g.scenario == ssp].a.values])
            fd = draws(fa)
            sets[ssp] = fd
            dd = draws(g[g.scenario == "delta_" + ssp].a.values); rr = draws(g[g.scenario == ssp].a.values)
            rec.update({f"{ssp}_change_pct": 100 * (fd.mean() / hb.mean() - 1), f"{ssp}_p_bad": float((fd < thr).mean()),
                        f"{ssp}_change_delta_only": 100 * (dd.mean() / hb.mean() - 1), f"{ssp}_change_realisation_only": 100 * (rr.mean() / hb.mean() - 1),
                        f"{ssp}_p_bad_delta_only": float((dd < thr).mean()), f"{ssp}_p_bad_realisation_only": float((rr < thr).mean())})
        det.append(rec)
        for scen, ydraw in sets.items():
            prod = contracted * ydraw / hb.mean()
            short = np.clip(contracted - prod, 0, None)
            cost = short * price_t * prem
            eur.append(dict(region=rg, crop=cr, scenario=scen, period="1991-2020" if scen == "historical" else "2041-2060",
                            contracted_t=round(contracted), mean_prod_t=round(prod.mean()), exp_shortfall_t=round(short.mean()),
                            exp_extra_cost_eur=round(cost.mean()), p90_extra_cost_eur=round(np.quantile(cost, 0.9)),
                            worst_year_extra_cost_eur=round(np.quantile(cost, 0.99)),
                            exp_replacement_spend_eur=round((short * price_t * (1 + prem)).mean()),
                            exp_extra_tco2e=round(short.mean() * C3.d_ef[it]), mean_prod_value_eur=round(prod.mean() * price_t),
                            p_bad_year=round(float((ydraw < thr).mean()), 3)))
    det = pd.DataFrame(det); det.round(4).to_csv(OUT / "c2_mc_detail.csv", index=False)

    # write C2 v2 (keep v1)
    v1 = OUT / "C2_climate_yield_risk_submission_v1.csv"
    if not v1.exists():
        shutil.copy(SUB / "C2_climate_yield_risk_submission.csv", v1)
    t2 = pd.read_csv(TPL / "C2_climate_yield_risk_submission.csv")[["region", "crop", "scenario", "period"]]
    rows = []
    for r in det.itertuples():
        for ssp in SSPS:
            rows.append(dict(region=r.region, crop=r.crop, scenario=ssp, mean_yield_change_pct=round(getattr(r, f"{ssp}_change_pct"), 2),
                             p_bad_year=round(getattr(r, f"{ssp}_p_bad"), 3)))
    out = t2.merge(pd.DataFrame(rows), on=["region", "crop", "scenario"], how="left")
    assert out.notna().all().all()
    out.to_csv(SUB / "C2_climate_yield_risk_submission.csv", index=False)
    e = pd.DataFrame(eur)
    e.to_csv(OUT / "c3_euro_risk.csv", index=False)
    old = pd.read_csv(v1)
    cmp = old.merge(out, on=["region", "crop", "scenario", "period"], suffixes=("_v1", "_v2"))
    cmp.to_csv(OUT / "c2_v1_vs_v2.csv", index=False)
    print(cal.round(3).to_string()); print(cmp.to_string()); print(det.round(3).to_string())


if __name__ == "__main__":
    main()
