"""Agro-climatic feature engine (semi-mechanistic, mirrors the truth-model structure in SIMULATION_DESIGN.md).

For every (scenario, year, cell, soil class, crop) we compute:
  sowing day (first 5-day mean T above crop threshold after 1 Apr), GDD-based stages (base 5 C),
  bucket soil water by soil class (reset full on 1 Apr), stage drought stress, heat days at flowering,
  waterlogging after sowing, rain before harvest, season length / immaturity, blight pressure (Jul-Aug warm+wet),
  pollen-beetle pressure (warm May).
Output: features.parquet
"""
import sys
import numpy as np
import pandas as pd
from pathlib import Path

ROOT = Path(__import__("os").environ["CCN_PKG"] + "/data")
OUT = Path(__import__("os").environ["CCN_WORK"] + "/C")

# crop parameters: sowing threshold (5-day mean C), flowering window GDD, maturity GDD
CROPS = {
    "pea":         dict(sow_t=6.0, flw=(420, 650), mat=850),
    "turnip_rape": dict(sow_t=6.5, flw=(450, 700), mat=1150),
    "potato":      dict(sow_t=8.5, flw=(450, 1000), mat=1300),
    "carrot":      dict(sow_t=7.5, flw=(500, 1100), mat=1350),
    "spinach":     dict(sow_t=6.0, flw=(250, 450), mat=550),
}
SOIL_CAP = {"sand": 60.0, "fine_sand": 100.0, "silt": 160.0, "clay": 130.0, "organic": 200.0}
SOILS = list(SOIL_CAP)


def year_features(T, TX, P, PET, doy):
    """T etc: arrays [cell, day] for one year (Jan 1..Dec 31). Returns list of dict rows (per soil, crop)."""
    n = T.shape[0]
    a1 = 90  # index of ~1 Apr (0-based doy 90/91)
    m = lambda d0, d1: slice(d0, d1)
    rows = {}
    # 5-day running mean temperature
    k = 5
    cs = np.cumsum(np.pad(T, ((0, 0), (1, 0))), axis=1)
    rm = (cs[:, k:] - cs[:, :-k]) / k  # rm[:, i] = mean T[i:i+k]
    gdd_d = np.clip(T - 5.0, 0, None)
    # bucket per soil (Apr 1 .. Oct 31)
    ndays = T.shape[1]
    last = min(304, ndays)
    stress = {}
    full = {}
    for s, cap in SOIL_CAP.items():
        W = np.full(n, cap)
        st = np.zeros((n, ndays))
        fu = np.zeros((n, ndays), bool)
        for d in range(a1, last):
            et = PET[:, d] * np.clip(W / (0.6 * cap), 0, 1)
            W = W + P[:, d] - et
            fu[:, d] = W >= cap
            W = np.clip(W, 0, cap)
            st[:, d] = np.clip(1 - W / (0.5 * cap), 0, 1)  # stress when below 50 % of capacity
        stress[s], full[s] = st, fu
    may = m(120, 151); jul_aug = m(181, 243); jja = m(151, 243)
    may_t = T[:, may].mean(1); may_warm = (TX[:, may] >= 15).sum(1)
    blight = ((T[:, jul_aug] >= 13) & (P[:, jul_aug] >= 1.0)).sum(1)
    hot_jja = (TX[:, jja] >= 27).sum(1)
    pjja = P[:, jja].sum(1); petjja = PET[:, jja].sum(1)
    gdd_season = gdd_d[:, a1:273].sum(1)
    for crop, cp in CROPS.items():
        above = rm[:, a1:200] >= cp["sow_t"]
        sow = np.where(above.any(1), above.argmax(1) + a1 + k - 1, 200)
        idx = np.arange(ndays)[None, :]
        after = idx >= sow[:, None]
        g = np.cumsum(gdd_d * after, axis=1)
        f0 = (g >= cp["flw"][0]).argmax(1); f1 = (g >= cp["flw"][1]).argmax(1)
        reached = g[:, -1] >= cp["mat"]
        matd = np.where(reached, (g >= cp["mat"]).argmax(1), 300)
        f0 = np.where(g[:, -1] >= cp["flw"][0], f0, 300); f1 = np.where(g[:, -1] >= cp["flw"][1], f1, 300)
        veg = after & (idx < f0[:, None])
        flw = (idx >= f0[:, None]) & (idx < f1[:, None])
        fill = (idx >= f1[:, None]) & (idx < matd[:, None])
        sow30 = after & (idx < sow[:, None] + 30)
        preh = (idx >= matd[:, None] - 14) & (idx < matd[:, None])
        hot_flw = ((TX >= 27) * flw).sum(1); hot25_flw = ((TX >= 25) * flw).sum(1)
        tmax_flw = np.where(flw.any(1), (TX * flw).sum(1) / np.maximum(flw.sum(1), 1), np.nan)
        rain_sow = (P * sow30).sum(1)
        rain_preh = (P * preh).sum(1); wetd_preh = ((P >= 2) * preh).sum(1)
        gdd_by_sep15 = g[:, 257]
        base = dict(crop=crop, sow_doy=sow, flw_doy=f0, mat_doy=matd, immature=(~reached).astype(int),
                    gdd_by_sep15=gdd_by_sep15, gdd_season=gdd_season, hot_flw=hot_flw, hot25_flw=hot25_flw,
                    tmax_flw=tmax_flw, rain_sow30=rain_sow, rain_preharv=rain_preh, wetdays_preharv=wetd_preh,
                    may_t=may_t, may_warm=may_warm, blight_days=blight, hot_jja=hot_jja,
                    p_jja=pjja, pet_jja=petjja)
        for s in SOILS:
            st = stress[s]
            r = dict(base)
            r["soil"] = s
            r["ds_veg"] = (st * veg).sum(1) / np.maximum(veg.sum(1), 1)
            r["ds_flw"] = (st * flw).sum(1) / np.maximum(flw.sum(1), 1)
            r["ds_fill"] = (st * fill).sum(1) / np.maximum(fill.sum(1), 1)
            r["ds_season"] = (st * (after & (idx < matd[:, None]))).sum(1) / np.maximum((after & (idx < matd[:, None])).sum(1), 1)
            r["wl_days"] = (full[s] * sow30 * (P >= 3)).sum(1)
            rows[(crop, s)] = r
    return rows


def build():
    w = pd.read_parquet(ROOT / "04_climate/weather_daily_1991_2060.parquet")
    w["date"] = pd.to_datetime(w.date)
    w["year"] = w.date.dt.year
    w["doy"] = w.date.dt.dayofyear - 1
    out = []
    for (scen, yr), g in w.groupby(["scenario", "year"], sort=True):
        g = g[g.doy < 365]
        cells = np.sort(g.cell_id.unique())
        piv = {v: g.pivot(index="cell_id", columns="doy", values=v).loc[cells].to_numpy(float)
               for v in ("tmean_c", "tmax_c", "precip_mm", "pet_mm")}
        rows = year_features(piv["tmean_c"], piv["tmax_c"], piv["precip_mm"], piv["pet_mm"], None)
        for (crop, s), r in rows.items():
            df = pd.DataFrame({kk: (vv if np.ndim(vv) else [vv] * len(cells)) for kk, vv in r.items()})
            df["cell_id"] = cells; df["scenario"] = scen; df["year"] = yr
            out.append(df)
        print(scen, yr, file=sys.stderr, end=" ")
    f = pd.concat(out, ignore_index=True)
    f.to_parquet(OUT / "features.parquet")
    print("\nfeatures", f.shape)


if __name__ == "__main__":
    build()
