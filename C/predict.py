"""C1 (2027-2031 parcel yields, ssp245) and C2 (2041-2060 risk by SSP) predictions + chart data + feature importance."""
import sys; sys.path.insert(0, __import__("os").environ["CCN_WORK"] + "/C")
import numpy as np
import pandas as pd
import model as M

ROOT, OUT = M.ROOT, M.OUT
TPL = ROOT.parent / "tasks/templates"
SUB = OUT.parent / "submissions"


def management_table(obs):
    """latest management per farm x crop (irrigation status last observed; N and sprays median of last 3 obs)."""
    o = obs.sort_values("year")
    last = o.groupby(["farm_id", "crop"]).tail(3).groupby(["farm_id", "crop"]).agg(
        irrigated=("irrigated", "last"), n_min=("n_min", "median"), sprays=("sprays", "median")).reset_index()
    reg = np.where(o.farm_id.str.startswith("S"), "SE", "FI")
    cmed = o[o.year >= 2022].assign(reg=reg[o.year >= 2022]).groupby(["crop", "reg"]).agg(
        irrigated=("irrigated", "mean"), n_min=("n_min", "median"), sprays=("sprays", "median")).reset_index()
    return last, cmed


def attach_mgmt(k, last, cmed):
    k = k.merge(last, on=["farm_id", "crop"], how="left")
    k["reg"] = np.where(k.farm_id.str.startswith("S"), "SE", "FI")
    k = k.merge(cmed.rename(columns={"irrigated": "irr_c", "n_min": "n_c", "sprays": "sp_c"}), on=["crop", "reg"], how="left")
    # non-respondents: irrigation as expected share (fraction) of crop-region
    k["irrigated"] = k.irrigated.fillna(k.irr_c); k["n_min"] = k.n_min.fillna(k.n_c); k["sprays"] = k.sprays.fillna(k.sp_c)
    return k.drop(columns=["irr_c", "n_c", "sp_c", "reg"])


def main():
    parcels = M.load_static()
    feats = pd.read_parquet(OUT / "features.parquet")
    d = pd.read_parquet(OUT / "training.parquet")
    _, obs = M.build_training(parcels, feats) if False else (None, d)
    model = M.YieldModel().fit(d)
    last, cmed = management_table(d)

    # ---------- C1 ----------
    tpl = pd.read_csv(TPL / "C1_yields_2027_2031_submission.csv")
    k = tpl[["parcel_id", "year", "crop"]].copy(); k["scenario"] = "ssp245"
    pf = M.parcel_features(parcels, feats, k)
    pf = attach_mgmt(pf, last, cmed)
    pf["yield_t_ha_pred"] = model.predict(pf)
    sub = tpl.drop(columns="yield_t_ha_pred").merge(pf[["parcel_id", "year", "crop", "yield_t_ha_pred"]], on=["parcel_id", "year", "crop"], how="left")
    assert len(sub) == len(tpl) and sub.yield_t_ha_pred.notna().all()
    sub["yield_t_ha_pred"] = sub.yield_t_ha_pred.round(3)
    sub.to_csv(SUB / "C1_yields_2027_2031_submission.csv", index=False)
    print("C1 written", len(sub)); print(sub.groupby(["region", "crop", "year"]).apply(
        lambda g: np.average(g.yield_t_ha_pred, weights=g.area_ha), include_groups=False).unstack().round(2))

    # ---------- C2 + chart series ----------
    ch = pd.read_csv(ROOT / "03_farming/parcel_crop_history_and_plan.csv")
    mix = ch[(ch.year == 2025) & ch.crop.isin(M.CROPS5)][["parcel_id", "crop"]]
    scen_years = [("historical", y) for y in range(1991, 2027)] + [(s, y) for s in ("ssp126", "ssp245", "ssp585") for y in range(2027, 2061)]
    frames = []
    for s, yrs in pd.DataFrame(scen_years, columns=["s", "y"]).groupby("s").y:
        kk = mix.assign(key=1).merge(pd.DataFrame({"year": yrs.values, "key": 1}), on="key").drop(columns="key")
        kk["scenario"] = s
        frames.append(kk)
    kk = pd.concat(frames, ignore_index=True)
    pf = M.parcel_features(parcels, feats, kk)
    pf = attach_mgmt(pf, last, cmed)
    pf["y"] = model.predict(pf, year_for_trend=2025)  # technology & management frozen at 2025 -> pure climate signal
    pf["prod"] = pf.y * pf.area_ha
    reg = pf.groupby(["region", "crop", "scenario", "year"]).agg(prod=("prod", "sum"), area=("area_ha", "sum")).reset_index()
    reg["mean_yield_t_ha"] = reg["prod"] / reg.area
    reg[["region", "crop", "scenario", "year", "mean_yield_t_ha"]].round(4).to_csv(OUT / "yield_history_and_projection.csv", index=False)

    base = reg[(reg.scenario == "historical") & reg.year.between(1991, 2020)].groupby(["region", "crop"]).mean_yield_t_ha.mean().rename("base")
    # anomaly calibration: GBM + shrinkage damps year-to-year anomalies. k = sd(observed regional anomaly) / sd(backtest-predicted),
    # from the leave-one-year-out backtest, clipped to [1, 1.4]. Applied to anomalies around the 1991-2020 mean.
    bt = pd.read_parquet(OUT / "backtest.parquet")
    a = bt.assign(po=bt.yield_t_ha * bt.survey_area, pp=bt.pred * bt.survey_area, A=bt.survey_area).groupby(["region", "crop", "year"])[["po", "pp", "A"]].sum()
    a["yo"], a["yp"] = a.po / a.A, a.pp / a.A
    kcal = a.groupby(level=[0, 1]).apply(lambda g: float(np.clip((g.yo / g.yo.mean()).std() / (g.yp / g.yp.mean()).std(), 1, 1.4))).rename("k")
    kcal.to_csv(OUT / "anomaly_calibration_k.csv")
    reg = reg.merge(base.reset_index(), on=["region", "crop"]).merge(kcal.reset_index(), on=["region", "crop"])
    reg["mean_yield_uncal"] = reg.mean_yield_t_ha
    reg["mean_yield_t_ha"] = reg.base * (1 + reg.k * (reg.mean_yield_t_ha / reg.base - 1))
    reg = reg.drop(columns=["base", "k"])
    reg[["region", "crop", "scenario", "year", "mean_yield_t_ha", "mean_yield_uncal"]].round(4).to_csv(OUT / "yield_history_and_projection.csv", index=False)
    fut = reg[reg.year.between(2041, 2060)].merge(base.reset_index(), on=["region", "crop"])
    c2 = fut.groupby(["region", "crop", "scenario"]).apply(lambda g: pd.Series(dict(
        mean_yield_change_pct=100 * (g.mean_yield_t_ha.mean() / g.base.iloc[0] - 1),
        p_bad_year=float((g.mean_yield_t_ha < 0.8 * g.base.iloc[0]).mean()))), include_groups=False).reset_index()
    # base-period bad-year frequency for context
    hb = reg[(reg.scenario == "historical") & reg.year.between(1991, 2020)].merge(base.reset_index(), on=["region", "crop"])
    pb = hb.groupby(["region", "crop"]).apply(lambda g: float((g.mean_yield_t_ha < 0.8 * g.base).mean()), include_groups=False).rename("p_bad_1991_2020")
    t2 = pd.read_csv(TPL / "C2_climate_yield_risk_submission.csv")[["region", "crop", "scenario", "period"]]
    out = t2.merge(c2, on=["region", "crop", "scenario"], how="left")
    out["mean_yield_change_pct"] = out.mean_yield_change_pct.round(2); out["p_bad_year"] = out.p_bad_year.round(3)
    out.to_csv(SUB / "C2_climate_yield_risk_submission.csv", index=False)
    print(out.merge(pb.reset_index(), on=["region", "crop"]).to_string())

    # ---------- feature importance (gain share) ----------
    fi = []
    for crop, m in model.models.items():
        g = m.booster_.feature_importance("gain"); g = g / g.sum()
        fi += [dict(crop=crop, feature=f, gain_share=round(float(v), 4)) for f, v in zip(M.X_COLS, g)]
    fi = pd.DataFrame(fi).sort_values(["crop", "gain_share"], ascending=[True, False])
    fi.to_csv(OUT / "feature_importance.csv", index=False)
    pd.Series(model.trend).rename("log_trend_per_yr").to_csv(OUT / "trend.csv")
    # parcel-level 2025-mix simulation for C3
    pf[["parcel_id", "farm_id", "region", "crop", "scenario", "year", "area_ha", "irrigated", "y"]].to_parquet(OUT / "sim_2025mix.parquet")


if __name__ == "__main__":
    main()
