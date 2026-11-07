# sinceai.app submission texts

Copy each block into the matching field.

## Project name (max 80)

Climate & Nature Navigator

## Tagline (max 140)

Catches the typos that make Apetit's climate report 314× wrong, finds the peat emissions it misses, and tells who should act.

## Built with (first five show as chips)

Python, pandas, LightGBM, JavaScript, Claude, scikit-learn, NumPy, GitHub Pages

## About the project (max 5,000)

**The problem.** Apetit's climate footprint is built by hand from thousands of purchase lines, meter readings, shipments and farm surveys. One unit slip ruins it: in the 2025 draft report, kilowatt-hours read as megawatt-hours and tonnes typed as kilos make Scope 3 314 times too high. And the biggest farm emission source is not counted at all: drained peat fields, which the current farm calculator treats as ordinary mineral soil. Apetit has committed to science-based targets, which are due by December 2027, and from 1 January 2027 the GHG Protocol Land Sector standard requires drained peat to be counted.

**Our solution.** Navigator turns fragmented climate and nature data into decisions in five steps:
1. **Checks every number.** A data-quality agent covering 18 issue types finds wrong units, slipped decimals, kronor booked as euros, double postings, wrong products, misreported soils and more. Each error is shown as "was → should be" with the reason and its impact in euros and tonnes. On Apetit's labelled 2023–24 errors it scores 96/100 (package baseline 52).
2. **Lets anyone add data and checks it instantly.** Type one purchase or one farm's survey answer, or drop a whole CSV; Navigator compares it with the supplier's usual prices and amounts, normal yields, the parcel register and the soil map, and proposes the correction.
3. **Finds what is missing.** Drained peat is 59 % of contract-farm emissions. 23 of 356 farms make half of them. Navigator plans an adviser route from the Säkylä plant (about 470 km, 8 days) and prints a one-page farm plan (English or Finnish) with an on-site soil check that turns the estimate into a verified number.
4. **Finds the cheapest way to the targets.** SBTi pathways for Scope 1+2, Scope 3 and FLAG under seven NGFS scenarios; "Find cheapest plan" closes every gap at least cost and flags anything beyond its design estimate.
5. **Prices climate and nature risk.** Yield models learned from 15 seasons of farm data price bad years in euros (about €0.46M a year today); buying peas from both Finland and Sweden cuts the expected pea shortfall cost by 44 %. Phosphorus losses to water are mapped to the top five catchments with a costed programme.

Every number links to its source file and record. Accepting or rejecting a fix, or recording a soil check, changes the inventory at once. Nothing reaches a report until a named expert approves it, and every decision is logged. "Ask Navigator" answers in any language from the pipeline's own tables, with sources, and takes the user to the right place in the app.

**How we built it.** A Python pipeline (pandas, NumPy, scikit-learn, LightGBM) rebuilds everything from the raw package files with one command in about two minutes, deterministically, and writes the auto-scored outputs for tasks A1–E. The app is a single offline HTML file (vanilla JavaScript, SVG charts, embedded fonts), published with GitHub Pages. The copilot uses Claude with tool calls into the computed tables; in production it maps to Azure OpenAI, and the pipeline maps to Microsoft Fabric.

**What we met on the way.** The planted errors interact: a currency error can look like a decimal slip, and a real credit note can look like an error. We tested every detector against the labelled 2023 and 2024 errors before trusting it. The soil map is only about 88 % accurate, so the peat estimate is shown as temporary and replaced farm by farm by on-site checks.

**What is real and what is simulated.** All data is the synthetic Apetit twin from the Since AI package. The methods, checks and code are real and run on any file with the same columns. No Apetit confidential data is used.

**What comes next.** A pilot with Apetit's field advisers this winter on real parcel and survey data: verify the peat on the 23 farms, lock a complete base year before the land standard applies, and run Navigator on Apetit's Microsoft Fabric.

## GenAI tools used

Claude (Anthropic) and Claude Code for analysis, coding and copy. The app's copilot calls Claude through the artifact runtime when available and falls back to local evidence search.

## Pre-existing code

None. All code was written at the event. The package's own `ccn_tools` (reference calculator and scorer) is used as provided.
