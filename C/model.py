"""Yield model: log(yield) = trend(crop) + farm skill (shrunken random effect) + GBM(weather, soil, management).
Fitted by backfitting; leave-one-year-out backtest. Exposes build_training(), fit(), predict_frame().
"""
import numpy as np
import pandas as pd
import lightgbm as lgb
from pathlib import Path

ROOT = Path(__import__("os").environ["CCN_PKG"] + "/data")
OUT = Path(__import__("os").environ["CCN_WORK"] + "/C")
CROPS5 = ["pea", "turnip_rape", "potato", "carrot", "spinach"]
WFEAT = ["sow_doy", "flw_doy", "mat_doy", "immature", "gdd_by_sep15", "gdd_season", "hot_flw", "hot25_flw", "tmax_flw",
         "rain_sow30", "rain_preharv", "wetdays_preharv", "may_t", "may_warm", "blight_days", "hot_jja", "p_jja", "pet_jja",
         "ds_veg", "ds_flw", "ds_fill", "ds_season", "wl_days"]
SOILFR = ["fr_sand", "fr_fine_sand", "fr_silt", "fr_clay", "fr_organic"]
MGMT = ["irrigated", "organic", "n_min", "sprays", "clay_pct", "slope_pct", "is_se"]
X_COLS = WFEAT + SOILFR + MGMT
T0 = 2020
# physically-signed constraints: more stress can never raise yield (keeps extrapolation sane under SSP5-8.5)
NEG = ["ds_veg", "ds_flw", "ds_fill", "ds_season", "hot_flw", "hot25_flw", "immature", "wl_days"]


def load_static():
    p = pd.read_csv(ROOT / "01_master/parcels.csv")
    cells = pd.read_csv(ROOT / "01_master/climate_grid_cells.csv")
    fr = pd.read_csv(ROOT / "01_master/farm_registry.csv")
    p["region"] = np.where(p.farm_id.str.startswith("S"), "SE_SKANE", "FI_SW")
    # nearest cell within region
    out = []
    for reg, g in p.groupby("region"):
        c = cells[cells.region == reg]
        d = (g.lat.values[:, None] - c.lat.values[None]) ** 2 + ((g.lon.values[:, None] - c.lon.values[None]) * np.cos(np.radians(g.lat.values[:, None]))) ** 2
        gg = g.copy(); gg["cell_id"] = c.cell_id.values[d.argmin(1)]
        out.append(gg)
    p = pd.concat(out)
    p = p.merge(fr[["farm_id", "organic_certified", "livestock"]], on="farm_id", how="left")
    return p


def parcel_features(parcels, feats, keys):
    """keys: DataFrame with parcel_id, year, crop, scenario -> joined weather features by parcel's cell and soil."""
    k = keys.merge(parcels[["parcel_id", "farm_id", "region", "cell_id", "soil_class_soilmap", "area_ha", "clay_pct_soilmap",
                            "slope_pct", "organic_certified"]], on="parcel_id", how="left")
    k = k.rename(columns={"soil_class_soilmap": "soil"})
    k = k.merge(feats, on=["scenario", "year", "cell_id", "crop", "soil"], how="left")
    for s in ["sand", "fine_sand", "silt", "clay", "organic"]:
        k["fr_" + s] = (k.soil == s).astype(float)
    k["clay_pct"] = k.clay_pct_soilmap; k["organic"] = k.organic_certified.astype(float)
    k["is_se"] = (k.region == "SE_SKANE").astype(float)
    return k


def build_training(parcels, feats):
    ch = pd.read_csv(ROOT / "03_farming/parcel_crop_history_and_plan.csv")
    ch = ch[ch.crop.isin(CROPS5) & (ch.status == "declared")]
    sv = pd.read_csv(ROOT / "03_farming/farm_survey_fi.csv")
    se = pd.read_csv(ROOT / "03_farming/foodhills_odlingsdata_se.csv", sep=";", decimal=",")
    se = pd.DataFrame(dict(farm_id=se.odlar_id, year=se["skördeår"], crop="pea", yield_t_ha=se["levererad_mängd_ton"] / se.areal_ha,
                           irrigated=(se.bevattnad == "ja").astype(float), n_min=se["kvävegiva_kg_ha"].astype(float), sprays=np.nan,
                           survey_area=se.areal_ha))
    fi = pd.DataFrame(dict(farm_id=sv.farm_id, year=sv.year, crop=sv.crop, yield_t_ha=sv.yield_t_ha, irrigated=sv.irrigated.astype(float),
                           n_min=sv.n_mineral_kg_ha, sprays=sv.sprays, survey_area=sv.area_ha))
    obs = pd.concat([fi, se], ignore_index=True)
    # robust cleaning: drop unit / decimal errors (ratio to crop-region-year median)
    obs["reg"] = np.where(obs.farm_id.str.startswith("S"), "SE", "FI")
    med = obs.groupby(["crop", "reg", "year"]).yield_t_ha.transform("median")
    r = obs.yield_t_ha / med
    obs["clean"] = (r > 0.3) & (r < 2.2) & obs.yield_t_ha.notna()
    obs.loc[obs.n_min > 400, "n_min"] = np.nan
    obs = obs[obs.clean].copy()
    keys = ch[["parcel_id", "farm_id", "year", "crop"]].copy(); keys["scenario"] = "historical"
    pf = parcel_features(parcels, feats, keys.drop(columns="farm_id"))
    num = WFEAT + SOILFR + ["clay_pct", "slope_pct", "organic", "is_se"]
    agg = pf.groupby(["farm_id", "year", "crop"]).apply(
        lambda g: pd.Series(np.average(g[num].to_numpy(float), axis=0, weights=g.area_ha), index=num), include_groups=False).reset_index()
    agg["area_parcels"] = pf.groupby(["farm_id", "year", "crop"]).area_ha.sum().values
    agg["region"] = np.where(agg.farm_id.str.startswith("S"), "SE_SKANE", "FI_SW")
    d = obs.merge(agg, on=["farm_id", "year", "crop"], how="inner")
    return d, obs


class YieldModel:
    def __init__(self, n_iter=3, shrink=3.0, params=None):
        self.n_iter, self.shrink = n_iter, shrink
        self.params = params or dict(n_estimators=500, learning_rate=0.03, num_leaves=15, min_child_samples=15,
                                     subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1,
                                     monotone_constraints=[-1 if c in NEG else 0 for c in X_COLS])

    def fit(self, d):
        self.models, self.trend, self.farm = {}, {}, {}
        for crop, g in d.groupby("crop"):
            y = np.log(g.yield_t_ha.values)
            X = g[X_COLS].astype(float)
            t = (g.year.values - T0).astype(float)
            fe = np.zeros(len(g)); b = 0.0
            for it in range(self.n_iter):
                m = lgb.LGBMRegressor(**self.params, random_state=it)
                m.fit(X, y - fe - b * t)
                gp = m.predict(X)
                r = y - gp
                # trend + farm effect jointly: demean by farm then OLS on t
                dfr = pd.DataFrame(dict(f=g.farm_id.values, r=r, t=t))
                fm = dfr.groupby("f").r.transform("mean"); tm = dfr.groupby("f").t.transform("mean")
                rc, tc = r - fm, t - tm
                b = float((rc * tc).sum() / max((tc * tc).sum(), 1e-9))
                rr = r - b * t
                st = pd.DataFrame(dict(f=g.farm_id.values, rr=rr - rr.mean())).groupby("f").rr.agg(["sum", "count"])
                feff = st["sum"] / (st["count"] + self.shrink)
                fe = g.farm_id.map(feff).values
            self.models[crop] = m; self.trend[crop] = b; self.farm[crop] = feff
            self.resid_sd = getattr(self, "resid_sd", {}); self.resid_sd[crop] = float(np.std(y - gp - b * t - fe))
        return self

    def predict(self, d, year_for_trend=None):
        out = np.full(len(d), np.nan)
        for crop, idx in d.groupby("crop").indices.items():
            g = d.iloc[idx]
            t = ((g.year.values if year_for_trend is None else np.full(len(g), year_for_trend)) - T0).astype(float)
            fe = g.farm_id.map(self.farm[crop]).fillna(0).values
            out[idx] = np.exp(self.models[crop].predict(g[X_COLS].astype(float)) + self.trend[crop] * t + fe)
        return out


def backtest(d, years=range(2014, 2027)):
    rows = []
    for yv in years:
        tr, te = d[d.year != yv], d[d.year == yv].copy()
        m = YieldModel().fit(tr)
        te["pred"] = m.predict(te)
        rows.append(te)
    bt = pd.concat(rows)
    bt["prod_obs"] = bt.yield_t_ha * bt.survey_area; bt["prod_pred"] = bt.pred * bt.survey_area
    agg = bt.groupby(["region", "crop", "year"])[["prod_obs", "prod_pred"]].sum()
    agg["ape"] = (agg.prod_pred / agg.prod_obs - 1).abs()
    cm = bt.groupby("crop").yield_t_ha.transform("mean")
    bt["nerr"] = (bt.pred - bt.yield_t_ha) / cm
    # baseline: farm historical mean (other years)
    return bt, agg


if __name__ == "__main__":
    parcels = load_static()
    feats = pd.read_parquet(OUT / "features.parquet")
    d, obs = build_training(parcels, feats)
    d.to_parquet(OUT / "training.parquet")
    print("training rows", len(d), d.groupby("crop").size().to_dict())
    bt, agg = backtest(d)
    print("MAPE by crop", agg.groupby(level=1).ape.mean().round(3).to_dict(), "overall", round(agg.ape.mean(), 4))
    print("nRMSE by crop", bt.groupby("crop").nerr.apply(lambda e: np.sqrt((e ** 2).mean())).round(3).to_dict(),
          "overall", round(float(np.sqrt((bt.nerr ** 2).mean())), 4))
    bt.to_parquet(OUT / "backtest.parquet"); agg.to_csv(OUT / "backtest_agg.csv")
