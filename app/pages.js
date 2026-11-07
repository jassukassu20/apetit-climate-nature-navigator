// ===================== OVERVIEW =====================
page("overview", "Overview", () => {
  const k = DATA.kpi, b = DATA.pathway?.base?.adjusted_2025 || {};
  const acts = DATA.actions || [];
  return `<div class="hero">
    <h1>Climate &amp; Nature Navigator for Apetit</h1>
    <p style="margin:6px 0 16px;max-width:980px;color:#dfe8e2;font-size:15px">Navigator turns Apetit's raw sustainability data — ERP lines, energy meters, farm surveys, supplier files, weather and catchment data — into <b>checked numbers, SBTi targets, priced climate risk and a nature plan</b>. An AI agent does the heavy lifting; a named expert approves every result before it is used.</p>
    <div class="grid g4">
      <div><div class="big">314×</div><div class="lbl">error in the draft 2025 report, caught and fixed</div></div>
      <div><div class="big">${fmt(k.org_soil_t/1000,1)} kt</div><div class="lbl">farm emissions the current calculator misses (peat soils)</div></div>
      <div><div class="big">€39/t</div><div class="lbl">average cost of the cheapest plan that meets all SBTi targets</div></div>
      <div><div class="big">€${fmt(k.c3_eal_585/1e6,2)} m/yr</div><div class="lbl">weather risk to contract supply, with the hedges that cut it</div></div>
    </div>
    <div class="row" style="margin-top:18px"><button class="btn pri" style="background:#7bd39b;color:#10291c;border:0;font-weight:700;padding:9px 16px;font-size:14px" onclick="startTour()">▶ Take the 3-minute tour</button><span class="lbl">or use the tabs above · synthetic data twin of Apetit (Since AI 2026 package)</span></div>
  </div>
  <h1>Decision brief · 2025 baseline → 2030 targets</h1>
  <p class="lead">One pipeline from raw feeds to decisions: a data-quality agent cleans the 2021–2025 activity data, a reference calculator builds the GHG inventory, scenario models project climate risk to contract farming and SBTi pathways, and an SBTN screen ranks nature hotspots. Every figure has a <span class="src">src</span> tag pointing to its records and factors, and nothing is published until a named expert approves it.</p>
  <div class="flow">
    <div class="st"><b>1 · Raw feeds (bronze)</b><span>${fmt(DATA.meta.n_raw_records)} records, 24 feeds, 2021–2025</span></div><div class="ar">→</div>
    <div class="st"><b>2 · DQ agent</b><span>${fmt(DATA.dq.n_2025)} issues flagged in 2025 · ${fmt(DATA.dq.n_review)} routed to an expert</span></div><div class="ar">→</div>
    <div class="st"><b>3 · Clean tables (silver)</b><span>corrections logged with reason + evidence</span></div><div class="ar">→</div>
    <div class="st"><b>4 · Inventory &amp; models (gold)</b><span>GHG Protocol · SBTi · SBTN · SSP/NGFS</span></div><div class="ar">→</div>
    <div class="st"><b>5 · Expert approval</b><span>sign-off per module, exportable audit log</span></div>
  </div>
  <div class="grid g4" style="margin-top:14px">
    <div class="card kpi"><div class="l">Scope 1 (2025)</div><div class="v">${fmt(k.s1)} t</div><div class="s">combustion + refrigerants ${src(k.src_s1)}</div></div>
    <div class="card kpi"><div class="l">Scope 2 market-based</div><div class="v">${fmt(k.s2m)} t</div><div class="s">location-based ${fmt(k.s2l)} t ${src(k.src_s2)}</div></div>
    <div class="card kpi"><div class="l">Scope 3</div><div class="v">${fmt(k.s3)} t</div><div class="s">cat 1 = ${fmt(100*k.cat1/k.s3,0)} % ${src(k.src_s3)}</div></div>
    <div class="card kpi"><div class="l">FLAG share of total</div><div class="v">${fmt(100*k.flag_share,1)} %</div><div class="s">${fmt(k.flag)} t land-based ${src(k.src_flag)}</div></div>
  </div>
  <div class="grid g4" style="margin-top:14px">
    <div class="card kpi"><div class="l">Hidden in current calculator</div><div class="v">${fmt(k.org_soil_t)} t</div><div class="s">drained organic soils: ${fmt(k.org_soil_share*100,0)} % of FI contract-farm emissions on ~${fmt(k.org_soil_area_share*100,0)} % of area ${src(k.src_org)}</div></div>
    <div class="card kpi"><div class="l">Weather risk to contract supply</div><div class="v">€${fmt(k.c3_eal_585/1e6,2)} m/yr</div><div class="s">expected shortfall cost (SSP5-8.5, 2041–60); 1-in-10 yr €${fmt(k.c3_p90_585/1e6,1)} m; FI+SE pea sourcing −${fmt(100*DATA.climate.hedge.cut245,0)} % ${src(k.src_c3)}</div></div>
    <div class="card kpi"><div class="l">Contract P reaching water</div><div class="v">${fmt(k.p_total/1000,1)} t P</div><div class="s">${fmt(k.n_total/1000,0)} t N · top catchment ${esc(k.top_catchment)} ${src(k.src_d1)}</div></div>
    <div class="card kpi"><div class="l">SBTi 2030 with levers below carbon price (NGFS NDCs)</div><div class="v">${[k.gap2030_s12,k.gap2030_s3,k.gap2030_flag].every(g=>g<=0)?'on track':[["S1+2",k.gap2030_s12],["S3",k.gap2030_s3],["FLAG",k.gap2030_flag]].filter(x=>x[1]>0).map(x=>x[0]).join(" + ")+" gap"}</div><div class="s">S1+2 ${fmt(k.gap2030_s12)} t · S3 non-FLAG ${fmt(k.gap2030_s3)} t · FLAG ${fmt(k.gap2030_flag)} t vs target (negative = met) · closable in Simulator ${src("B/pathways.csv")}</div></div>
  </div>
  <div class="row" style="margin-top:22px"><h2 style="margin:0">What Apetit should do next week</h2><span style="flex:1"></span>${SAMPLE?'<button class="btn pri" onclick="aiMemo()">✨ Draft board memo with AI</button>':''}</div>
  ${acts.map((a,i)=>`<div class="action" style="border-left-color:${COLORS[i%8]}"><b>${i+1}. ${esc(a.title)}</b><div class="m">${esc(a.why)}</div><div class="m"><b style="display:inline">Owner:</b> ${esc(a.owner)} · <b style="display:inline">Size:</b> ${esc(a.size)} · <b style="display:inline">Evidence:</b> <span class="tag">${esc(a.evidence)}</span></div></div>`).join("")}
  <h2 style="margin-top:22px">Review status</h2>
  <div class="card">${table(["dq","inventory","pathways","climate","nature","copilot"].map(m=>({m, a: store.get("approvals",{})[m]})),[
    {h:"Module",f:r=>esc(r.m)},{h:"Status",f:r=>r.a?'<span class="pill ok">approved</span>':'<span class="pill wa">draft</span>'},{h:"Reviewer",f:r=>esc(r.a?.by||"")},{h:"When",f:r=>esc(r.a?.ts?.slice(0,16).replace("T"," ")||"")}])}</div>
  <p class="small muted">Synthetic data (Since AI package v${esc(DATA.meta.package_version)}). Do not present as Apetit's actual emissions. Generated ${esc(DATA.meta.generated)}.</p>`;
});

// ===================== DATA QUALITY =====================
let dqFilter = {type:"", table:"", q:""};
page("dq", "DQ agent", () => {
  const dq = DATA.dq; const dec = store.get("dq_decisions",{});
  const rows = dq.issues.filter(r=>(!dqFilter.type||r.issue_type===dqFilter.type)&&(!dqFilter.table||r.table===dqFilter.table)&&(!dqFilter.q||JSON.stringify(r).toLowerCase().includes(dqFilter.q.toLowerCase())));
  const types = [...new Set(dq.issues.map(r=>r.issue_type))].sort(), tables=[...new Set(dq.issues.map(r=>r.table))].sort();
  const byType = types.map(t=>({t, n:dq.issues.filter(r=>r.issue_type===t).length})).sort((a,b)=>b.n-a.n);
  const nAcc = Object.values(dec).filter(d=>d.d==="accept").length, nRej = Object.values(dec).filter(d=>d.d==="reject").length;
  return `<h1>Data-quality agent</h1>
  <p class="lead">18 detectors (unit slips, duplicates, currency, decimal shifts, meter gaps/spikes, wrong gas codes, GoO vs registry, organic soils reported as mineral, stale/unit-wrong PCFs, missing transport legs, mode mislabels…). Legitimate oddities — credit notes, vessel lots in tonnes, seasonal peaks, ammonia — are explicitly whitelisted. Each flag carries confidence, an explanation and the proposed correction; low-confidence or high-impact flags are routed to an expert.</p>
  ${reviewBar("dq","2025 issue list and proposed corrections.")}
  <div class="grid g4">
    <div class="card kpi"><div class="l">Dev score (2023–24 labels)</div><div class="v">${fmt(dq.dev_score,1)}</div><div class="s">baseline ${fmt(dq.baseline_score,1)} · F1 ${fmt(dq.dev_f1,3)} ${src("tasks/dev/A1_dev_issue_labels_2023_2024.csv, scored with ccn_tools.score")}</div></div>
    <div class="card kpi"><div class="l">2025 issues flagged</div><div class="v">${fmt(dq.n_2025)}</div><div class="s">${fmt(dq.n_review)} need expert review</div></div>
    <div class="card kpi"><div class="l">Inventory impact of cleaning</div><div class="v">${fmt(dq.impact_t)} t</div><div class="s">raw pipeline vs cleaned, 2025 total ${src("A/corrections_log.csv")}</div></div>
    <div class="card kpi"><div class="l">Your decisions</div><div class="v">${nAcc} ✓ / ${nRej} ✗</div><div class="s">stored with reviewer + timestamp</div></div>
  </div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card"><h3>2025 flags by type</h3>${barH(byType,{label:r=>r.t,value:r=>r.n,fmtV:v=>fmt(v)})}</div>
    <div class="card"><h3>Draft 2025 report vs cleaned inventory</h3>${table(dq.draft_check||[],[{h:"Line",k:"line"},{h:"Draft (raw)",n:1,f:r=>fmt(r.draft)},{h:"Cleaned",n:1,f:r=>fmt(r.clean)},{h:"Ratio",n:1,f:r=>fmt(r.ratio,1)+"×"},{h:"Verdict",f:r=>`<span class="pill ${r.ratio>1.05||r.ratio<0.95?'no':'ok'}">${r.ratio>1.05||r.ratio<0.95?'total_mismatch':'ok'}</span>`}])}
    <p class="small muted">The draft summary (data/05_scenarios/draft_report_summary_2025.csv) was typed from the raw pipeline: kWh read as MWh and a decimal shift inflate it by orders of magnitude — exactly what the agent must stop before publication.</p></div>
  </div>
  <div class="card" style="margin-top:14px">
    <div class="row" style="margin-bottom:8px"><b>Issue queue</b>
      <select onchange="dqFilter.type=this.value;render()"><option value="">all types</option>${types.map(t=>`<option ${t===dqFilter.type?'selected':''}>${t}</option>`).join("")}</select>
      <select onchange="dqFilter.table=this.value;render()"><option value="">all tables</option>${tables.map(t=>`<option ${t===dqFilter.table?'selected':''}>${t}</option>`).join("")}</select>
      <input type="text" placeholder="search…" value="${esc(dqFilter.q)}" onchange="dqFilter.q=this.value;render()">
      <span class="muted small">${rows.length} shown</span><span style="flex:1"></span>
      <button class="btn sm" onclick="dqBulk('accept')">Accept all shown ≥0.9 conf.</button></div>
    ${table(rows,[
      {h:"Record key",f:r=>`<span class="tag">${esc(r.record_key)}</span>`},
      {h:"Issue",f:r=>`<span class="pill ${r.confidence>=0.9?'':'wa'}">${esc(r.issue_type)}</span>`},
      {h:"Conf.",n:1,f:r=>fmt(r.confidence,2)},
      {h:"Explanation / evidence",f:r=>esc(r.explanation)},
      {h:"Decision",f:r=>{const d=dec[r.record_key];return d?`<span class="pill ${d.d==='accept'?'ok':'no'}">${d.d}</span> <span class="small muted">${esc(d.by)}</span>`:`<button class="btn sm" onclick="dqDecide('${esc(r.record_key)}','accept')">✓</button> <button class="btn sm" onclick="dqDecide('${esc(r.record_key)}','reject')">✗</button>`}}
    ],{max:600})}
  </div>`;
});
function dqDecide(key, d){ const by=reviewerName(); if(!by){toast("Enter your name in the Reviewer box first.");return;} const x=store.get("dq_decisions",{}); x[key]={d,by,ts:new Date().toISOString()}; store.set("dq_decisions",x); audit("dq_"+d,key,""); render(); }
function dqBulk(d){ const by=reviewerName(); if(!by){toast("Enter your name in the Reviewer box first.");return;} const x=store.get("dq_decisions",{}); DATA.dq.issues.filter(r=>r.confidence>=0.9&&(!dqFilter.type||r.issue_type===dqFilter.type)&&(!dqFilter.table||r.table===dqFilter.table)).forEach(r=>{ if(!x[r.record_key]) x[r.record_key]={d,by,ts:new Date().toISOString()}; }); store.set("dq_decisions",x); audit("dq_bulk_"+d,"filter",JSON.stringify(dqFilter)); render(); }

// ===================== INVENTORY =====================
let invCat = "";
page("inventory", "Inventory", () => {
  const inv = DATA.inventory; const cats = inv.categories;
  const lines = inv.lines.filter(l=>!invCat || l.category===invCat).sort((a,b)=>b.tco2e-a.tco2e);
  const yrs = inv.by_year;
  const series = ["scope1","scope2_market","scope3"].map((s,i)=>({name:s, pts: yrs.filter(r=>r.scope===s).map(r=>[r.year,r.tco2e])}));
  return `<h1>2025 GHG inventory (GHG Protocol, AR6 GWP100)</h1>
  <p class="lead">Operational control, continuing operations; Foodhills (Bjuv) from 1 Dec 2025; Swedish growers enter in 2026. Location- and market-based Scope 2 both reported; biogenic CO2 as a memo item. Click a category to see its line items, the factor used and the number of source records.</p>
  ${reviewBar("inventory","2025 inventory (A2 submission).")}
  <div class="grid g2">
    <div class="card"><h3>By category, tCO2e — click to drill down</h3>
      ${barH(cats,{width:620,label:r=>r.category,value:r=>r.tco2e,color:r=>r.scope==="scope1"?"var(--s1)":r.scope.startsWith("scope2")?"var(--s7)":"var(--s2)",tipFn:r=>`<b>${r.category}</b><br>${fmt(r.tco2e)} t · ${r.scope}<br>${esc(r.method_note||"")}`})}
      <div class="row small">${cats.map(c=>`<button class="btn sm" onclick="invCat='${c.category}';render()">${c.category.replace(/_/g," ")}</button>`).join("")} <button class="btn sm" onclick="invCat='';render()">all</button></div>
      ${legend([{name:"Scope 1",color:"var(--s1)"},{name:"Scope 2",color:"var(--s7)"},{name:"Scope 3",color:"var(--s2)"}])}
    </div>
    <div class="card"><h3>2021–2025 trend, cleaned pipeline</h3>
      ${lineChart(series.filter(s=>s.name!=="scope3"),{yFmt:v=>fmt(v)})}
      ${lineChart(series.filter(s=>s.name==="scope3"),{yFmt:v=>fmt(v/1000)+"k",height:200})}
      <p class="small muted">Validated end-to-end on public 2023/2024 truths: dev A2 score ${fmt(inv.dev_2023,1)} (2023) and ${fmt(inv.dev_2024,1)} (2024) vs naive baseline 25.5 / 23.2.</p></div>
  </div>
  <div class="card" style="margin-top:14px"><h3>Line items ${invCat? "· "+esc(invCat):""} (${lines.length})</h3>
   ${table(lines,[{h:"Category",k:"category"},{h:"Line item",f:r=>`<span class="tag">${esc(r.line_item)}</span>`},{h:"tCO2e",n:1,f:r=>fmtT(r.tco2e)},{h:"Method / factor",k:"basis"}],{max:500})}</div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card"><h3>Organic-soil correction (current calculator vs corrected)</h3>${table(DATA.inventory.org_soil||[],Object.keys((DATA.inventory.org_soil||[{}])[0]||{}).map(k=>({h:k,n:typeof (DATA.inventory.org_soil[0]||{})[k]==="number",f:r=>typeof r[k]==="number"?fmt(r[k],2):esc(r[k])})))}</div>
    <div class="card"><h3>FLAG / non-FLAG split, Scope 3 cat 1</h3>${table(DATA.inventory.flag_split||[],Object.keys((DATA.inventory.flag_split||[{}])[0]||{}).map(k=>({h:k,n:typeof (DATA.inventory.flag_split[0]||{})[k]==="number",f:r=>typeof r[k]==="number"?fmt(r[k],1):esc(r[k])})))}</div>
  </div>`;
});

// ===================== PATHWAYS =====================
let pwScen = "ndcs", pwPort = "cost", pwScope = "s12";
page("pathways", "SBTi & MACC", () => {
  const P = DATA.pathway; const key = pwScen + (pwPort==="all"?"|all_levers":"");
  const rows = P.rows.filter(r=>r.scenario===key);
  const lab = {s12:"Scope 1+2 (market-based)", s3nf:"Scope 3 non-FLAG", flag:"FLAG"};
  const series = [{name:"BAU",pts:rows.map(r=>[r.year,r["bau_"+pwScope]]),color:"var(--ink-3)",dash:1},
                  {name:"With levers",pts:rows.map(r=>[r.year,r["lev_"+pwScope]]),color:"var(--s1)"},
                  {name:"SBTi target",pts:rows.map(r=>[r.year,r["tgt_"+pwScope]]),color:"var(--s6)",dash:1}];
  const r30 = rows.find(r=>r.year===2030)||{};
  const scenOpts = P.scenarios.map(s=>`<option ${s===pwScen?'selected':''}>${s}</option>`).join("");
  const b = P.base;
  const lv = P.levers.filter(l=>l.kind==="abatement");
  const maccScen = P.macc.filter(m=>m.scenario===pwScen); const mm = Object.fromEntries(maccScen.map(m=>[m.id,m]));
  const maccRows = lv.map(l=>({...l, cost: mm[l.id]? mm[l.id].cost_net : l.cost}));
  const cp = maccScen[0]?.carbon_price_2030;
  return `<h1>SBTi targets, pathways and abatement</h1>
  <p class="lead">Base year 2025, structurally adjusted for a full year of Foodhills (recommended under SBTi V2). Targets: Scope 1+2 −4.2 %/yr, Scope 3 non-FLAG −2.5 %/yr, FLAG −3.03 %/yr (linear). BAU includes Pudasjärvi closure (S1/2 → cat 1), Kantvik steam sale (S1 → S2), Foodhills growers and plant-based demand by scenario. Levers were re-computed from the cleaned inventory; structural changes (L05, L26) and measurement improvements (L27) are shown separately and are <b>never</b> counted as reductions.</p>
  ${reviewBar("pathways","Base year choice, targets and lever portfolio.")}
  <div class="grid g3">
    <div class="card"><h3>Base-year options</h3>${table([
      {o:"2025 as reported",s12:b.reported_2025.s1+b.reported_2025.s2m,s3:b.reported_2025.s3,f:b.reported_2025.flag,n:"Foodhills only Dec → not comparable"},
      {o:"2025 adjusted ✓",s12:b.adjusted_2025.s1+b.adjusted_2025.s2m,s3:b.adjusted_2025.s3,f:b.adjusted_2025.flag,n:"recommended (V2: latest comprehensive year)"},
      {o:"2019 recalculated",s12:b.recalc_2019.s1+b.recalc_2019.s2m,s3:b.recalc_2019.s3,f:null,n:"grain trade & Foodhills estimated, no FLAG split"}],
      [{h:"Option",k:"o"},{h:"S1+2",n:1,f:r=>fmt(r.s12)},{h:"S3",n:1,f:r=>fmt(r.s3)},{h:"FLAG",n:1,f:r=>fmt(r.f)},{h:"Note",k:"n"}])}
      <p class="small muted">${esc(P.foodhills_adjustment.basis)}</p></div>
    <div class="card"><h3>Targets 2030 (5-yr, V2) ${src("targets.csv")}</h3>${table(P.targets.filter(t=>[2030,2032,2035].includes(t.year)),[{h:"Year",k:"year"},{h:"S1+2",n:1,f:r=>fmt(r.s12_target)},{h:"S3 non-FLAG",n:1,f:r=>fmt(r.s3nf_target)},{h:"FLAG",n:1,f:r=>fmt(r.flag_target)}])}
      <p class="small muted">V2 coverage: Scope 3 categories ≥ 5 % of Scope 3 — ${Object.entries(P.scope3_category_shares).filter(([k,v])=>v>=0.05).map(([k,v])=>k+" "+fmt(v*100,0)+"%").join(", ")}. Cat 10 (processing of sold oil/meal) screened and excluded with justification.</p></div>
    <div class="card"><h3>Scenario</h3>
      <div class="row"><select onchange="pwScen=this.value;render()">${scenOpts}</select>
      <select onchange="pwPort=this.value;render()"><option value="cost" ${pwPort==="cost"?"selected":""}>levers cheaper than carbon price</option><option value="all" ${pwPort==="all"?"selected":""}>all levers</option></select></div>
      <div class="row" style="margin-top:8px">${Object.keys(lab).map(k=>`<button class="btn sm ${k===pwScope?'pri':''}" onclick="pwScope='${k}';render()">${lab[k]}</button>`).join("")}</div>
      <p class="small">2030 gap to target: <b>${fmt(r30["gap_"+pwScope])} t</b> (${r30["gap_"+pwScope]<=0?'<span class="pill ok">on track</span>':'<span class="pill no">gap</span>'})<br>Carbon price 2030: €${fmt(r30.carbon_price)}/t · ETS2 fuels €${fmt(r30.ets2)}/t<br>Levers used: <span class="tag">${esc(r30.levers||"–")}</span></p></div>
  </div>
  <div class="card" style="margin-top:14px"><h3>${lab[pwScope]} · ${esc(pwScen)}</h3>${lineChart(series,{yFmt:v=>fmt(v),x0:2025,x1:2035,width:1100,height:300})}${legend(series.map(s=>({name:s.name,color:s.color})))}</div>
  <div class="card" style="margin-top:14px"><h3>Marginal abatement cost curve · ${esc(pwScen)} (carbon price 2030 €${fmt(cp)}/t)</h3>${macc(maccRows)}${legend([{name:"Scope 1/2",color:"var(--s1)"},{name:"Scope 3 non-FLAG",color:"var(--s2)"},{name:"FLAG",color:"var(--s3)"}])}</div>
  <div class="card" style="margin-top:14px"><h3>Lever register (recomputed vs design)</h3>${table(P.levers.slice().sort((a,b)=>(a.cost??1e9)-(b.cost??1e9)),[
    {h:"Id",k:"id"},{h:"Lever",k:"name"},{h:"Kind",f:r=>`<span class="pill ${r.kind==='abatement'?'':'wa'}">${r.kind}</span>`},{h:"t/yr",n:1,f:r=>fmt(r.abatement)},{h:"range",n:1,f:r=>fmt(r.low)+"–"+fmt(r.high)},{h:"design",n:1,f:r=>fmt(r.design_abatement)},{h:"€/t",n:1,f:r=>r.cost==null?"–":fmt(r.cost)},{h:"Conf.",k:"confidence"},{h:"Start",k:"start"},{h:"Basis",k:"basis"},{h:"Co-benefits",k:"co_benefits"}])}</div>`;
});

// ===================== CLIMATE RISK =====================
let crScen = "ssp245";
page("climate", "Climate risk", () => {
  const C = DATA.climate;
  const c2 = C.c2.filter(r=>r.scenario===crScen);
  const eur = (C.euro||[]).filter(r=>r.scenario===crScen);
  const hist = C.history||[];
  const keys = ["FI_SW pea","SE_SKANE pea","FI_SW turnip_rape"];
  const roll = pts => pts.map((p,i)=>{ const w = pts.slice(Math.max(0,i-4), i+1); return [p[0], w.reduce((a,x)=>a+x[1],0)/w.length]; });
  const ser = keys.map(k=>({name:k, pts: roll(hist.filter(r=>(r.region+" "+r.crop)===k && (r.scenario==="historical"||r.scenario===crScen)).sort((a,b)=>a.year-b.year).map(r=>[r.year, r.index]))}));
  return `<h1>Climate risk to contract farming</h1>
  <p class="lead">Agro-climatic features mirror crop physiology: stage-specific drought (bucket soil-water by soil class, irrigation), heat at flowering, waterlogging after sowing on clay, harvest rain, season length, late blight and pollen beetle. Models are trained on 2012–2026 farm yields and validated by leave-years-out backtest, then run on 2027–2031 (SSP2-4.5) and, for 2041–2060, a 40,000-draw Monte Carlo per crop and SSP (delta-shifted historical seasons + SSP realisation + calibrated non-weather noise) with today's management and technology frozen at 2025. Key message: the risk is the bad years, and they already happen — the 2041–60 shift is modest.</p>
  ${reviewBar("climate","Yield forecasts (C1), climate risk (C2) and € translation (C3).")}
  <div class="grid g3">
    <div class="card kpi"><div class="l">Backtest, aggregate production MAPE</div><div class="v">${fmt(C.backtest?.agg_mape_pct,1)} %</div><div class="s">region × crop × year, leave-years-out ${src("C/backtest_agg.csv")}</div></div>
    <div class="card kpi"><div class="l">Backtest parcel nRMSE</div><div class="v">${fmt(C.backtest?.nrmse,3)}</div><div class="s">score zero at 0.35</div></div>
    <div class="card kpi"><div class="l">FI–SE pea yield correlation</div><div class="v">${fmt(C.hedge?.corr,2)}</div><div class="s">${esc(C.hedge?.note||"")}</div></div>
  </div>
  <div class="row" style="margin:14px 0">${["ssp126","ssp245","ssp585"].map(s=>`<button class="btn ${s===crScen?'pri':''}" onclick="crScen='${s}';render()">${s.toUpperCase()}</button>`).join("")}</div>
  <div class="grid g2">
    <div class="card"><h3>Mean yield change 2041–60 vs 1991–2020, % (${crScen})</h3>${barH(c2.map(r=>({...r,abs:Math.abs(r.mean_yield_change_pct)})),{label:r=>r.region+" "+r.crop,value:r=>r.abs,fmtV:(v,r)=>(r.mean_yield_change_pct>0?"+":"−")+fmt(v,1)+" %",color:r=>r.mean_yield_change_pct<0?"var(--s8)":"var(--s3)",tipFn:r=>`${r.region} ${r.crop}: ${fmt(r.mean_yield_change_pct,1)} % · P(bad year) ${fmt(100*r.p_bad_year,0)} %`})}
      <p class="small muted">Red = decline, green = gain (bar length = magnitude).</p></div>
    <div class="card"><h3>Probability of a bad year (&lt;80 % of normal)</h3>${barH(c2,{label:r=>r.region+" "+r.crop,value:r=>100*r.p_bad_year,fmtV:v=>fmt(v,0)+" %",color:()=>"var(--s4)"})}</div>
  </div>
  <div class="card" style="margin-top:14px"><h3>€ at risk per year (${crScen}) — shortfall × contract price × replacement premium ${src("C/c3_euro_risk.csv; contract_prices_and_replacement_premiums.csv")}</h3>${table(eur,autoCols(eur,["scenario"]))}</div>
  <div class="card" style="margin-top:14px"><h3>Adaptation options ${src("C/c3_adaptation.csv")}</h3>${table((C.adaptation||[]).filter(r=>(r.scenario===crScen||crScen==="ssp126"&&r.scenario==="ssp245")&&Math.abs(r.net_benefit_eur||0)>1),autoCols(C.adaptation||[]))}<p class="small muted">Irrigation cost assumed €250/ha/yr (replace with Apetit figures). Shown for the selected SSP (SSP1-2.6 shows SSP2-4.5 results).</p></div>
  ${ser.length?`<div class="card" style="margin-top:14px"><h3>Yield index, 5-yr rolling mean, history → ${crScen} (1991–2020 = 100)</h3>${lineChart(ser,{yFmt:v=>fmt(v),yMin:80,yMax:120,width:1100,height:300,marks:[{x:2026,label:"today"}]})}${legend(ser)}</div>`:""}
  <div class="card" style="margin-top:14px"><h3>Explainability: what drives yields</h3>${barH((C.importance||[]).slice(0,14),{width:1100,rowH:22,label:r=>r.crop+" · "+r.feature,value:r=>r.importance,fmtV:v=>fmt(100*v,0)+" % of gain",color:()=>"var(--s7)"})}<p class="small muted">ds_* = drought stress (season / flowering), hot25_flw = heat days at flowering, p_jja = summer rain. Stress features are monotone-constrained: more drought or heat can never raise yield.</p></div>`;
});

// ===================== NATURE =====================
let ntSel = null;
page("nature", "Nature", () => {
  const N = DATA.nature; const pr = N.priority; const maxS = Math.max(...pr.map(r=>r.priority_score));
  const geo = N.geo; const byId = Object.fromEntries(pr.map(r=>[r.catchment_id,r]));
  const tipF = f => { const r = byId[f.properties.catchment_id]||{}; return `<b>${f.properties.catchment_id}</b> · ${f.properties.receiving_water_type} · ${f.properties.ecological_status_class}<br>P ${fmt(r.apetit_p_to_water_kg)} kg · N ${fmt(r.apetit_n_to_water_kg)} kg<br>priority ${fmt(r.priority_score,2)} (rank ${r.priority_rank})`; };
  const fill = f => { const r = byId[f.properties.catchment_id]; return r && r.priority_score>0 ? seqColor(r.priority_score/maxS) : "#eceae4"; };
  const hs = N.hotspots.map(h=>({lat:h.lat,lon:h.lon,r:3.5,color:"var(--s2)",tip:`<b>${h.parcel_id}</b> ${h.crop} ${fmt(h.area_ha,1)} ha<br>${fmt(h.p_kg,1)} kg P · ${esc(h.main_drivers)}<br>→ ${esc(h.recommended)}`}));
  return `<h1>Nature: SBTN-style prioritisation</h1>
  <p class="lead">Field-level phosphorus and nitrogen losses (soil-P test, clay, slope, crop, rainfall 2025, buffer strips, catch crops, drainage, N surplus) → delivery to water by distance → catchment retention. Calibrated on dev catchments and monitored outlet loads. Priority = (P/median P + 0.5·N/median N) × state weight × P-sensitivity.</p>
  ${reviewBar("nature","Catchment ranking (D1), hotspot parcels and value-chain screening (D2).")}
  <div class="grid g4">
    <div class="card kpi"><div class="l">Dev score D1</div><div class="v">${fmt(N.metrics.dev_in_sample.score,1)}</div><div class="s">leave-one-out ${fmt(N.metrics.dev_leave_one_out.score,1)} · baseline ${fmt(N.metrics.dev_baseline.score,1)}</div></div>
    <div class="card kpi"><div class="l">Contract P to water 2025</div><div class="v">${fmt(N.metrics.total_p_kg/1000,2)} t</div><div class="s">${fmt(N.metrics.n_parcels)} contract parcels</div></div>
    <div class="card kpi"><div class="l">Contract N to water 2025</div><div class="v">${fmt(N.metrics.total_n_kg/1000,1)} t</div><div class="s">after retention</div></div>
    <div class="card kpi"><div class="l">Top-50 hotspot parcels</div><div class="v">${fmt(N.hotspots.reduce((a,h)=>a+h.p_kg,0)/N.metrics.total_p_kg*100,0)} %</div><div class="s">of contract P; fix ${fmt(N.hotspots.reduce((a,h)=>a+h.kg_p_avoided,0))} kg P for €${fmt(N.hotspots.reduce((a,h)=>a+h.eur_per_yr,0)/1000)} k/yr</div></div>
  </div>
  <div class="grid g2" style="margin-top:14px">
    <div class="card"><h3>Finland (Säkylä region) — priority (darker = higher), dots = hotspot parcels</h3>${geoMap(geo,{fill,tipFn:tipF,points:hs,filter:f=>f.properties.region==="FI_SW"})}</div>
    <div class="card"><h3>Sweden (Skåne / Halland)</h3>${geoMap(geo,{fill,tipFn:tipF,points:hs,filter:f=>f.properties.region!=="FI_SW"})}
     <h3 style="margin-top:14px">Top-5 catchment programme</h3>${table(N.programme,[{h:"Catchment",k:"catchment_id"},{h:"Parcels",n:1,k:"contract_parcels"},{h:"ha",n:1,f:r=>fmt(r.contract_ha)},{h:"P kg",n:1,f:r=>fmt(r.p_kg)},{h:"P avoided",n:1,f:r=>fmt(r.p_avoided_kg)},{h:"€/yr",n:1,f:r=>fmt(r.eur_yr)},{h:"€/kg P",n:1,f:r=>fmt(r.eur_per_kg_p)}])}</div>
  </div>
  <div class="card" style="margin-top:14px"><h3>Catchment ranking ${src("submissions/D1_catchment_priority_submission.csv")}</h3>${table(pr.slice().sort((a,b)=>a.priority_rank-b.priority_rank),[{h:"Rank",n:1,k:"priority_rank"},{h:"Catchment",k:"catchment_id"},{h:"Region",k:"region"},{h:"P kg",n:1,f:r=>fmt(r.apetit_p_to_water_kg)},{h:"N kg",n:1,f:r=>fmt(r.apetit_n_to_water_kg)},{h:"Score",n:1,f:r=>fmt(r.priority_score,2)}],{max:45})}</div>
  <div class="card" style="margin-top:14px"><h3>Hotspot parcels → measures (pending agronomist review)</h3>${table(N.hotspots,[{h:"Parcel",f:r=>`<span class="tag">${r.parcel_id}</span>`},{h:"Catch.",k:"catchment_id"},{h:"Crop",k:"crop"},{h:"P kg",n:1,f:r=>fmt(r.p_kg,1)},{h:"Drivers",k:"main_drivers"},{h:"Recommended",k:"recommended"},{h:"P avoided",n:1,f:r=>fmt(r.kg_p_avoided,1)},{h:"€/kg P",n:1,f:r=>fmt(r.eur_per_kg_p)},{h:"Status",f:r=>`<span class="pill wa">${esc(r.review_status)}</span>`}])}</div>
  <div class="card" style="margin-top:14px"><h3>D2 · Value-chain materiality screening (SBTN step 1a/1b, incl. imports)</h3>${table(N.d2,[{h:"#",n:1,k:"rank"},{h:"Material",k:"name_en"},{h:"Origin",k:"origin"},{h:"t 2025",n:1,f:r=>fmt(r.t_2025)},{h:"tCO2e",n:1,f:r=>fmt(r.tco2e)},{h:"FLAG",n:1,f:r=>fmt(r.flag_share*100,0)+"%"},{h:"Land",n:1,k:"p_land"},{h:"Water",n:1,k:"p_water"},{h:"Nutr.",n:1,k:"p_nutrients"},{h:"Pest.",n:1,k:"p_pesticides"},{h:"Defor.",n:1,k:"p_deforestation"},{h:"EUDR",f:r=>r.eudr?"in scope":"–"},{h:"SBTN HIC",f:r=>r.sbtn_hic?"yes":"–"},{h:"Score",n:1,f:r=>fmt(r.materiality_score,1)},{h:"Rationale",k:"rationale"}])}</div>`;
});

// ===================== COPILOT (AI agent with tools) =====================
let chat = []; let busy = false;
let SAMPLE = null; (async()=>{ try{ if(window.claude && window.claude.use){ SAMPLE = await window.claude.use("sample"); if(current==="copilot"||current==="overview") render(); } }catch(e){ SAMPLE=null; } })();
const aiMode = () => SAMPLE ? "claude" : (store.get("llm_url","") && store.get("llm_key","") ? "endpoint" : "retrieval");
page("copilot", "AI copilot", () => {
  const mode = aiMode();
  const ex = ["Why is our pea footprint 6× higher than the current calculator says?","Which levers close the FLAG gap cheapest, and what do they cost?","Is soy protein isolate in EUDR scope?","What is the € climate risk for Finnish peas under SSP5-8.5?","Which data issues in 2025 need an expert decision first?","Should we use 2019 or 2025 as SBTi base year?"];
  return `<h1>AI copilot — an agent that answers only with evidence</h1>
  <p class="lead">The copilot is a tool-using agent. It searches the evidence index (results, framework digest, method docs), queries the inventory, levers, pathways, climate and catchment tables, and DQ issues, then answers with citations. Numbers come from the pipeline — the language model may not invent or recompute them. In production: Azure OpenAI in AI Foundry over Azure AI Search.</p>
  ${reviewBar("copilot","Answer set for questions E01–E39 and copilot behaviour.")}
  <div class="row small" style="margin-bottom:10px">Mode: ${mode==="claude"?'<span class="pill ok">Claude agent (live)</span>':mode==="endpoint"?'<span class="pill ok">custom LLM endpoint</span>':'<span class="pill wa">retrieval only (no LLM available in this view)</span>'}</div>
  <div class="grid g2">
    <div class="card"><div class="chat" id="chat">${chat.map(m=>`<div class="msg ${m.r}">${esc(m.t)}${m.tools?`<div class="ev">tools: ${esc(m.tools)}</div>`:""}${m.ev?`<div class="ev">evidence: ${esc(m.ev)}</div>`:""}</div>`).join("") || '<div class="muted">Ask anything about the 2025 data, targets, risks or frameworks. Try:</div>'+ex.map(x=>`<button class="btn sm" style="margin:3px 0;text-align:left" onclick="$('#q').value=this.textContent;ask()">${esc(x)}</button>`).join("<br>")}</div>
      <div class="row" style="margin-top:10px"><input type="text" id="q" style="flex:1" placeholder="Ask a question… (any language)" onkeydown="if(event.key==='Enter')ask()"><button class="btn pri" onclick="ask()" ${busy?"disabled":""}>${busy?"Thinking…":"Ask"}</button></div>
      <details style="margin-top:10px"><summary class="small">Custom OpenAI-compatible endpoint (local file only, e.g. Azure OpenAI / Featherless)</summary>
        <div class="row small" style="margin-top:6px"><input type="text" id="llm_url" placeholder="https://…/v1/chat/completions" value="${esc(store.get('llm_url',''))}" style="flex:1"><input type="text" id="llm_model" placeholder="model" value="${esc(store.get('llm_model',''))}"><input type="text" id="llm_key" placeholder="API key (kept in this browser)" value="${esc(store.get('llm_key',''))}"><button class="btn sm" onclick="store.set('llm_url',$('#llm_url').value);store.set('llm_model',$('#llm_model').value);store.set('llm_key',$('#llm_key').value);toast('Saved');render()">Save</button></div></details>
    </div>
    <div class="card"><h3>Benchmark question set (E)</h3>${table(DATA.qa,[{h:"Id",k:"id"},{h:"Question",k:"question"},{h:"Answer",f:r=>`<b>${esc(r.answer_short||r.answer)}</b> ${esc(r.unit||"")}`},{h:"Evidence",f:r=>`<span class="small muted">${esc(r.evidence)}</span>`}],{max:60})}</div>
  </div>`;
});
function tokenize(s){ return (s.toLowerCase().match(/[a-zåäöü0-9%]+/g)||[]).filter(w=>w.length>2 && !STOP.has(w)); }
const STOP = new Set("the and what was were how many which for from with that this are does did per all incl after why our should".split(" "));
function retrieve(q, k=4){
  const qt = tokenize(q); const docs = DATA.kb;
  const N = docs.length; const df = {}; docs.forEach(d=>new Set(d._t||(d._t=tokenize(d.title+" "+d.text))).forEach(w=>df[w]=(df[w]||0)+1));
  return docs.map(d=>{ let s=0; const tf={}; d._t.forEach(w=>tf[w]=(tf[w]||0)+1); qt.forEach(w=>{ if(tf[w]) s += (1+Math.log(tf[w]))*Math.log(1+N/(df[w]||1)); }); return {d, s: s/Math.sqrt(d._t.length+20)}; })
    .filter(x=>x.s>0).sort((a,b)=>b.s-a.s).slice(0,k).map(x=>x.d);
}
const r1 = v => typeof v==="number" ? Math.round(v*10)/10 : v;
const TOOLS = [
  {name:"search_evidence", description:"Full-text search over computed results, E answers, inventory lines, levers, catchments, materiality, climate results, framework digest and method docs. Returns snippets each with an evidence reference to cite.", inputSchema:{type:"object",properties:{query:{type:"string"}},required:["query"]},
   execute:({query})=>retrieve(query,6).map(d=>({title:d.title,text:d.text.slice(0,900),evidence:d.evidence}))},
  {name:"get_inventory", description:"2025 GHG inventory: KPIs and category totals (tCO2e). Optional category substring returns its top line items with factor/basis.", inputSchema:{type:"object",properties:{category:{type:"string"}}},
   execute:({category})=>({kpi:{scope1:r1(DATA.kpi.s1),scope2_market:r1(DATA.kpi.s2m),scope2_location:r1(DATA.kpi.s2l),scope3:r1(DATA.kpi.s3),flag:r1(DATA.kpi.flag),flag_share:r1(DATA.kpi.flag_share*100)+"%",organic_soil_t:r1(DATA.kpi.org_soil_t)},categories:DATA.inventory.categories.map(c=>({scope:c.scope,category:c.category,tco2e:r1(c.tco2e)})),
     lines: category? DATA.inventory.lines.filter(l=>l.category.includes(category)||String(l.line_item).includes(category)).sort((a,b)=>b.tco2e-a.tco2e).slice(0,25).map(l=>({...l,tco2e:r1(l.tco2e)})):undefined, organic_soil_by_crop: DATA.inventory.org_soil, evidence:"A/lines_long.csv; submissions/A2_inventory_2025_submission.csv"})},
  {name:"get_levers", description:"Decarbonisation lever register recomputed from the inventory: abatement t/yr, range, €/t, start, confidence, basis, co-benefits.", inputSchema:{type:"object",properties:{}},
   execute:()=>DATA.pathway.levers.map(l=>({id:l.id,name:l.name,kind:l.kind,scope:l.scope,flag:l.flag,abatement:l.abatement,low:l.low,high:l.high,eur_per_t:l.cost,annual_cost_eur:l.annual_cost_eur,start:l.start,confidence:l.confidence,basis:l.basis,co_benefits:l.co_benefits}))},
  {name:"get_pathway", description:"SBTi pathway row for an NGFS scenario (net_zero_2050, below_2c, low_demand, delayed_transition, fragmented_world, ndcs, current_policies; append |all_levers for all levers) and year 2025-2035: BAU, with-lever and target values for s12, s3nf, flag and gaps. Also base-year options and targets.", inputSchema:{type:"object",properties:{scenario:{type:"string"},year:{type:"number"}},required:["scenario","year"]},
   execute:({scenario,year})=>({row:DATA.pathway.rows.find(r=>r.scenario===scenario&&r.year===year)||"not found",base:DATA.pathway.base,foodhills_adjustment:DATA.pathway.foodhills_adjustment.basis,evidence:"B/pathways.csv; B/b_results.json"})},
  {name:"get_climate_risk", description:"Climate yield risk 2041-2060 vs 1991-2020 by region (FI_SW, SE_SKANE), crop and SSP: yield change, p_bad_year, € shortfall costs and adaptation options, and the FI-SE hedge.", inputSchema:{type:"object",properties:{crop:{type:"string"},scenario:{type:"string"}}},
   execute:({crop,scenario})=>{ const f=r=>(!crop||r.crop===crop)&&(!scenario||r.scenario===scenario); return {c2:DATA.climate.c2.filter(f),euro:DATA.climate.euro.filter(f),adaptation:DATA.climate.adaptation.filter(f).slice(0,10),hedge:DATA.climate.hedge,evidence:"submissions/C2_climate_yield_risk_submission.csv; C/c3_euro_risk.csv; C/c3_adaptation.csv"}; }},
  {name:"get_nature", description:"SBTN catchment priorities (P/N kg to water, score, rank), top-5 programme, hotspot parcels and D2 materiality screening. Optional catchment_id.", inputSchema:{type:"object",properties:{catchment_id:{type:"string"}}},
   execute:({catchment_id})=>({metrics:DATA.nature.metrics,priority:DATA.nature.priority.filter(r=>!catchment_id||r.catchment_id===catchment_id).sort((a,b)=>a.priority_rank-b.priority_rank).slice(0,12),programme:DATA.nature.programme,hotspots:DATA.nature.hotspots.filter(h=>!catchment_id||h.catchment_id===catchment_id).slice(0,10),d2_top:DATA.nature.d2.slice(0,8).map(d=>({name:d.name_en,origin:d.origin,t:d.t_2025,tco2e:d.tco2e,rank:d.rank,rationale:d.rationale})),evidence:"submissions/D1_*.csv; D/hotspots_top50.csv; D/d2_materiality.csv"})},
  {name:"get_dq_issues", description:"2025 data-quality flags from the DQ agent with confidence and explanation; optional issue_type filter; also counts by type and the draft-report check.", inputSchema:{type:"object",properties:{issue_type:{type:"string"}}},
   execute:({issue_type})=>{ const is=DATA.dq.issues; const by={}; is.forEach(i=>by[i.issue_type]=(by[i.issue_type]||0)+1); return {counts:by,needs_review:DATA.dq.n_review,draft_check:DATA.dq.draft_check,issues:is.filter(i=>!issue_type||i.issue_type===issue_type).slice(0,20),evidence:"submissions/A1_issues_submission.csv; A/corrections_log.csv"}; }},
];
const SYS = `You are the Climate & Nature Navigator copilot for Apetit (Finnish food company: frozen vegetables, rapeseed oil, contract farmers in Finland and Sweden). The data is a synthetic twin (Since AI 2026 package) — say so if the user may mistake it for real figures.
Rules: 1) Use the tools to get facts; never answer numbers from memory and never invent or recompute figures beyond simple arithmetic you show. 2) Cite evidence for every claim as [evidence: ...] using the evidence strings returned by tools. 3) Follow GHG Protocol, SBTi (incl. FLAG), SBTN and NGFS logic; methodology changes and structural changes are never emission reductions. 4) If tools return nothing relevant, say you have no evidence and suggest asking an expert. 5) Be concise and decision-oriented: answer first, then 2-4 supporting points, then evidence. 6) Answer in the language of the question.`;
async function ask(){
  const q = $("#q").value.trim(); if(!q||busy) return; chat.push({r:"u",t:q}); audit("copilot_question","",q);
  const mode = aiMode();
  if(mode==="claude"){
    busy=true; const msg={r:"a",t:"Thinking…",tools:""}; chat.push(msg); render();
    const used=[]; const tools = TOOLS.map(t=>({...t, execute:(inp)=>{ used.push(t.name); msg.tools=used.join(", "); return t.execute(inp||{}); }}));
    const hist = chat.filter(m=>m!==msg).slice(-8).map(m=>({role:m.r==="u"?"user":"assistant",content:m.t}));
    hist[hist.length-1].content = SYS + "\n\nQuestion: " + q;
    try{
      const res = await SAMPLE(hist,{tools, cache:false, modelTier:"default", onText:({text})=>{ msg.t=text; const c=$("#chat"); if(c){ const els=c.querySelectorAll(".msg.a"); const el=els[els.length-1]; if(el) el.firstChild.textContent=text; } }});
      msg.t = res.text || msg.t;
    }catch(e){ const h=retrieve(q)[0]; msg.t = (e.code==="not_granted"?"AI access was not granted in this view. ":"AI call failed ("+(e.message||e.code)+"). ")+(h?"Best evidence found:\n\n"+h.text:""); msg.ev=h?.evidence; }
    busy=false; render(); setTimeout(()=>{ const c=$("#chat"); if(c) c.scrollTop=c.scrollHeight; },0); return;
  }
  const hits = retrieve(q);
  if(!hits.length){ chat.push({r:"a",t:"I found no evidence in the package for that. I will not guess — please rephrase or ask an expert."}); render(); return; }
  if(mode==="endpoint"){
    busy=true; chat.push({r:"a",t:"…thinking with "+hits.length+" evidence snippets"}); render();
    try{
      const ctx = hits.map((h,i)=>`[${i+1}] ${h.title}\n${h.text}\nEVIDENCE: ${h.evidence}`).join("\n\n");
      const res = await fetch(store.get("llm_url",""),{method:"POST",headers:{"Content-Type":"application/json","Authorization":"Bearer "+store.get("llm_key","")},body:JSON.stringify({model:store.get("llm_model",""),temperature:0,messages:[{role:"system",content:SYS+" Answer ONLY from the numbered evidence; cite [n]."},{role:"user",content:`Evidence:\n${ctx}\n\nQuestion: ${q}`}]})});
      const js = await res.json(); chat.pop();
      chat.push({r:"a",t:js.choices?.[0]?.message?.content || JSON.stringify(js).slice(0,400), ev: hits.map((h,i)=>`[${i+1}] ${h.evidence}`).join(" | ")});
    }catch(e){ chat.pop(); chat.push({r:"a",t:"LLM call failed ("+e.message+"). Retrieved evidence:\n\n"+hits[0].text, ev:hits[0].evidence}); }
    busy=false;
  } else {
    const h = hits[0]; chat.push({r:"a",t:h.text + (hits.length>1? `\n\nRelated: ${hits.slice(1).map(x=>x.title).join(" · ")}`:""), ev:h.evidence});
  }
  render(); setTimeout(()=>{ const c=$("#chat"); if(c) c.scrollTop=c.scrollHeight; $("#q")?.focus(); },0);
}
async function aiMemo(){
  if(!SAMPLE){ toast("AI is not available in this view"); return; }
  const ap = store.get("approvals",{});
  const status = ["dq","inventory","pathways","climate","nature"].map(m=>`${m}: ${ap[m]?"APPROVED by "+ap[m].by:"DRAFT (not approved)"}`).join("; ");
  const facts = {kpi:DATA.kpi, actions:DATA.actions, scores:DATA.scores, base:DATA.pathway.base, targets:DATA.pathway.targets.filter(t=>[2030,2035].includes(t.year)), hedge:DATA.climate.hedge, nature:DATA.nature.metrics, programme:DATA.nature.programme, assumptions:DATA.assumptions};
  showModal("AI board memo", "Drafting…"); 
  try{
    const res = await SAMPLE(`Write a one-page board memo (max 450 words) for Apetit's management team titled "Climate & nature: decisions for Q1 2027". Structure: Situation (3 bullets) / Decisions requested (numbered, each with owner, t CO2e and €) / Risks & assumptions / Review status. Use ONLY the facts in this JSON; quote numbers as given (round sensibly); state that figures come from a synthetic data twin; for every module whose status is DRAFT, mark the related numbers "(draft – pending expert approval)". Review status: ${status}.\nFACTS JSON:\n${JSON.stringify(facts).slice(0,60000)}`, {cache:false, onText:({text})=>{ const t=document.querySelector("#modal textarea"); if(t) t.value=text; }});
    const t=document.querySelector("#modal textarea"); if(t) t.value=res.text; audit("ai_memo","overview",status);
  }catch(e){ const t=document.querySelector("#modal textarea"); if(t) t.value="AI call failed: "+(e.message||e.code); }
}
function showModal(title, txt){
  document.getElementById("modal")?.remove();
  const m = document.createElement("div"); m.id="modal";
  m.innerHTML = `<div style="position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:200;display:flex;align-items:center;justify-content:center" onclick="if(event.target===this)this.parentNode.remove()"><div class="card" style="width:min(860px,92vw)"><div class="row"><b>${esc(title)}</b><span style="flex:1"></span><button class="btn pri sm" id="cpy">Copy</button><button class="btn sm" onclick="document.getElementById('modal').remove()">Close</button></div><textarea style="width:100%;height:60vh;margin-top:8px;font:13px/1.5 system-ui" ></textarea></div></div>`;
  document.body.appendChild(m); m.querySelector("textarea").value = txt;
  m.querySelector("#cpy").onclick = async () => { const v=m.querySelector("textarea").value; try{ await navigator.clipboard.writeText(v); toast("Copied"); }catch(e){ m.querySelector("textarea").select(); toast("Press Ctrl/Cmd+C to copy"); } };
}

// ===================== SIMULATOR =====================
let simScen = "ndcs"; let simSel = null; let simScale = {};
function simDefault(){ const s=DATA.pathway.macc.filter(m=>m.scenario===simScen); const cp=s[0]?.carbon_price_2030||100; simSel={}; s.forEach(m=>{ if(m.cost_net<=cp) simSel[m.id]=true; }); simScale={}; }
function simRun(){
  const rows = DATA.pathway.rows.filter(r=>r.scenario===simScen); const L = DATA.pathway.levers.filter(l=>l.kind==="abatement");
  return rows.map(r=>{ const red={s12:0,s3nf:0,flag:0};
    L.forEach(l=>{ if(!simSel[l.id]||r.year<l.start) return; const a=l.abatement*(simScale[l.id]||1)*Math.min(1,(r.year-l.start+1)/Math.max(l.ramp,1));
      if(l.scope.startsWith("scope1")||l.scope.startsWith("scope2")) red.s12+=a; else if(l.flag && ["L13","L14","L15","L16","L17"].includes(l.id)){ red.flag+=a*0.86; red.s3nf+=a*0.14; } else if(l.flag) red.flag+=a; else red.s3nf+=a; });
    return {...r, sim_s12:r.bau_s12-red.s12, sim_s3nf:r.bau_s3nf-red.s3nf, sim_flag:r.bau_flag-red.flag}; });
}
function simAuto(){
  // greedy marginal-cost: repeatedly take the cheapest step (enable at 1x, or scale to 1.5x/2x at a cost penalty)
  // that serves a scope whose 2030 or 2035 target is still missed.
  const mm = Object.fromEntries(DATA.pathway.macc.filter(m=>m.scenario===simScen).map(m=>[m.id,m.cost_net]));
  const L = DATA.pathway.levers.filter(l=>l.kind==="abatement");
  const key = l => (l.scope.startsWith("scope1")||l.scope.startsWith("scope2"))? "s12" : (["L13","L14","L15","L16","L17"].includes(l.id)? "flag" : (l.flag?"flag":"s3nf"));
  simSel={}; simScale={};
  const gaps = () => { const r=simRun(); const g={s12:0,s3nf:0,flag:0}; [2030,2035].forEach(y=>{ const x=r.find(z=>z.year===y); for(const k in g) g[k]=Math.max(g[k], x["sim_"+k]-x["tgt_"+k]); }); return g; };
  for(let it=0; it<80; it++){
    const g = gaps(); if(Object.values(g).every(v=>v<=0)) break;
    const acts = [];
    L.forEach(l=>{ const k=key(l); const serves = g[k]>0 || (l.id==="L13"||l.id==="L14"||l.id==="L16") && (g.flag>0||g.s3nf>0); if(!serves) return;
      const cur = simSel[l.id]? (simScale[l.id]||1) : 0; const next = cur===0?1: cur===1?1.5: cur===1.5?2: null; if(next==null) return;
      acts.push({l, next, eff: mm[l.id] * (next>1 ? next : 1) + (next>1? 15:0)}); });
    if(!acts.length) break;
    acts.sort((a,b)=>a.eff-b.eff); const a=acts[0]; simSel[a.l.id]=true; if(a.next>1) simScale[a.l.id]=a.next;
  }
  audit("simulator_autoclose", simScen, JSON.stringify({simSel,simScale})); render();
}
page("simulator", "Simulator", () => {
  if(!simSel) simDefault();
  const R = simRun(); const L = DATA.pathway.levers.filter(l=>l.kind==="abatement"); const mm = Object.fromEntries(DATA.pathway.macc.filter(m=>m.scenario===simScen).map(m=>[m.id,m.cost_net]));
  const cost = L.filter(l=>simSel[l.id]).reduce((a,l)=>a+l.annual_cost_eur*(simScale[l.id]||1),0);
  const ab = L.filter(l=>simSel[l.id]).reduce((a,l)=>a+l.abatement*(simScale[l.id]||1),0);
  const cp = DATA.pathway.macc.find(m=>m.scenario===simScen)?.carbon_price_2030;
  const lab = {s12:"Scope 1+2",s3nf:"Scope 3 non-FLAG",flag:"FLAG"};
  const gap = (y,k) => { const x=R.find(z=>z.year===y); return x["sim_"+k]-x["tgt_"+k]; };
  const card = k => `<div class="card"><h3>${lab[k]}</h3>${lineChart([{name:"BAU",pts:R.map(r=>[r.year,r["bau_"+k]]),color:"var(--ink-3)",dash:1},{name:"Your plan",pts:R.map(r=>[r.year,r["sim_"+k]]),color:"var(--s1)"},{name:"Target",pts:R.map(r=>[r.year,r["tgt_"+k]]),color:"var(--s6)",dash:1}],{width:420,height:220,x0:2025,x1:2035,yFmt:v=>fmt(v/1000,1)+"k"})}
    <p class="small">2030 gap <b>${fmt(gap(2030,k))} t</b> ${gap(2030,k)<=0?'<span class="pill ok">met</span>':'<span class="pill no">gap</span>'} · 2035 gap <b>${fmt(gap(2035,k))} t</b> ${gap(2035,k)<=0?'<span class="pill ok">met</span>':'<span class="pill no">gap</span>'}</p></div>`;
  return `<h1>What-if simulator · build your own transition plan</h1>
  <p class="lead">Digital-twin of the pathway: switch levers on or off and scale them, under any NGFS scenario, and see in real time whether the SBTi targets for Scope 1+2, Scope 3 non-FLAG and FLAG are met in 2030 and 2035, and what it costs. "Auto-close the gap" picks the cheapest levers first and flags any lever scaled beyond its design estimate for expert validation.</p>
  <div class="row" style="margin-bottom:12px"><select onchange="simScen=this.value;simDefault();render()">${DATA.pathway.scenarios.map(s=>`<option ${s===simScen?'selected':''}>${s}</option>`).join("")}</select>
    <button class="btn" onclick="simDefault();render()">Levers below carbon price (€${fmt(cp)}/t)</button><button class="btn" onclick="simSel={};simScale={};render()">None</button><button class="btn pri" onclick="simAuto()">Auto-close the gap</button>
    <span class="small muted">Plan: ${Object.keys(simSel).filter(k=>simSel[k]).length} levers · ${fmt(ab)} tCO2e/yr at full ramp · €${fmt(cost/1e6,2)} m/yr · avg €${fmt(ab?cost/ab:0)}/t</span></div>
  <div class="grid g3">${card("s12")}${card("s3nf")}${card("flag")}</div>
  <div class="card" style="margin-top:14px">${table(L.slice().sort((a,b)=>mm[a.id]-mm[b.id]),[
    {h:"On",f:r=>`<input type="checkbox" ${simSel[r.id]?"checked":""} onchange="simSel['${r.id}']=this.checked;render()">`},
    {h:"Id",k:"id"},{h:"Lever",k:"name"},{h:"Scope",f:r=>r.flag?"FLAG":r.scope},{h:"t/yr",n:1,f:r=>fmt(r.abatement*(simScale[r.id]||1))},{h:"net €/t",n:1,f:r=>fmt(mm[r.id])},{h:"Start",k:"start"},{h:"Conf.",k:"confidence"},
    {h:"Scale",f:r=>`<select onchange="simScale['${r.id}']=+this.value;render()">${[0.5,1,1.5,2].map(v=>`<option value="${v}" ${(simScale[r.id]||1)===v?'selected':''}>${v}×</option>`).join("")}</select>${(simScale[r.id]||1)>1?' <span class="pill wa">beyond design — validate</span>':''}`}],{max:40})}</div>`;
});

// ===================== BUSINESS CASE =====================
page("value", "Why Navigator", () => {
  const v = DATA.value;
  return `<h1>Why Apetit should adopt the Navigator</h1>
  <p class="lead">What the Navigator gives Apetit, and the evidence for each point. Every figure links to the pipeline outputs. The data is a synthetic twin, so the € and t figures show the order of magnitude to expect on Apetit's own data.</p>
  <div class="grid g3">${v.points.map((p,i)=>`<div class="card" style="border-top:4px solid ${COLORS[i%8]}"><div class="kpi"><div class="v">${esc(p.big)}</div><div class="l">${esc(p.small)}</div></div><h2 style="margin-top:10px">${esc(p.title)}</h2><p class="small">${esc(p.text)}</p><p class="small muted">Evidence: <span class="tag">${esc(p.evidence)}</span></p></div>`).join("")}</div>
  <div class="card" style="margin-top:14px"><h3>Compliance calendar the Navigator is built for</h3>${table(v.calendar,[{h:"Date",k:"date"},{h:"What",k:"what"},{h:"How the Navigator helps",k:"how"}])}</div>`;
});
// ===================== METHOD =====================
page("method", "Method", () => {
  const log = store.get("audit",[]);
  return `<h1>Method, assumptions and audit trail</h1>
  <div class="grid g2">
    <div class="card"><h3>How expert review works</h3><ol class="small">
      <li>The agent proposes; it never overwrites bronze data. Each correction is a row: record_key, field, old → new value, rule, evidence, confidence, proposed_by.</li>
      <li>Low-confidence flags (&lt;0.9) and anything that moves a category by &gt;1 % are routed to an expert queue (Data quality tab).</li>
      <li>Each module (inventory, pathways, climate, nature, copilot) has a draft → approved state with reviewer name and timestamp; nothing is published while in draft.</li>
      <li>"Export audit log" writes approvals, issue decisions and every reviewer action as JSON — in production a Delta table in the Fabric Lakehouse.</li>
      <li>Gold numbers are reproducible from bronze + approved corrections with one command: <span class="tag">python run_all.py</span>.</li></ol></div>
    <div class="card"><h3>Production path on Apetit's Microsoft stack</h3>${table(DATA.stack,[{h:"Layer",k:"layer"},{h:"Hackathon",k:"now"},{h:"Apetit production",k:"prod"}])}</div>
  </div>
  <div class="card" style="margin-top:14px"><h3>Key assumptions &amp; limitations</h3><ul class="small">${DATA.assumptions.map(a=>`<li>${esc(a)}</li>`).join("")}</ul></div>
  <div class="card" style="margin-top:14px"><h3>Auto-scored results (dev / backtest)</h3>${table(DATA.scores,[{h:"Task",k:"task"},{h:"Ours",n:1,f:r=>esc(r.ours)},{h:"Baseline",n:1,f:r=>esc(r.baseline)},{h:"How measured",k:"how"}])}</div>
  <div class="card" style="margin-top:14px"><h3>Audit log in this browser (${log.length})</h3>${table(log.slice().reverse(),[{h:"Time",f:r=>esc(r.ts.slice(0,19).replace("T"," "))},{h:"Reviewer",k:"reviewer"},{h:"Action",k:"action"},{h:"Target",k:"target"},{h:"Detail",k:"detail"}],{max:200})}</div>`;
});

// tab order
{ const ORDER=["overview","value","dq","inventory","pathways","simulator","climate","nature","copilot","method"]; PAGES.sort((a,b)=>ORDER.indexOf(a.id)-ORDER.indexOf(b.id)); }

// ===================== GUIDED TOUR =====================
const TOUR = [
 ["overview","The decision brief: what Apetit should do next, each action with an owner, tonnes CO2e and euros."],
 ["value","Why it matters: eight business reasons, each backed by evidence from the pipeline."],
 ["dq","Step 1 · The AI data-quality agent found the errors in the 2025 data. An expert accepts or rejects each flag (type your name top-right, then click ✓)."],
 ["inventory","Step 2 · The cleaned 2025 GHG inventory. Click any category to see each line, its emission factor and its source."],
 ["pathways","Step 3 · SBTi targets incl. FLAG, under 7 climate-policy scenarios, with the cost curve of reduction measures (hover the bars)."],
 ["simulator","Step 4 · Try it: click “Auto-close the gap” — the cheapest set of measures that meets every SBTi target."],
 ["climate","Step 5 · Climate risk to contract farming in euros, per climate scenario, and which adaptations pay back."],
 ["nature","Step 6 · Where nutrient losses hit lakes and rivers hardest, and which 50 fields to fix first (hover the map)."],
 ["copilot","Step 7 · Ask the AI copilot anything — in any language. It answers only with evidence and cites its sources."],
 ["method","Step 8 · How it works: assumptions, scores against the answer keys, the Microsoft production path and the audit log."],
];
let tourIdx = -1;
function startTour(){ tourIdx = 0; go(TOUR[0][0]); }
function tourStep(d){ tourIdx = Math.max(0, Math.min(TOUR.length-1, tourIdx+d)); go(TOUR[tourIdx][0]); }
function endTour(){ tourIdx = -1; renderTour(); }
window.renderTour = function(){
  const el = document.getElementById("tourbar"); if(!el) return;
  if(tourIdx<0){ el.innerHTML=""; document.body.style.paddingBottom="0"; return; }
  const i = TOUR.findIndex(t=>t[0]===current); if(i>=0) tourIdx=i;
  document.body.style.paddingBottom="90px";
  el.innerHTML = `<div class="in"><b style="white-space:nowrap">${tourIdx+1} / ${TOUR.length}</b><span style="flex:1">${esc(TOUR[tourIdx][1])}</span>
    <button class="btn sm" onclick="tourStep(-1)" ${tourIdx===0?"disabled":""}>◂ Back</button>
    ${tourIdx<TOUR.length-1?'<button class="btn pri sm" onclick="tourStep(1)">Next ▸</button>':'<button class="btn pri sm" onclick="endTour()">Finish ✓</button>'}
    <button class="btn sm" onclick="endTour()">✕</button></div>`;
};
