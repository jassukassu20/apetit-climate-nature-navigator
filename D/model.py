"""Track D1 field-level P/N loss model (SBTN step 2: pressure x state).

Semi-physical multiplicative model per contract parcel (2025 Apetit crops), following the drivers in
SIMULATION_DESIGN.md §8. Relative factors are literature-informed priors; only the absolute scale
(and the delivery-decay length) is calibrated on the 6 public dev catchments, checked with
leave-one-out CV and against the 15 monitored outlet loads.
"""
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__import__("os").environ["CCN_PKG"] + "")
D = ROOT / "data"
APETIT_CROPS = ["pea", "potato", "carrot", "spinach", "turnip_rape"]
STATE_W = {"good": 1.0, "moderate": 1.2, "poor": 1.5, "bad": 1.8}

# --- priors (relative factors) ---
SOIL_EROSION = {"clay": 1.5, "silt": 1.3, "fine_sand": 0.9, "sand": 0.6, "organic": 0.5}
SOIL_N_LEACH = {"clay": 0.85, "silt": 1.0, "fine_sand": 1.15, "sand": 1.35, "organic": 1.4}
CROP_EROSION = {"pea": 1.0, "turnip_rape": 0.9, "potato": 1.8, "carrot": 1.7, "spinach": 1.5}
CROP_N_UPTAKE_KG_PER_T = {"pea": 0.0, "turnip_rape": 33.0, "potato": 3.3, "carrot": 1.5, "spinach": 4.0}
DEFAULT_N = {"pea": 25, "turnip_rape": 95, "potato": 95, "carrot": 95, "spinach": 250}


def load():
    par = pd.read_csv(D / "01_master/parcels.csv")
    ch = pd.read_csv(D / "03_farming/parcel_crop_history_and_plan.csv")
    cat = pd.read_csv(D / "06_nature/catchments.csv")
    sv = pd.read_csv(D / "03_farming/farm_survey_fi.csv")
    fh = pd.read_csv(D / "03_farming/foodhills_odlingsdata_se.csv", sep=";", decimal=",")
    cells = pd.read_csv(D / "01_master/climate_grid_cells.csv")
    wm = pd.read_csv(D / "04_climate/weather_monthly_1991_2060.csv")
    loads = pd.read_csv(D / "06_nature/monitored_catchment_loads.csv")
    return par, ch, cat, sv, fh, cells, wm, loads


def rain_factor(par, cells, wm, year):
    h = wm[wm.scenario == "historical"]
    ann = h.groupby(["cell_id", "year"]).precip_mm.sum().unstack()
    norm = ann.loc[:, 1991:2020].mean(axis=1)
    fac = ann[year] / norm
    # nearest cell within region
    cl = cells.set_index("cell_id")
    xy = cl[["lat", "lon"]].values
    d2 = (par.lat.values[:, None] - xy[:, 0]) ** 2 + ((par.lon.values[:, None] - xy[:, 1]) * 0.5) ** 2
    cell = cl.index.values[d2.argmin(1)]
    return pd.Series(fac.reindex(cell).values, index=par.index), cell


def build_parcels(year=2025, data=None):
    par, ch, cat, sv, fh, cells, wm, loads = data or load()
    c = ch[(ch.year == year) & ch.crop.isin(APETIT_CROPS)][["parcel_id", "crop", "catch_crop"]]
    p = par.merge(c, on="parcel_id", how="inner").reset_index(drop=True)
    # soil-P imputation: farm median -> soil class x region median
    p["region"] = np.where(p.farm_id.str.startswith("S"), "SE", "FI")
    p["p_test_imputed"] = p.p_test_mgl_latest.isna()
    fm = par.groupby("farm_id").p_test_mgl_latest.median()
    p["p_test"] = p.p_test_mgl_latest.fillna(p.farm_id.map(fm))
    sm = par.assign(region=np.where(par.farm_id.str.startswith("S"), "SE", "FI")).groupby(["region", "soil_class_soilmap"]).p_test_mgl_latest.median()
    p["p_test"] = p.p_test.fillna(pd.Series(list(zip(p.region, p.soil_class_soilmap))).map(sm))
    # N inputs: survey (FI) / Foodhills (SE) else crop defaults
    s = sv[sv.year == year].assign(n_in=lambda d: d.n_mineral_kg_ha + d.n_manure_kg_ha)
    p = p.merge(s[["farm_id", "crop", "n_in", "yield_t_ha", "catch_crop_share"]], on=["farm_id", "crop"], how="left")
    f = fh[fh["skördeår"] == year].rename(columns={"odlar_id": "farm_id"})
    f = f.assign(crop="pea", n_se=f["kvävegiva_kg_ha"], y_se=f["levererad_mängd_ton"] / f["areal_ha"])
    p = p.merge(f[["farm_id", "crop", "n_se", "y_se"]], on=["farm_id", "crop"], how="left")
    p["n_in"] = p.n_in.fillna(p.n_se).fillna(p.crop.map(DEFAULT_N))
    ymed = s.groupby("crop").yield_t_ha.median()
    p["yield_t_ha"] = p.yield_t_ha.fillna(p.y_se).fillna(p.crop.map(ymed)).fillna(3.0)
    p["n_surplus"] = (p.n_in.clip(upper=350) - p.yield_t_ha.clip(upper=80) * p.crop.map(CROP_N_UPTAKE_KG_PER_T)).clip(lower=0, upper=250)
    rf, cell = rain_factor(p, cells, wm, year)
    p["rain_factor"], p["cell_id"] = rf.values, cell
    p = p.merge(cat[["catchment_id", "nutrient_retention_frac_estimate"]], on="catchment_id", how="left")
    return p


def field_losses(p, L_p=400.0, L_n=1500.0, k_rain=1.0):
    """Edge-of-field losses (kg/ha) before scale calibration, plus delivery to water."""
    ero = (p.soil_class_soilmap.map(SOIL_EROSION) * (1 + p.slope_pct / 3.0) * p.crop.map(CROP_EROSION)
           * np.where(p.catch_crop, 0.8, 1.0) * np.where(p.drainage == "open_ditch", 1.15, 1.0))
    diss = (p.p_test / 12.0) * np.where(p.catch_crop, 1.05, 1.0)
    rain = p.rain_factor ** k_rain
    p_field = (0.6 * ero + 0.4 * diss) * rain * np.where(p.buffer_strip, 0.7, 1.0)
    n_field = (p.soil_class_soilmap.map(SOIL_N_LEACH) * (1 + p.n_surplus / 60.0)
               * np.where(p.catch_crop, 0.7, 1.0) * rain * np.where(p.buffer_strip, 0.9, 1.0)
               * np.where(p.soil_class_soilmap == "organic", 1.3, 1.0))
    del_p = np.exp(-p.dist_to_water_m / L_p)
    del_n = np.exp(-p.dist_to_water_m / L_n)
    ret = 1 - p.nutrient_retention_frac_estimate
    return dict(p_field=p_field, n_field=n_field, p_water=p_field * del_p * ret * p.area_ha,
                n_water=n_field * del_n * ret * p.area_ha)


def catchment_sums(p, fl):
    return pd.DataFrame(dict(catchment_id=p.catchment_id, P=fl["p_water"], N=fl["n_water"])).groupby("catchment_id").sum()


def fit_scale(raw, dev, col):
    m = raw.join(dev, how="inner")
    return float(np.exp(np.mean(np.log(m[col] / m[col.split("_")[0]]))))
