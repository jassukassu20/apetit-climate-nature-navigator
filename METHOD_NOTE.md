# Method note: Climate & Nature Navigator

**Data sources.**
* Since AI synthetic package v1.0.0, used entirely as provided: the Apetit sample, master data, raw feeds 2021–2025, farm survey, Foodhills file, crop history and plan, daily weather 1991–2060 (historical + SSP1-2.6/2-4.5/5-8.5), catchments, monitored loads, scenarios, levers, prices, framework digest.
* No external data was used. Frameworks: GHG Protocol (Corporate, Scope 2, Scope 3, LSR), SBTi CNZS V1.3.1/V2 + FLAG, SBTN Steps 1–2, NGFS Phase V, IPCC 2019 / AR6 GWP100.

**Pipeline.**
* Bronze (raw feeds) → DQ agent findings → approved corrections → silver (canonical clean tables) → gold (inventory lines, pathways, risk, priorities).
* Gold is fully reproducible from bronze plus the corrections log (`python run_all.py <package>`).

**How expert review works.**
1. The agent never overwrites source data. Each correction is logged with record_key, field, old → new value, rule, evidence, confidence and a `needs_expert_review` flag.
   * 223 of 759 findings are routed to an expert.
   * Routing criteria: low confidence, soil misreports, PCF rejections, and estimates that change a category.
2. In the app, an expert accepts or rejects each flag. Each module (DQ, inventory, pathways, climate, nature, copilot) stays **Draft** until a named reviewer approves it. Approvals record reviewer, time and data version.
3. "Export audit log" writes every decision as JSON. In production this is a Delta table behind a Power Apps approval flow.
4. The copilot answers only from retrieved evidence and cites it. Numeric answers come from the pipeline, never from the language model.

**Key assumptions (all flagged in the app).**
* **Soil map:** the organic-soil share from the soil map (~88 % accurate) is scaled ×1.17, calibrated on the 2023–24 truths. It should be replaced by Apetit's parcel register.
* **Meter gaps:** gap-filled meter months are capped at the GoO volume where they overshoot by less than 10 %.
* **Foodhills full year:**
  * Bjuv natural gas: 7,300 MWh.
  * Swedish growers computed from the Foodhills file on mineral soil.
* **Pudasjärvi:** after closure, its S1+S2 is re-booked as cat 1 contract manufacturing.
* **Kantvik steam:** after the sale, purchased steam is assumed at 0.02 t/MWh.
* **Lever costs:** capex annualised at 6 %, plus opex delta, less the ETS2 fuel price for fuel levers. Uncertainty bands are ±20 / 40 / 60 % by confidence level.
* **Yields:** technology and management are frozen at 2025 for C2. Bad-year variance is re-scaled ×1.0–1.24 from the backtest.
* **Climate costs:** prices and premiums are held at 2026 values. Irrigation is costed at €250/ha/yr.
* **Nutrients:** an export-coefficient model with one global P scale and one N scale, fitted on 6 dev catchments; expect about ±10 % error. Measure costs are indicative.

**Limitations.**
* Synthetic data throughout.
* Carbon prices are illustrative NGFS-range values; use IIASA NGFS data before deciding.
* One weather realisation per SSP; no CO2 fertilisation.
* No removals are reported. Catch-crop removals would need GHG Protocol LSR monitoring.
* Scope 3 category 10 is screened but not calculated.
* The 2019 base year cannot be split into FLAG / non-FLAG.

**Method changes are not reductions.** Switching from spend-based to supplier-specific factors (L27), and structural changes (Pudasjärvi, Kantvik), trigger base-year recalculation checks. They are excluded from abatement.
