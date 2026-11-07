# Apetit Climate & Nature Navigator

**From raw, error-ridden sustainability data to checked numbers, SBTi targets, priced climate risk and a nature plan. An AI agent does the heavy lifting, and a named expert approves every result before it is used.**

## For the jury: start here (2 minutes)

| What | Where |
|---|---|
| ▶ **Live demo** (no install) | Website link at the top right of this page (*About*). Or download [`docs/index.html`](docs/index.html) and open it in a browser. Click **"Take the 3-minute tour"**. |
| 📊 **Pitch slides** | [`docs/Navigator_pitch_deck.pdf`](docs/Navigator_pitch_deck.pdf) |
| 📄 **One-page method note** | [`METHOD_NOTE.md`](METHOD_NOTE.md) |
| ✅ **CSV files for auto-scored tasks** | [`submissions/`](submissions/): A1, A2, C1, C2, D1, E |
| 🔁 **Reproduce everything** | `pip install -r requirements.txt` then `python run_all.py /path/to/APETIT_CLIMATE_NATURE_NAVIGATOR_2026` (about 2 min, byte-identical outputs) |

**Problem.** The 2025 draft report overstates Scope 3 by **314×** (kWh read as MWh, tonnes keyed as kg). The farm calculator also misses **15.8 kt** of peat-soil emissions.

**Approach.** Raw feeds go to an AI data-quality agent, then to clean tables, a GHG inventory and scenario models (SBTi/FLAG, NGFS, SSP, SBTN). Each module has to be approved by an expert, and every action is recorded in an audit log.

**Evidence.**
* A1: 96.0 (baseline 52.2)
* A2: 95.9 / 96.6 (baseline about 25)
* C1 backtest error: 6.8 % (baseline 11.6 %)
* D1: 76.7 (baseline 12.0)
* E: dev 3/3

**What Apetit should do.**
1. Block the draft report.
2. Count peat soils.
3. Set the SBTi base year to 2025 with a FLAG target.
4. Run the rapeseed supplier programme and the off-peat programme (the cheapest plan meeting all targets averages **€39/t**).
5. Hedge pea supply across Finland and Sweden (−72 % shortfall cost).
6. Fix the 50 hotspot fields first.

> All data is the synthetic Since AI 2026 package (v1.0.0). Figures illustrate the method, not Apetit's real emissions.

---

## What it does

| Step | What happens | Output |
|---|---|---|
| **A · Data-quality agent** | 18 detectors, one per planted issue type (unit slips, duplicates, currency, decimal shifts, meter gaps and spikes, wrong gas codes, GoO log vs registry, organic soil reported as "mineral", stale or unit-wrong PACT PCFs, missing transport legs, mode mislabels, draft-report totals…). Legitimate oddities (credit notes, vessel lots in tonnes, seasonal peaks, ammonia) are whitelisted. Every finding gets a confidence, an explanation, the proposed correction and a `needs_expert_review` flag. | `submissions/A1_*.csv`, `A/corrections_log.csv` |
| **A · Inventory** | Corrections → clean canonical tables (silver) → GHG Protocol reference calculator → 2021–2025 inventory (gold), with the factor and source behind every line. Organic soils are included in contract-farm footprints. | `submissions/A2_*.csv`, `A/lines_long.csv`, `A/inventory_lines_2025.csv` |
| **B · Pathways** | 2025 base year adjusted for a full year of Foodhills, plus a 2019 recalculation shown for comparison; FLAG/non-FLAG split; SBTi linear targets (4.2 / 2.5 / 3.03 %/yr); BAU with Pudasjärvi, Kantvik and Foodhills; 30 levers re-computed from the inventory; MACC and pathways under 7 NGFS scenarios. Structural (L05, L26) and measurement (L27) changes are never counted as reductions. | `B/pathways.csv`, `B/levers_recomputed.csv`, `B/targets.csv` |
| **C · Climate risk** | 40,000-draw Monte Carlo per crop/SSP on top of agro-climatic features (GDD phenology, soil-water bucket, stage-wise drought, heat at flowering, waterlogging, harvest rain, blight, pollen beetle) → per-crop LightGBM models with monotone stress constraints + farm skill + trend → 2027–31 yields, 2041–60 risk under each SSP, € shortfall cost, import emissions, FI/SE hedge and adaptation value. | `submissions/C1_*.csv`, `submissions/C2_*.csv`, `C/c3_*.csv` |
| **D · Nature (SBTN)** | Field P and N losses → delivery to water → catchment retention, calibrated on the dev catchments and monitored loads; pressure × state priority; top-50 hotspot parcels with measures and €/kg P; D2 value-chain materiality screening including imports. | `submissions/D1_*.csv`, `D/hotspots_top50.csv`, `D/d2_materiality.csv` |
| **E · AI copilot** | A tool-using Claude agent (inside the published app) that queries the pipeline's tables, searches the evidence index, drafts a board memo, and answers with evidence (record keys, files, standard sections). Retrieval over results and framework docs runs in the browser. An optional OpenAI-compatible LLM (Azure OpenAI in production) only phrases answers from the retrieved evidence. | `submissions/E_answers_submission.csv` |
| **App** | `app/index.html`, a single self-contained file with no server. It has the decision brief, "Why Navigator" business case, what-if lever simulator (auto-closes the SBTi gap at least cost), DQ issue queue with accept/reject, inventory drill-down, pathway/MACC explorer, climate risk, catchment maps, copilot and a method page. Each module has a draft → approved state, and every reviewer action goes to an exportable audit log. | `app/index.html` |

## Run it

```bash
pip install -r requirements.txt
python run_all.py /path/to/APETIT_CLIMATE_NATURE_NAVIGATOR_2026   # ~2 min
open app/index.html
```

The run is deterministic: it re-creates every CSV in `submissions/` byte-identically.

## Results (self-checked on public dev keys / backtests)

| Task | Ours | Package baseline |
|---|---|---|
| A1 issues (2023–24 labels) | **96.0** (P 0.97, R 0.95, type acc. 1.00) | 52.2 |
| A2 inventory 2023 / 2024 | **95.9 / 96.6** | 25.5 / 23.2 |
| C1 yields (leave-year-out backtest 2014–26) | **6.8 %** production MAPE, nRMSE 0.136 | ~11.6 % (farm mean) |
| D1 catchments (6 dev) | **76.7** (leave-one-out 73.5) | 12.0 |
| E dev numeric | **3 / 3** | – |

## Key findings (synthetic company, 2025)

* **The draft 2025 report is wrong by ~300×.** It is the uncleaned pipeline: kWh read as MWh, tonnes keyed as kg, refrigerant grams as kg, and a total that does not add up.
* **2025 inventory:** Scope 1 4,414 t; Scope 2 61 t market-based (963 t location-based); Scope 3 228,011 t (cat 1 91 %). FLAG is **70 %** of the total, so a FLAG target is mandatory.
* **Organic soils are hidden by today's calculator:** 15,774 t, 59 % of Finnish contract-farm emissions. Pea is 1.04 kg CO2e/kg, not 0.17. 27 farms have ≥30 % of their contract area on organic soil.
* **SBTi 2030 (2025 adjusted base):**
  * Scope 1+2 is met with L01 + L07 + L03 (biogas, Bjuv gas → biogas, R404A).
  * Scope 3 non-FLAG and FLAG depend on the rapeseed supplier programme (L13/L14, ~22 kt/yr at €31–52/t) and moving off peat (L11, ~7.9 kt/yr at ~€11/t).
* **Climate:**
  * Weather risk is already here: Finnish pea falls below 80 % of normal in ~1 year in 7 (turnip rape ~1 in 13). Expected shortfall cost is ~€0.46 m/yr (~€1.5 m in a 1-in-10 year). A 40,000-draw Monte Carlo shows only a modest shift to 2041–60.
  * Sourcing peas from two countries cuts expected shortfall cost by 44 % today and by 72 % under SSP2-4.5.
  * Irrigating potato and carrot pays back (+€350 k/yr net).
* **Nature:**
  * Contract parcels deliver 7.6 t P and 91 t N to water. Priority catchments: CA12, CA24, CA14, CS07, CA06.
  * The top-50 hotspot parcels carry 15 % of contract P.

## Production path (Microsoft stack)

* **Lakehouse:** Fabric Lakehouse with bronze = `02_raw_feeds`, silver = clean canonical Delta tables, gold = inventory lines and KPIs.
* **Agent and calculation:** the DQ agent and calculator run as Fabric notebooks and an Azure AI Foundry agent. The issue and approval log is a Delta table.
* **Models:** yield and nutrient models in Azure ML / Fabric Data Science.
* **Copilot:** Azure AI Search over the framework PDFs + Azure OpenAI, fronted by Copilot Studio.
* **Approvals and reporting:** Power Apps approval flow and a Power BI report.
* **Geospatial:** real SYKE and Ruokavirasto layers replace the synthetic geometries without code changes (same schema).

See `METHOD_NOTE.md` for assumptions, limitations and how expert review works.
