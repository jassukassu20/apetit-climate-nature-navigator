// ============ shared vocabulary & live state ============
const CROP={pea:"Pea",turnip_rape:"Turnip rape",spinach:"Spinach",potato:"Potato",carrot:"Carrot"};
const CROP_FI={pea:"herne",turnip_rape:"rypsi",spinach:"pinaatti",potato:"peruna",carrot:"porkkana"};
const REGION={FI_SW:"SW Finland",SE_SKANE:"Skåne, Sweden"};
const SCEN={net_zero_2050:"Net zero 2050",below_2c:"Below 2 °C",low_demand:"Low demand",delayed_transition:"Delayed transition",fragmented_world:"Fragmented world",ndcs:"Current pledges (NDCs)",current_policies:"Current policies"};
const SSP={ssp126:"Low emissions (SSP1-2.6)",ssp245:"Middle road (SSP2-4.5)",ssp585:"High emissions (SSP5-8.5)"};
const FAM={unit_error:["×1000","Wrong unit"],decimal_shift:["×10","Decimal point"],currency_error:["×11","Currency"],duplicate_record:["×2","Posted twice"],material_mismatch:["≠","Wrong product"],
  soil_misreport:["peat","Soil reported wrong"],area_mismatch:["ha","Area mismatch"],mode_mislabel:["≠","Transport mode"],pcf_stale_period:["old","Supplier footprint outdated"],pcf_unit_error:["×1000","Supplier footprint unit"],
  missing_leg:["+","Missing transport leg"],missing_record:["+","Missing month"],outlier_implausible:["!","Impossible value"],coordinate_swap:["⇄","Coordinates swapped"],certificate_mismatch:["≠","Green-power certificate"],
  meter_spike:["!","Meter spike"],wrong_gas_code:["≠","Refrigerant code"],total_mismatch:["Σ","Totals don't add up"]};
const TABLE={erp_purchase_lines:"Purchase line",farm_survey:"Farm survey",commuting_survey:"Commuting survey",supplier_pcfs:"Supplier footprint",energy_meter_readings:"Energy meter",travel_bookings:"Business travel",shipments:"Shipment",waste_transfer_notes:"Waste note",farm_registry:"Farm register",fuel_deliveries:"Fuel delivery",refrigerant_service_log:"Refrigerant log",goo_cancellations:"Green-power certificate",draft_report_summary:"Draft report"};
const F=DATA.farms, FL=F.list, HALF=F.half_n;
const dqDec=()=>store.get("dq",{});           // key -> accept | reject
const soilDec=()=>store.get("soil",{});       // farm -> peat | mineral
function soilState(fid){const s=soilDec()[fid];if(s)return s;const c=DATA.cards.find(c=>c.farm===fid&&c.type==="soil_misreport");const d=c&&dqDec()[c.key];return d==="reject"?"mineral":d==="accept"?"peat":null;}
function live(){ // inventory & FLAG after the reviewer's decisions
  const dec=dqDec();let d=0,dFlag=0;
  DATA.cards.forEach(c=>{if(c.type!=="soil_misreport"&&dec[c.key]==="reject"&&c.dt)d-=c.dt;});
  FL.forEach(f=>{if(f.org>0&&soilState(f.id)==="mineral"){d-=f.org;dFlag-=f.org;}});
  d+=store.get("entries",[]).reduce((a,e)=>a+(e.t||0),0);
  const base=DATA.kpi.s1+DATA.kpi.s2m+DATA.kpi.s3;
  const verifiedPeat=FL.filter(f=>soilState(f.id)==="peat").reduce((a,f)=>a+f.org,0);
  const removedPeat=FL.filter(f=>f.org>0&&soilState(f.id)==="mineral").reduce((a,f)=>a+f.org,0);
  return {base,total:base+d,delta:d,flag:DATA.kpi.flag+dFlag,verifiedPeat,removedPeat,peat:F.org_t-removedPeat};
}
function setSoil(fid,v){const by=needName();if(!by)return;const s=soilDec();s[fid]=v;store.set("soil",s);
  const c=DATA.cards.find(c=>c.farm===fid&&c.type==="soil_misreport");if(c){const d=dqDec();d[c.key]=v==="peat"?"accept":"reject";store.set("dq",d);}
  audit("soil_check",fid,v);render();}
function decide(key,v){const by=needName();if(!by)return;const d=dqDec();if(v)d[key]=v;else delete d[key];store.set("dq",d);
  const c=DATA.cards.find(c=>c.key===key);if(c&&c.farm){const s=soilDec();if(v)s[c.farm]=v==="accept"?"peat":"mineral";else delete s[c.farm];store.set("soil",s);}
  audit("dq_"+(v||"undo"),key,"");render();}

// ============ BRIEF ============
page("brief","Brief",()=>{
  const k=DATA.kpi, L=live(), P=DATA.pathway.rows.filter(r=>r.scenario==="ndcs"), r30=P.find(r=>r.year===2030), r35=P.find(r=>r.year===2035);
  const scope3=DATA.dq.draft_check.find(r=>r.line==="scope3")||{};
  const order=[6,0,1,2,3,4,5];
  const acts=order.map(i=>DATA.actions[i]).filter(Boolean);
  return `<section class="intro">
    <div style="display:flex;flex-direction:column;gap:16px">
      <div class="kick">Apetit · Climate &amp; Nature Navigator</div>
      <h1>Correct climate numbers, and a clear plan for <em>who does what</em>.</h1>
      <p class="lead">Apetit's climate report is built by hand from thousands of numbers. One typo can make it hundreds of times wrong, and most of the farm emissions from drained peat are not counted at all. Navigator fixes both, and a named expert approves every result.</p>
      <div class="cta"><button class="btn pri lg" onclick="go('add')">Try it: add a number</button><button class="btn lg" onclick="document.getElementById('chain').scrollIntoView({behavior:'smooth'})">See the 5-step story</button></div>
    </div>
    <div class="what">
      <div><i>1</i><p><b>Checks every number</b><span>Finds typos, wrong units, wrong currencies and double postings, and shows the corrected value.</span></p></div>
      <div><i>2</i><p><b>Finds what is missing</b><span>Counts the drained-peat emissions today's farm calculator leaves out, farm by farm.</span></p></div>
      <div><i>3</i><p><b>Tells who should act</b><span>A visit plan for field advisers, the cheapest way to the SBTi targets, and the weather and nature risks.</span></p></div>
    </div>
  </section>
  <div class="kick" id="chain" style="margin-bottom:-18px">The 5-step story · click a step</div>
  <div class="chain">
    <button class="step" onclick="go('data')"><span class="n">01 · THE NUMBERS</span><span class="big num">${fmt(scope3.ratio||314,0)}×</span><p>The draft 2025 report overstates Scope 3 ${fmt(scope3.ratio||314,0)} times: kilowatt-hours read as megawatt-hours, tonnes typed as kilos.</p><span class="go">Data check →</span></button>
    <button class="step" onclick="go('data')"><span class="n">02 · THE FIXES</span><span class="big num">${DATA.cards.length}</span><p>errors in the 2025 data, each shown as <i>was → should be</i> with the reason. An expert accepts or rejects.</p><span class="go">Review fixes →</span></button>
    <button class="step" onclick="go('farms')"><span class="n">03 · THE BLIND SPOT</span><span class="big num">${fmt(100*F.org_t/F.total_t,0)} %</span><p>of contract-farm emissions come from drained peat, which today's farm calculator leaves out.</p><span class="go">Farms &amp; peat →</span></button>
    <button class="step" onclick="go('farms')"><span class="n">04 · THE PLAN</span><span class="big num">${HALF} farms</span><p>make half of farm emissions. One winter: ${HALF} adviser visits, ~${fmt(F.route.km_road)} km, ${F.route.days} days, before the new land standard applies.</p><span class="go">Visit plan →</span></button>
    <button class="step" onclick="go('targets')"><span class="n">05 · THE TARGETS</span><span class="big num">2030 ${[r30.gap_s12,r30.gap_flag].every(g=>g<=0)?'✓':'!'}</span><p>Scope 1+2 and FLAG are on track for 2030 with measures cheaper than the carbon price. Scope 3 non-FLAG is ${fmt(Math.max(0,r30.gap_s3nf)/1000,1)} kt short, and 2035 needs the peat and rapeseed programmes scaled up.</p><span class="go">Targets →</span></button>
  </div>
  <div class="card"><div class="row" style="justify-content:space-between"><h3>Why now</h3><span class="small muted">Dates from the package's framework digest (status 3 Nov 2026)</span></div>
    <div class="tl" style="margin-top:12px">
      <div class="now"><b>7 Nov 2026</b><span>Today</span></div>
      <div class="hot"><b>1 Jan 2027</b><span>GHG Protocol Land Sector standard in force: drained peat must be counted</span></div>
      <div><b>1 Feb 2027</b><span>SBTi Net-Zero Standard V2 takes effect</span></div>
      <div><b>Dec 2027</b><span>SBTi near-term targets due (24 months from the Dec 2025 commitment)</span></div>
    </div></div>
  <details class="acc"><summary><span class="ic">t</span><span class="tt"><b>Key figures 2025</b><span>Scope 1 ${fmt(k.s1)} t · Scope 2 ${fmt(k.s2m)} t · Scope 3 ${fmt(k.s3)} t · land-based share ${fmt(100*k.flag_share,0)} %</span></span><span></span></summary><div class="body">
  <div class="grid g4">
    <div class="card kpi"><div class="l">Scope 1, 2025</div><div class="v num">${fmt(k.s1)} t</div><div class="small muted">fuels and refrigerants ${src(k.src_s1)}</div></div>
    <div class="card kpi"><div class="l">Scope 2, market-based</div><div class="v num">${fmt(k.s2m)} t</div><div class="small muted">location-based ${fmt(k.s2l)} t ${src(k.src_s2)}</div></div>
    <div class="card kpi"><div class="l">Scope 3</div><div class="v num">${fmt(k.s3)} t</div><div class="small muted">${fmt(100*k.cat1/k.s3,0)} % is purchased goods ${src(k.src_s3)}</div></div>
    <div class="card kpi"><div class="l">Land-based (FLAG) share</div><div class="v num">${fmt(100*k.flag_share,0)} %</div><div class="small muted">above 20 %, so a FLAG target is mandatory ${src(k.src_flag)}</div></div>
  </div>
  </div></details>
  ${L.delta?`<div class="reviewbar"><b>Your review changed the inventory by ${L.delta>0?'+':''}${fmt(L.delta)} t</b> (now ${fmt(L.total)} t, FLAG ${fmt(L.flag)} t).<span class="sp"></span><button class="btn sm" onclick="go('data')">See decisions</button></div>`:''}
  <section style="display:flex;flex-direction:column;gap:14px"><div class="row"><h2>What Apetit should do next</h2><span class="sp"></span>
      <button class="btn ${allApproved()?'pri':''}" ${allApproved()&&SAMPLE?'':'disabled'} onclick="aiMemo()" data-tip="${allApproved()?(SAMPLE?'Drafts a one-page board memo from the approved numbers':'Needs Claude in this view'):'Locked until all 4 sections are approved'}">Draft board memo</button></div>
    <p class="small muted">Click an action to see why, who owns it and the source.</p>
    <div class="stack-acc">${acts.map((a,i)=>`<details class="acc"><summary><span class="ic">${i+1}</span><span class="tt"><b>${esc(a.title)}</b><span>Owner: ${esc(a.owner)}</span></span><span class="pill">${esc(a.size)}</span></summary><div class="body"><p>${esc(a.why)}</p><p class="small muted">Evidence: <span class="tag">${esc(a.evidence)}</span></p></div></details>`).join("")}</div>
  </section>`;
});

// ============ DATA CHECK ============
let dcFam="", dcAll=false, upl=null;
function famOf(t){return FAM[t]||["!",t.replace(/_/g," ")];}
function pretty(v){const n=Number(String(v).replace(/[,€]/g,""));return (String(v).trim()!==""&&!isNaN(n)&&!/^\d{4}$/.test(String(v)))?fmt(n,Math.abs(n)<10?3:0):String(v);}
function card(c){const f=famOf(c.type),d=dqDec()[c.key];
  const impact=[c.eur?`<span class="pill">${eur(Math.abs(c.eur))} ${c.eur<0?'overstated':'understated'}</span>`:'',c.dt?`<span class="pill">${fmt(Math.abs(c.dt))} t CO2e</span>`:''].join("");
  return `<article class="dc ${d==='accept'?'acc':d==='reject'?'rej':''}"><div class="mult">${esc(f[0])}</div>
   <div><div class="row"><b>${esc(c.label||TABLE[c.table]||c.table)}</b><span class="mono muted">${esc(c.key)}</span></div>
     <div class="wasis"><span class="was num">${esc(c.field==="*"?"counted twice":pretty(c.was))}</span><span class="muted">→</span><span class="is num">${esc(c.field==="*"?"counted once":pretty(c.is))}</span><span class="small muted">${esc(c.field!=="*"?c.field.replace(/_/g," "):"")}</span></div>
     <p>${esc(c.why)}</p><div class="row" style="margin-top:6px">${impact}<span class="pill ${c.conf>=0.9?'ok':'wa'}">${c.conf>=0.9?'High confidence':'Expert check needed'}</span><span class="pill">${esc(f[1])}</span></div></div>
   <div class="acts">${d?`<span class="pill ${d==='accept'?'ok':'no'}">${d==='accept'?'Fix accepted':'Fix rejected'}</span><button class="btn sm" onclick="decide('${esc(c.key)}','')">Undo</button>`
     :`<button class="btn ok" onclick="decide('${esc(c.key)}','accept')">Accept fix</button><button class="btn no" onclick="decide('${esc(c.key)}','reject')">Reject</button>`}</div></article>`;}
page("data","Data check",()=>{
  const L=live(),dec=dqDec(),cards=DATA.cards.slice().sort((a,b)=>(Math.abs(b.eur||0)+Math.abs(b.dt||0)*200)-(Math.abs(a.eur||0)+Math.abs(a.dt||0)*200));
  const types=[...new Set(cards.map(c=>c.type))].sort((a,b)=>cards.filter(c=>c.type===b).length-cards.filter(c=>c.type===a).length);
  const shown=cards.filter(c=>!dcFam||c.type===dcFam), nA=Object.values(dec).filter(v=>v==="accept").length, nR=Object.values(dec).filter(v=>v==="reject").length;
  const dr=DATA.dq.draft_check;
  return `${reviewBar("data","2025 corrections and the cleaned inventory.")}
  <div class="hero314 card"><div style="display:flex;flex-direction:column;gap:10px"><div class="kick">Before anything else</div><h1>The draft 2025 report is <em>${fmt(dr.find(r=>r.line==="scope3")?.ratio,0)}×</em> too high.</h1>
      <p class="lead">It was typed from the raw pipeline: kilowatt-hours read as megawatt-hours, tonnes keyed as kilos, refrigerant grams as kilos. Its own total does not add up. Navigator blocks it and rebuilds the inventory from cleaned data.</p></div>
    <div style="display:flex;flex-direction:column;gap:8px">${dr.map(r=>`<div class="row" style="justify-content:space-between;border-bottom:1px solid var(--line);padding:6px 0"><b>${esc({scope1:"Scope 1",scope2_market:"Scope 2",scope3:"Scope 3",total_market_based:"Total"}[r.line]||r.line)}</b><span class="wasis" style="margin:0"><span class="was num">${fmt(r.draft)}</span><span class="muted">→</span><span class="is num">${fmt(r.clean)} t</span></span><span class="pill ${r.ratio>1.05||r.ratio<0.95?'no':'ok'}">${r.ratio>1.05||r.ratio<0.95?fmt(r.ratio,r.ratio<10?1:0)+'×':'ok'}</span></div>`).join("")}
      <span class="small muted">${src("data/05_scenarios/draft_report_summary_2025.csv vs cleaned A2 inventory")}</span></div></div>
  <div class="grid g4">
    <div class="card kpi"><div class="l">Errors found in 2025</div><div class="v num">${DATA.cards.length}</div><div class="small muted">${DATA.cards.filter(c=>c.review).length} need an expert</div></div>
    <div class="card kpi"><div class="l">Tested on Apetit's labelled 2023–24 errors</div><div class="v num">${fmt(DATA.dq.dev_score,0)}/100</div><div class="small muted">package baseline ${fmt(DATA.dq.baseline_score,0)} ${src("ccn_tools.score_a1 on tasks/dev labels")}</div></div>
    <div class="card kpi"><div class="l">Your decisions</div><div class="v num">${nA} ✓ · ${nR} ✗</div><div class="small muted">logged with name and time</div></div>
    <div class="card kpi"><div class="l">2025 inventory after review</div><div class="v num">${fmt(L.total)} t</div><div class="small muted">${L.delta?`${L.delta>0?'+':''}${fmt(L.delta)} t from your review and new entries`:'all fixes applied'}</div></div>
  </div>
  <section style="display:flex;flex-direction:column;gap:12px"><h2>The ${cards.length} errors, grouped</h2><p class="small muted">Click a group to open it. Each error shows the wrong value, the corrected value and why. Accept or reject each fix.</p>
  <div class="stack-acc">${types.map(t=>{const cs=cards.filter(c=>c.type===t),done=cs.filter(c=>dec[c.key]).length,e=cs.reduce((a,c)=>a+Math.abs(c.eur||0),0),tt=cs.reduce((a,c)=>a+Math.abs(c.dt||0),0);
    return `<details class="acc" ${dcFam===t?'open':''} ontoggle="if(this.open)dcFam='${t}'"><summary><span class="ic">${esc(famOf(t)[0])}</span><span class="tt"><b>${esc(famOf(t)[1])}</b><span>${cs.length} found${e?` · ${eur(e)} wrong`:''}${tt?` · ${fmt(tt)} t CO2e`:''} · ${done} reviewed</span></span><span class="pill ${done===cs.length?'ok':'wa'}">${done===cs.length?'done':'to review'}</span></summary><div class="body">${cs.map(card).join("")}</div></details>`;}).join("")}</div></section>
  <p class="small">Have new data? <a style="color:var(--water);cursor:pointer;font-weight:600" onclick="go('add')">Add a purchase, a farm answer or a whole file →</a></p>
  <details class="more"><summary>Cleaned 2025 inventory by category</summary>
    ${barH(DATA.inventory.categories,{width:900,label:r=>r.category.replace(/_/g," ").replace(/^cat(\d+) /,"Cat $1 · "),value:r=>r.tco2e,color:r=>r.scope==="scope1"?"var(--water)":r.scope.startsWith("scope2")?"var(--muted)":"var(--field)"})}
    ${table(DATA.inventory.lines.slice().sort((a,b)=>b.tco2e-a.tco2e),[{h:"Category",f:r=>esc(r.category.replace(/_/g," "))},{h:"Line",f:r=>`<span class="tag">${esc(r.line_item)}</span>`},{h:"t CO2e",n:1,f:r=>fmtT(r.tco2e)},{h:"Method",k:"basis"}],{max:300})}
    <p class="small muted" style="margin-top:8px">Checked against the public 2023 and 2024 inventories: ${fmt(DATA.inventory.dev_2023,1)} and ${fmt(DATA.inventory.dev_2024,1)} out of 100 (package baseline ~25).</p></details>`;
});

// ============ ADD DATA (input → instant check → result) ============
const REF=DATA.ref;
let addMode="purchase", lastResult=null, fileResult=null;
const entries=()=>store.get("entries",[]);
const fq=v=>Number(v).toLocaleString("en-US",{maximumFractionDigits:3});
const nearR=(x,t,tol)=>x>0&&Math.abs(Math.log10(x)-Math.log10(t))<tol;
const matName=id=>(REF.materials.find(m=>m.id===id)||{}).n||id;
function checkPurchase(v){
  const m=REF.materials.find(x=>x.id===v.mat); if(!m) return {status:"warn",title:"Choose a product",why:"Pick what was bought so Navigator knows what is normal for it."};
  const kg=v.qty*(v.unit==="t"?1000:1), rate=v.cur==="SEK"?REF.sek:v.cur==="USD"?REF.usd:1, eurAmt=v.amt/rate, med=REF.ppk[v.mat], r=(eurAmt/kg)/med;
  const qm=REF.qmed[v.sup+"|"+v.mat], supCur=REF.supcur[v.sup], regMat=(REF.suppliers.find(s=>s.id===v.sup)||{}).mat;
  const tOf=k=>k*m.ef/1000, base={kg, t:tOf(kg), ef:m.ef, product:m.n};
  const price=`At this amount the price would be €${fmt(eurAmt/kg,eurAmt/kg<10?2:0)} per kg. Normal for this product (${m.n}) is about €${fmt(med,2)} per kg.`;
  if(v.unit==="kg"&&r>250) return {...base,status:"warn",title:"This looks like tonnes typed as kilos",was:`${fq(v.qty)} kg`,is:`${fq(v.qty*1000)} kg`,why:price+` That is ${fmt(r,0)} times too expensive, so the quantity is most likely in tonnes.`,fix:{qty:v.qty*1000,unit:"kg"},fixKg:kg*1000};
  if(v.unit==="t"&&r<1/250) return {...base,status:"warn",title:"This looks like kilos typed as tonnes",was:`${fq(v.qty)} t`,is:`${fq(v.qty)} kg`,why:price+" The price is about a thousand times too low.",fix:{qty:v.qty,unit:"kg"},fixKg:v.qty};
  if(nearR(r,0.1,.25)) return {...base,status:"warn",title:"The decimal point looks one place off",was:`${fmt(kg)} kg`,is:`${fmt(kg/10)} kg`,why:price+` The quantity is ten times larger than the price suggests${qm?` and this supplier usually delivers about ${fmt(qm)} kg`:''}.`,fix:{qty:v.qty/10,unit:v.unit},fixKg:kg/10};
  if(v.cur==="EUR"&&(supCur==="SEK"||nearR(r,REF.sek,.12))) return {...base,status:"warn",title:"This looks like Swedish kronor booked as euros",was:`€${fmt(v.amt)}`,is:`€${fmt(v.amt/REF.sek)} (${fmt(v.amt)} SEK)`,why:(supCur==="SEK"?`This supplier invoices in kronor on its other lines. `:``)+price+` That is about ${fmt(r,1)} times normal, which matches the krona rate.`,fix:{cur:"SEK"},fixKg:kg};
  if(v.cur==="EUR"&&supCur==="USD") return {...base,status:"warn",title:"This supplier invoices in US dollars",was:"EUR",is:"USD",why:"Every other line from this supplier is in dollars. Check the invoice currency.",fix:{cur:"USD"},fixKg:kg};
  if(nearR(r,10,.25)&&qm&&nearR(kg/qm,0.1,.45)) return {...base,status:"warn",title:"The decimal point looks one place off",was:`${fmt(kg)} kg`,is:`${fmt(kg*10)} kg`,why:price+` The quantity is ten times smaller than this supplier usually delivers (${fmt(qm)} kg).`,fix:{qty:v.qty*10,unit:v.unit},fixKg:kg*10};
  if(regMat&&regMat!==v.mat) return {...base,status:"warn",title:"Is this the right product?",was:m.n,is:matName(regMat),why:`This supplier is registered for ${matName(regMat)}. A wrong product code means a wrong emission factor.`,fixKg:kg};
  if(r>3||r<1/3) return {...base,status:"warn",title:"The price is unusual. Please check the invoice",why:price,fixKg:kg};
  return {...base,status:"ok",title:"Looks right",why:price.replace("would be","is")+` The quantity fits this supplier.`};
}
function checkFarm(v){
  const f=REF.farms[v.farm]; if(!f) return {status:"warn",title:"Choose a farm"};
  const med=REF.yield_med[v.crop], issues=[];let fix={};
  if(v.yield>3*med){issues.push({t:"The yield looks ten times too high",was:`${fmt(v.yield,2)} t/ha`,is:`${fmt(v.yield/10,2)} t/ha`,why:`Normal ${CROP[v.crop].toLowerCase()} yield is about ${fmt(med,2)} t/ha. A decimal point has probably moved.`});fix.yield=v.yield/10;}
  else if(v.yield<0.25*med) issues.push({t:"The yield is very low",was:`${fmt(v.yield,2)} t/ha`,is:"check",why:`Normal is about ${fmt(med,2)} t/ha. Was the crop lost, or is the unit wrong?`});
  const ca=(f.crops||{})[v.crop];
  if(ca&&Math.abs(v.area-ca)/ca>0.2) issues.push({t:"The area does not match the parcel register",was:`${fmt(v.area,1)} ha`,is:`${fmt(ca,1)} ha`,why:`The register lists ${fmt(ca,1)} ha of ${CROP[v.crop].toLowerCase()} for this farm in 2025.`});
  const share=f.area?f.peat/f.area:0;
  if(v.soil==="mineral"&&share>=0.3) issues.push({t:"The soil map shows peat on this farm",was:"Mineral soil",is:`Peat on ${fmt(f.peat,1)} ha (${fmt(100*share,0)} %)`,why:`Drained peat adds about ${fmt(f.org)} t CO2e a year on this farm. The field adviser should check the soil on the next visit.`});
  return issues.length?{status:"warn",title:issues.length===1?issues[0].t:`${issues.length} things to check`,issues,peat:share>=0.3?f.org:0}:{status:"ok",title:"Looks right",why:`Yield, area and soil fit the parcel register and the soil map.`};
}
function addEntry(kind,v,res,useFix){const e=entries();
  const kg=kind==="purchase"?(useFix&&res.fixKg?res.fixKg:res.kg):0, t=kind==="purchase"?kg*(res.ef||0)/1000:0;
  e.unshift({ts:new Date().toISOString(),kind,v,title:res.title,status:res.status,corrected:!!useFix&&res.status==="warn",t,label:kind==="purchase"?`${matName(v.mat)} · ${v.sup}`:`Farm ${v.farm} · ${CROP[v.crop]}`});
  store.set("entries",e);audit("add_"+kind,kind==="purchase"?v.mat:v.farm,res.title+(useFix?" (corrected)":""));lastResult=null;render();toast("Saved to your entries");}
function resultHTML(res){if(!res)return"";
  const rows=res.issues?res.issues:[{t:res.title,was:res.was,is:res.is,why:res.why}];
  return `<div class="result ${res.status==='ok'?'ok':'warn'}"><div class="row"><span style="font-size:26px">${res.status==='ok'?'✓':'!'}</span><h3>${esc(res.title)}</h3></div>
   ${rows.map(x=>`${res.issues?`<b>${esc(x.t)}</b>`:''}${x.was?`<div class="wasis"><span class="was num">${esc(x.was)}</span><span class="muted">→</span><span class="is num">${esc(x.is)}</span></div>`:''}<p>${esc(x.why||'')}</p>`).join("")}
   ${res.kg!=null?`<p class="small">This purchase adds <b>${fmt((res.status==='warn'&&res.fixKg?res.fixKg:res.kg)*res.ef/1000,1)} t CO2e</b> to the 2025 inventory (${esc(res.product)}, ${fmt(res.ef,2)} kg CO2e per kg).</p>`:''}
   <div class="row">${res.status==='warn'&&(res.fix||res.issues)?`<button class="btn pri" onclick="addEntry(addMode,lastResult.v,lastResult,true)">Use the corrected value</button><button class="btn" onclick="addEntry(addMode,lastResult.v,lastResult,false)">Keep as typed</button>`:`<button class="btn pri" onclick="addEntry(addMode,lastResult.v,lastResult,false)">Save</button>`}</div></div>`;}
const val=id=>document.getElementById(id)?.value;
function runCheck(){
  if(addMode==="purchase"){const v={mat:val("f_mat"),sup:val("f_sup"),qty:+val("f_qty"),unit:val("f_unit"),amt:+val("f_amt"),cur:val("f_cur"),date:val("f_date")};
    if(!(v.qty>0&&v.amt>0)){toast("Fill in quantity and amount.");return;} lastResult={...checkPurchase(v),v};}
  else {const v={farm:val("g_farm"),crop:val("g_crop"),area:+val("g_area"),yield:+val("g_yield"),soil:val("g_soil")};if(!(v.area>0&&v.yield>0)){toast("Fill in area and yield.");return;} lastResult={...checkFarm(v),v};}
  audit("check_"+addMode,"",lastResult.title);document.getElementById("resbox").innerHTML=resultHTML(lastResult);document.getElementById("resbox").scrollIntoView({behavior:"smooth",block:"nearest"});}
function example(kind){const m=REF.materials.find(x=>x.id==="M101")||REF.materials[0],s=REF.suppliers.find(x=>x.mat===m.id)||REF.suppliers[0],q=40000,a=Math.round(q*REF.ppk[m.id]);
  const set=(id,v)=>{const el=document.getElementById(id);if(el)el.value=v;};
  set("f_mat",m.id);supOptions();set("f_sup",s.id);set("f_cur","EUR");set("f_unit","kg");set("f_amt",a);
  set("f_qty",kind==="tonnes"?q/1000:q);if(kind==="sek")set("f_amt",Math.round(a*REF.sek));
  if(kind==="decimal")set("f_qty",q*10);lastResult=null;document.getElementById("resbox").innerHTML="";}
function exampleFarm(){const top=FL.find(f=>f.reported==="mineral"&&f.org>0)||FL[0];const f=REF.farms[top.id];
  const set=(id,v)=>{const el=document.getElementById(id);if(el)el.value=v;};set("g_farm",top.id);set("g_crop",top.main||"pea");set("g_area",(f.crops||{})[top.main]||f.area);set("g_yield",((REF.yield_med[top.main||"pea"]||3)*10).toFixed(1));set("g_soil","mineral");}
function supOptions(){const m=val("f_mat"),el=document.getElementById("f_sup");if(!el)return;const list=REF.suppliers.filter(s=>s.mat===m);const rest=REF.suppliers.filter(s=>s.mat!==m);
  el.innerHTML=`<optgroup label="Usual suppliers for this product">${list.map(s=>`<option value="${s.id}">${s.id} · ${s.country}</option>`).join("")}</optgroup><optgroup label="Other suppliers">${rest.map(s=>`<option value="${s.id}">${s.id} · ${s.country} · ${esc(matName(s.mat))}</option>`).join("")}</optgroup>`;}
function farmFileCheck(rows){const ys=rows.map(r=>+r.year||0),y=ys.includes(2025)?2025:Math.max(...ys);return rows.filter(r=>REF.farms[r.farm_id]&&CROP[r.crop]&&(!y||+r.year===y)).map(r=>({r,res:checkFarm({farm:r.farm_id,crop:r.crop,area:+r.area_ha,yield:+r.yield_t_ha,soil:/organic/i.test(r.soil_type_reported||"")?"organic":"mineral"})})).filter(x=>x.res.status==="warn"&&x.res.issues);}
page("add","Add data",()=>{const E=entries(),tAdd=E.reduce((a,e)=>a+(e.t||0),0);
  const today=new Date().toISOString().slice(0,10);
  return `<section style="display:flex;flex-direction:column;gap:12px"><div class="kick">Add new information</div>
    <h1>Type it in. Navigator <em>checks it in a second</em>.</h1>
    <p class="lead">Enter one purchase or one farm's survey answer, or drop a whole file. Navigator compares it with what is normal: the supplier's usual prices and amounts, normal yields, the parcel register and the soil map. If something looks wrong, it shows the corrected value and why.</p></section>
  <div class="choices">
    <button class="choice" aria-pressed="${addMode==='purchase'}" onclick="addMode='purchase';lastResult=null;render()"><b>A purchase</b><span>One line from an invoice: product, supplier, amount and price.</span></button>
    <button class="choice" aria-pressed="${addMode==='farm'}" onclick="addMode='farm';lastResult=null;render()"><b>A farm's survey answer</b><span>Crop, area, yield and the soil type the farmer reported.</span></button>
    <button class="choice" aria-pressed="${addMode==='file'}" onclick="addMode='file';lastResult=null;render()"><b>A whole file</b><span>A purchase-line or farm-survey CSV export. Checked in this browser.</span></button>
  </div>
  ${addMode==="purchase"?`<div class="card" style="display:flex;flex-direction:column;gap:18px"><div class="row"><h2>New purchase</h2><span class="sp"></span><label class="small muted" for="ex">Fill an example</label><select id="ex" onchange="if(this.value)example(this.value);this.value=''"><option value="">Choose…</option><option value="ok">Correct line</option><option value="tonnes">Tonnes typed as kilos</option><option value="decimal">Decimal point slipped</option><option value="sek">Kronor booked as euros</option></select></div>
    <div class="form">
      <label class="wide">Product<select id="f_mat" onchange="supOptions()">${REF.materials.map(m=>`<option value="${m.id}" ${m.id==="M101"?'selected':''}>${esc(m.n)}</option>`).join("")}</select></label>
      <label>Supplier<select id="f_sup"></select></label>
      <label>Quantity<input id="f_qty" type="number" min="0" step="any" inputmode="decimal" placeholder="e.g. 40000"></label>
      <label>Unit<select id="f_unit"><option value="kg">kilograms (kg)</option><option value="t">tonnes (t)</option></select></label>
      <label>Date<input id="f_date" type="date" value="${today}"></label>
      <label>Invoice amount<input id="f_amt" type="number" min="0" step="any" inputmode="decimal" placeholder="e.g. 19000"></label>
      <label>Currency<select id="f_cur"><option>EUR</option><option>SEK</option><option>USD</option></select></label>
    </div><div><button class="btn pri lg" onclick="runCheck()">Check this purchase</button></div><div id="resbox">${resultHTML(lastResult)}</div></div>`:''}
  ${addMode==="farm"?`<div class="card" style="display:flex;flex-direction:column;gap:18px"><div class="row"><h2>Farm survey answer</h2><span class="sp"></span><button class="btn sm" onclick="exampleFarm()">Fill an example</button></div>
    <div class="form">
      <label>Farm<select id="g_farm">${FL.map(f=>`<option value="${f.id}">${f.id}${f.rank<=HALF?' · top '+HALF:''}</option>`).join("")}</select></label>
      <label>Crop<select id="g_crop">${Object.entries(CROP).map(([k,v])=>`<option value="${k}">${v}</option>`).join("")}</select></label>
      <label>Soil type reported<select id="g_soil"><option value="mineral">Mineral soil</option><option value="organic">Organic soil (peat)</option></select></label>
      <label>Contract area (ha)<input id="g_area" type="number" min="0" step="any" placeholder="e.g. 20"></label>
      <label>Yield (t/ha)<input id="g_yield" type="number" min="0" step="any" placeholder="e.g. 1.5"></label>
    </div><div><button class="btn pri lg" onclick="runCheck()">Check this answer</button></div><div id="resbox">${resultHTML(lastResult)}</div></div>`:''}
  ${addMode==="file"?`<div class="drop" id="drop" style="padding:28px"><div style="display:flex;flex-direction:column;gap:8px;align-items:flex-start"><h2>Drop a CSV file here</h2><p>or <label for="upf">choose a file</label><input type="file" id="upf" accept=".csv,text/csv">. Nothing leaves this browser.</p>
    <p class="small muted">Purchase lines: doc_no, line_no, posting_date, material_id, supplier_id, quantity, uom, net_amount, currency, movement_type. Farm survey: farm_id, crop, area_ha, yield_t_ha, soil_type_reported. Try it with <span class="tag">02_raw_feeds/erp_purchase_lines_2021_2025.csv</span> or <span class="tag">03_farming/farm_survey_fi.csv</span> from the package.</p></div><div id="uplout">${fileResult||''}</div></div>`:''}
  <details class="acc" ${E.length?'open':''}><summary><span class="ic">${E.length}</span><span class="tt"><b>Your entries</b><span>${E.length?`${E.filter(e=>e.status==='warn').length} needed a correction · they add ${fmt(tAdd,1)} t CO2e to the 2025 inventory`:'Nothing saved yet'}</span></span><span>${E.length?`<button class="btn sm" onclick="event.preventDefault();store.set('entries',[]);render()">Clear</button>`:''}</span></summary><div class="body">
    ${E.map(e=>`<div class="row" style="border-bottom:1px solid var(--line);padding:8px 0"><span class="pill ${e.status==='ok'?'ok':e.corrected?'ok':'wa'}">${e.status==='ok'?'OK':e.corrected?'Corrected':'Kept as typed'}</span><b>${esc(e.label)}</b><span class="small muted">${esc(e.title)}</span><span class="sp"></span>${e.t?`<span class="num">${fmt(e.t,1)} t</span>`:''}<span class="small muted">${esc(e.ts.slice(0,16).replace("T"," "))}</span></div>`).join("")||'<p class="small muted">Checked entries appear here, with the decision you made.</p>'}</div></details>`;
},{after(){supOptions();const dz=$("#drop"),fi=$("#upf");if(!dz)return;
  const load=f=>f.text().then(t=>{try{const rows=GUARD.parseCSV(t);if(!rows.length)throw 0;let html="";
    if("net_amount" in rows[0]){const R=GUARD.run(rows,DATA.erp_master.mat,DATA.erp_master.sup);const by={};R.issues.forEach(o=>by[o.type]=(by[o.type]||0)+1);
      html=`<div class="result warn" style="margin-top:16px"><h3>${esc(f.name)}: ${R.issues.length} suspected errors in ${fmt(R.n)} lines</h3><p>Checked in ${fmt(R.ms,0)} ms. ${Object.entries(by).map(([t,n])=>`${famOf(t)[1]}: ${n}`).join(" · ")}</p>
        <details class="acc"><summary><span class="ic">${R.issues.length}</span><span class="tt"><b>Show the lines</b><span>wrong value → corrected value</span></span><span></span></summary><div class="body">${R.issues.slice(0,60).map(o=>`<div class="row small" style="border-bottom:1px solid var(--line);padding:6px 0"><span class="pill">${esc(famOf(o.type)[1])}</span><span class="mono">${esc(o.r.key)}</span><span>${esc(o.r.posting_date)}</span><span>${esc(matName(o.r.material_id))}</span><span class="was num" style="font-size:15px">${esc(String(o.fix.from))}</span>→<span class="is num" style="font-size:15px">${esc(String(o.fix.to))}</span></div>`).join("")}</div></details></div>`;}
    else if("soil_type_reported" in rows[0]){const W=farmFileCheck(rows);
      html=`<div class="result warn" style="margin-top:16px"><h3>${esc(f.name)}: ${W.length} answers to check (2025, the parcel-register year)</h3>
        <details class="acc"><summary><span class="ic">${W.length}</span><span class="tt"><b>Show the answers</b><span>farm, crop and what looks wrong</span></span><span></span></summary><div class="body">${W.slice(0,80).map(x=>`<div class="row small" style="border-bottom:1px solid var(--line);padding:6px 0"><b>${esc(x.r.farm_id)}</b><span>${esc(x.r.year||'')}</span><span>${esc(CROP[x.r.crop]||x.r.crop)}</span><span>${esc(x.res.issues.map(i=>i.t).join(" · "))}</span></div>`).join("")}</div></details></div>`;}
    else throw 0; fileResult=html;$("#uplout").innerHTML=html;audit("file_check",f.name,"");}catch(e){$("#uplout").innerHTML=`<p style="margin-top:12px;color:var(--bad)">This file does not have the columns listed above.</p>`;}});
  fi.addEventListener("change",()=>fi.files[0]&&load(fi.files[0]));
  dz.addEventListener("dragover",e=>{e.preventDefault();dz.classList.add("over");});dz.addEventListener("dragleave",()=>dz.classList.remove("over"));
  dz.addEventListener("drop",e=>{e.preventDefault();dz.classList.remove("over");e.dataTransfer.files[0]&&load(e.dataTransfer.files[0]);});}});

// ============ FARMS & PEAT ============
let fSel=FL[2].id, showRoute=true, planLang=store.get("planLang","fi");
function farmMap(){
  const feats=DATA.fi_geo.features, pts=feats.flatMap(f=>f.geometry.coordinates[0]).concat(DATA.mapfarms.map(f=>[f.lon,f.lat]));
  const lx=Math.min(...pts.map(p=>p[0])),hx=Math.max(...pts.map(p=>p[0])),ly=Math.min(...pts.map(p=>p[1])),hy=Math.max(...pts.map(p=>p[1]));
  const W=640,H=520,pad=16,k=Math.cos((ly+hy)/2*Math.PI/180),sc=Math.min((W-2*pad)/((hx-lx)*k),(H-2*pad)/(hy-ly)),ox=(W-(hx-lx)*k*sc)/2,oy=(H-(hy-ly)*sc)/2;
  const P=(lon,lat)=>[ox+(lon-lx)*k*sc,oy+(hy-lat)*sc];
  let s=`<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Contract farms in south-west Finland"><defs><pattern id="marsh" width="8" height="6" patternUnits="userSpaceOnUse"><rect width="8" height="6" fill="#7a4322"/><path d="M1 3h5" stroke="#f1e3d6" stroke-width="1.2"/></pattern></defs>`;
  feats.forEach(f=>s+=`<path d="M${f.geometry.coordinates[0].map(p=>P(p[0],p[1]).map(v=>v.toFixed(1)).join(",")).join("L")}Z" fill="#f6f7f1" stroke="var(--line)" stroke-width=".8"/>`);
  const byId=Object.fromEntries(DATA.mapfarms.map(f=>[f.id,f]));
  if(showRoute){const rp=F.route.order.map(id=>id==="SAKYLA"?P(F.depot.lon,F.depot.lat):P(byId[id].lon,byId[id].lat));s+=`<polyline points="${rp.map(p=>p.map(v=>v.toFixed(1)).join(",")).join(" ")}" fill="none" stroke="var(--ink)" stroke-width="2" stroke-dasharray="6 5"/>`;}
  const max=FL[0].t;
  DATA.mapfarms.slice().reverse().forEach(f=>{const [x,y]=P(f.lon,f.lat),top=f.rank<=HALF,r=2.2+Math.sqrt(f.t/max)*22,st=soilState(f.id);
    s+=`<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="${r.toFixed(1)}" fill="${f.org>0&&st!=='mineral'?'url(#marsh)':top?'#4c7a55':'#9db3a2'}" opacity="${top?1:.55}" stroke="${f.id===fSel?'#2f6e9f':top?'#f0bd16':'none'}" stroke-width="${f.id===fSel?4:top?3:0}" style="cursor:pointer" onclick="fSel='${f.id}';render()" data-tip="${esc(`<b>Farm ${f.id}</b> · rank ${f.rank}<br>${fmt(f.t)} t CO2e, of which peat ${fmt(f.org)} t`)}"/>`;});
  const [dx,dy]=P(F.depot.lon,F.depot.lat);s+=`<rect x="${dx-7}" y="${dy-7}" width="14" height="14" fill="var(--ink)"/><text x="${dx+11}" y="${dy+4}" class="lbl">Säkylä plant</text>`;
  const k10=10/111*sc;s+=`<g transform="translate(${W-pad-k10},${H-10})"><rect width="${k10}" height="4" fill="var(--ink)"/><text x="${k10/2}" y="-6" text-anchor="middle">10 km</text></g>`;
  return s+`</svg>`;}
function miniMap(f){const ps=f.parcels||[];if(!ps.length)return"";const la=ps.map(p=>p.lat),lo=ps.map(p=>p.lon),k=Math.cos(la[0]*Math.PI/180);
  const lx=Math.min(...lo),hx=Math.max(...lo),ly=Math.min(...la),hy=Math.max(...la),W=230,H=180,pad=18,sc=Math.min((W-2*pad)/Math.max(1e-4,(hx-lx)*k),(H-2*pad)/Math.max(1e-4,hy-ly));
  const X=p=>pad+(p.lon-lx)*k*sc+((W-2*pad)-(hx-lx)*k*sc)/2,Y=p=>pad+(hy-p.lat)*sc+((H-2*pad)-(hy-ly)*sc)/2;
  return `<svg class="chart" viewBox="0 0 ${W} ${H}" style="max-width:${W}px"><rect width="${W}" height="${H}" rx="8" fill="var(--paper)"/>${ps.map(p=>`<circle cx="${X(p).toFixed(1)}" cy="${Y(p).toFixed(1)}" r="${(3+Math.sqrt(p.ha)*1.8).toFixed(1)}" fill="${p.soil==='organic'?'url(#marsh)':'#4c7a55'}" opacity="${p.soil==='organic'?1:.6}" stroke="${p.water<100&&!p.buffer?'#2f6e9f':'none'}" stroke-width="2.5" data-tip="${esc(p.id+' · '+p.ha+' ha · '+p.soil+' · '+p.water+' m to water')}"/>`).join("")}<text x="${W-8}" y="${H-7}" text-anchor="end">${fmt((hx-lx)*k*111,1)} km</text></svg>`;}
function plan(f){const fi=planLang==="fi",T=(a,b)=>fi?b:a,st=soilState(f.id),orgNow=st==="mineral"?0:f.org,tot=f.t-(st==="mineral"?f.org:0),w=f.wx||{};
  const cn=c=>fi?CROP_FI[c]||c:(CROP[c]||c).toLowerCase(), dec=n=>fi?String(n).replace(".",","):String(n);
  const grass=Math.round((f.peat_ha_map||0)*F.grass_cut_t_ha);
  const wet=w.p25<w.pn*0.8?T("drier than usual","tavallista kuivempi"):w.p25>w.pn*1.2?T("wetter than usual","tavallista sateisempi"):T("close to normal","lähellä tavallista");
  return `<article class="plan" aria-live="polite"><div class="planhead"><div><div class="small muted">${T("Farm visit plan 2026–27","Tilakäyntisuunnitelma 2026–27")} · ${T("rank","sija")} ${f.rank}/${F.n}</div><h2>${T("Farm","Tila")} ${f.id}</h2>
      <div class="small muted">${Object.entries(f.crops||{}).map(([c,a])=>`${cn(c)} ${dec(a)} ha`).join(" · ")} · ${T("contract farm since","sopimustilana vuodesta")} ${f.joined||"–"}</div></div>
      <div class="row" style="align-items:flex-start"><div class="seg" role="group" aria-label="Language"><button aria-pressed="${!fi}" onclick="planLang='en';store.set('planLang','en');render()">EN</button><button aria-pressed="${fi}" onclick="planLang='fi';store.set('planLang','fi');render()">FI</button></div></div></div>
    <section class="sec"><h4>${T("Climate figure","Ilmastoluku")}</h4><div><div class="big num">${fmt(tot)} <small>t CO2e / ${T("year","vuosi")} (2025)</small></div>
      <div class="stack"><i style="width:${100*(f.t-f.org)/Math.max(1,f.t)}%;background:var(--field)"></i><i class="peatfill" style="width:${100*orgNow/Math.max(1,f.t)}%"></i></div>
      <div class="legend"><span><i style="background:var(--field)"></i>${T("Current calculator","Nykyinen laskuri")} ${fmt(f.t-f.org)} t</span><span><i class="peatfill"></i>${T("Drained peat, missing today","Turvelohkot, puuttuu nyt")} ${fmt(orgNow)} t</span></div>
      ${st?'':`<p class="small muted" style="margin-top:6px">${T(`Peat share is an estimate from the soil map, scaled ×${F.org_scale} until checked on site.`,`Turpeen osuus on arvio maaperäkartasta (×${dec(F.org_scale)}), kunnes se tarkistetaan tilalla.`)}</p>`}</div></section>
    ${f.org>0?`<section class="sec"><h4>${T("Check on the visit","Tarkistetaan käynnillä")}</h4><div class="check ${st?'done':''}">
      <div>${f.reported==="mineral"?T(`The survey says <b>mineral soil</b>, but the soil map shows ${dec(f.peat_ha_map)} ha of contract parcels on <b>peat</b>.`,`Kyselyssä on <b>kivennäismaa</b>, mutta maaperäkartan mukaan ${dec(f.peat_ha_map)} ha sopimuslohkoista on <b>turvetta</b>.`)
        :f.reported==="organic"?T(`The survey and the soil map agree: ${dec(f.peat_ha_map)} ha on peat. Confirm the parcels.`,`Kysely ja maaperäkartta täsmäävät: ${dec(f.peat_ha_map)} ha turvetta. Vahvista lohkot.`)
        :T(`No 2025 survey. The soil map shows ${dec(f.peat_ha_map)} ha on peat.`,`Vuoden 2025 kysely puuttuu. Maaperäkartan mukaan ${dec(f.peat_ha_map)} ha on turvetta.`)}</div>
      ${st?`<div class="row"><span class="pill ok">${T("Verified","Varmennettu")}: ${st==="peat"?T("peat","turvetta"):T("mineral soil","kivennäismaata")}</span><button class="btn sm" onclick="(()=>{const s=soilDec();delete s['${f.id}'];store.set('soil',s);const c=DATA.cards.find(c=>c.farm==='${f.id}'&&c.type==='soil_misreport');if(c){const d=dqDec();delete d[c.key];store.set('dq',d);}render();})()">${T("Undo","Kumoa")}</button></div>`
        :`<div class="row"><button class="btn" onclick="setSoil('${f.id}','peat')">${T("Parcels are peat","Lohkot ovat turvetta")}</button><button class="btn" onclick="setSoil('${f.id}','mineral')">${T("Parcels are mineral soil","Lohkot ovat kivennäismaata")}</button></div>`}
      <div class="mono muted">${[...(f.soil_flags||[]),...(f.peat_parcels||[]).slice(0,4).map(p=>"parcel:"+p.id)].map(esc).join(" · ")}</div></div></section>`:''}
    ${w.p25!=null?`<section class="sec"><h4>${T("Last summer","Viime kesä")}</h4><p>${T(`June–July 2025 was ${wet}: ${w.p25} mm of rain (normally ${w.pn} mm), ${w.h25} days above 27 °C (normally ${w.hn}).`,`Kesä–heinäkuu 2025 oli ${wet}: sadetta ${w.p25} mm (tavallisesti ${w.pn} mm), yli 27 °C:n päiviä ${w.h25} (tavallisesti ${dec(w.hn)}).`)}
      ${w.y25!=null&&w.yavg!=null?T(` Your ${cn(f.main)} yielded ${w.y25} t/ha against your usual ${w.yavg} t/ha.`,` ${cn(f.main)[0].toUpperCase()+cn(f.main).slice(1)}sato oli ${dec(w.y25)} t/ha, tavallisesti ${dec(w.yavg)} t/ha.`):''}</p></section>`:''}
    ${f.org>0&&st!=='mineral'?`<section class="sec"><h4>${T("What to do","Mitä tehdään")}</h4><div>
      <div class="opt"><span>${T("<b>Perennial grass</b> on the peat parcels","<b>Monivuotinen nurmi</b> turvelohkoille")}</span><b class="num">−${fmt(grass)} t/${T("yr","v")}</b></div>
      <div class="opt"><span>${T("<b>Raise the water table / rewet</b> (pilot lever L12). Largest cut; needs support and a contract.","<b>Vesitalouden nosto / ennallistaminen</b> (pilotti L12). Suurin vähennys, vaatii tukea ja sopimuksen.")}</span><b>${T("largest","suurin")}</b></div>
      <div class="opt"><span>${T("<b>Grow the contract crop on a mineral parcel.</b> Apetit's figure falls, but the climate only gains if the peat parcel's use changes.","<b>Sopimuskasvi kivennäismaalohkolle.</b> Apetitin luku laskee, mutta ilmasto hyötyy vain, jos turvelohkon käyttö muuttuu.")}</span><b class="num">−${fmt(orgNow)} t*</b></div>
      <p class="small muted" style="margin-top:6px">* ${T("Not a real reduction under the SBTi FLAG target if the peat parcel is still cultivated the same way.","Ei todellinen vähennys SBTi FLAG -tavoitteessa, jos turvelohkoa viljellään edelleen samoin.")}</p></div></section>`:''}
    <section class="sec"><h4>${T("Parcels","Lohkot")}</h4><div class="row" style="align-items:flex-start;gap:16px">${miniMap(f)}<div class="legend" style="flex-direction:column;gap:6px"><span><i class="peatfill"></i>${T("Peat","Turve")}</span><span><i style="background:var(--field);opacity:.6"></i>${T("Mineral soil","Kivennäismaa")}</span><span><i style="background:transparent;border:2px solid var(--water)"></i>${T("Under 100 m from water, no buffer strip","Alle 100 m vedestä, ei suojakaistaa")}</span></div></div></section>
    <section class="sec"><h4>${T("Sources","Lähteet")}</h4><div class="mono muted">A/farm_footprints_2025.csv · data/01_master/parcels.csv · data/03_farming/farm_survey_fi.csv · weather_monthly_1991_2060.csv ${esc(w.cell||"")} · METHODOLOGY.md §5</div></section>
  </article>`;}
page("farms","Farms & peat",()=>{
  const L=live(), f=FL.find(x=>x.id===fSel)||FL[0], top=FL.slice(0,HALF), nVer=top.filter(x=>x.org>0&&soilState(x.id)).length, nPeat=top.filter(x=>x.org>0).length;
  const row=x=>{const st=soilState(x.id);return `<button class="frow" aria-current="${x.id===fSel}" onclick="fSel='${x.id}';render()"><span class="rk num">${x.rank}</span><span><b>Farm ${x.id}</b> <span class="small muted">${Object.keys(x.crops||{}).map(c=>CROP[c]||c).join(", ")}</span>
     <span class="row" style="gap:5px;margin-top:3px">${x.org>0?`<span class="pill peat" style="font-size:11.5px">peat ${fmt(x.peat_ha_map,1)} ha</span>`:''}${st?`<span class="pill ok" style="font-size:11.5px">checked: ${st}</span>`:x.soil_flags&&x.soil_flags.length?'<span class="pill wa" style="font-size:11.5px">soil to check</span>':''}${x.src==="imputed"?'<span class="pill no" style="font-size:11.5px">no survey</span>':''}</span>
     <span class="mb"><i style="width:${100*(x.t-x.org)/FL[0].t}%;background:var(--field)"></i><i class="peatfill" style="width:${100*(st==='mineral'?0:x.org)/FL[0].t}%"></i></span></span><span class="num" style="text-align:right;font-weight:700">${fmt(x.t)}<br><span class="small muted">t</span></span></button>`;};
  return `${reviewBar("farms","Peat estimate, farm ranking and visit plan.")}
  <section style="display:flex;flex-direction:column;gap:10px"><div class="kick">Contract farming · south-west Finland · 2025</div>
    <h1><em>${HALF} of ${F.n} farms</em> make half of contract-farm emissions.</h1>
    <p class="lead">The cause is drained peat. It is ${fmt(100*F.org_t/F.total_t,0)} % of farm emissions and today's calculator leaves it out. Advisers can check these ${HALF} farms in one winter, before the GHG Protocol land standard applies on 1 January 2027.</p></section>
  <div class="grid g4">
    <div class="card kpi"><div class="l">Peat emissions, estimate</div><div class="v num">${fmt(L.peat)} t</div><div class="small muted" data-tip="Soil-map organic share scaled ×${F.org_scale}, calibrated on 2023–24 labels. Replaced farm by farm as advisers check the soil.">soil map ×${F.org_scale}, temporary ⓘ</div></div>
    <div class="card kpi"><div class="l">Checked on site</div><div class="v num">${nVer} / ${nPeat}</div><div class="small muted">${fmt(L.verifiedPeat)} t confirmed · ${fmt(L.removedPeat)} t removed</div></div>
    <div class="card kpi"><div class="l">Visit route from Säkylä</div><div class="v num">~${fmt(F.route.km_road)} km</div><div class="small muted">${HALF} visits · ${F.route.days} adviser days</div></div>
    <div class="card kpi"><div class="l">These ${HALF} farms cover</div><div class="v num">${fmt(100*F.top_org_t/F.org_t,0)} %</div><div class="small muted">of all peat emissions (${fmt(F.top_org_t)} t)</div></div>
  </div>
  <div class="farmwrap"><div style="display:flex;flex-direction:column;gap:14px">
    <div class="card"><div class="row"><h3>Contract farms, sized by emissions</h3><span class="sp"></span><label class="small"><input type="checkbox" ${showRoute?'checked':''} onchange="showRoute=this.checked;render()"> Visit route</label></div>
      <div class="legend" style="margin:6px 0"><span><i class="peatfill"></i>Has peat</span><span><i style="background:transparent;border:3px solid var(--rape);border-radius:50%"></i>Top ${HALF}</span><span><i style="background:var(--ink)"></i>Säkylä plant</span><span>Click a farm</span></div>${farmMap()}</div>
    <div class="card flist">${top.map(row).join("")}<div class="cut">↑ half of all farm emissions · next farms ↓</div>${FL.slice(HALF,40).map(row).join("")}</div></div>
    ${plan(f)}</div>`;
});

// ============ TARGETS (simulator) ============
let simScen="ndcs", simSel=null, simScale={};
function simDefault(){const s=DATA.pathway.macc.filter(m=>m.scenario===simScen);const cp=s[0]?.carbon_price_2030||100;simSel={};s.forEach(m=>{if(m.cost_net<=cp)simSel[m.id]=true;});simScale={};}
const sKey=l=>(l.scope.startsWith("scope1")||l.scope.startsWith("scope2"))?"s12":(["L13","L14","L15","L16","L17"].includes(l.id)?"flag":(l.flag?"flag":"s3nf"));
function simRun(){const rows=DATA.pathway.rows.filter(r=>r.scenario===simScen),L=DATA.pathway.levers.filter(l=>l.kind==="abatement");
  return rows.map(r=>{const red={s12:0,s3nf:0,flag:0};L.forEach(l=>{if(!simSel[l.id]||r.year<l.start)return;const a=l.abatement*(simScale[l.id]||1)*Math.min(1,(r.year-l.start+1)/Math.max(l.ramp,1));
    if(sKey(l)==="s12")red.s12+=a;else if(["L13","L14","L15","L16","L17"].includes(l.id)){red.flag+=a*0.86;red.s3nf+=a*0.14;}else if(l.flag)red.flag+=a;else red.s3nf+=a;});
    return {...r,sim_s12:r.bau_s12-red.s12,sim_s3nf:r.bau_s3nf-red.s3nf,sim_flag:r.bau_flag-red.flag};});}
function simAuto(){const mm=Object.fromEntries(DATA.pathway.macc.filter(m=>m.scenario===simScen).map(m=>[m.id,m.cost_net])),L=DATA.pathway.levers.filter(l=>l.kind==="abatement");simSel={};simScale={};
  const gaps=()=>{const r=simRun(),g={s12:0,s3nf:0,flag:0};[2030,2035].forEach(y=>{const x=r.find(z=>z.year===y);for(const k in g)g[k]=Math.max(g[k],x["sim_"+k]-x["tgt_"+k]);});return g;};
  for(let it=0;it<80;it++){const g=gaps();if(Object.values(g).every(v=>v<=0))break;const acts=[];
    L.forEach(l=>{const k=sKey(l);const serves=g[k]>0||(["L13","L14","L16"].includes(l.id))&&(g.flag>0||g.s3nf>0);if(!serves)return;const cur=simSel[l.id]?(simScale[l.id]||1):0;const next=cur===0?1:cur===1?1.5:cur===1.5?2:null;if(next==null)return;acts.push({l,next,eff:mm[l.id]*(next>1?next:1)+(next>1?15:0)});});
    if(!acts.length)break;acts.sort((a,b)=>a.eff-b.eff);const a=acts[0];simSel[a.l.id]=true;if(a.next>1)simScale[a.l.id]=a.next;}
  audit("simulator_autoclose",simScen,JSON.stringify({simSel,simScale}));render();}
page("targets","Targets",()=>{
  if(!simSel)simDefault();
  const R=simRun(),L=DATA.pathway.levers.filter(l=>l.kind==="abatement"),mm=Object.fromEntries(DATA.pathway.macc.filter(m=>m.scenario===simScen).map(m=>[m.id,m.cost_net]));
  const cost=L.filter(l=>simSel[l.id]).reduce((a,l)=>a+l.annual_cost_eur*(simScale[l.id]||1),0),ab=L.filter(l=>simSel[l.id]).reduce((a,l)=>a+l.abatement*(simScale[l.id]||1),0);
  const cp=DATA.pathway.macc.find(m=>m.scenario===simScen)?.carbon_price_2030, lab={s12:"Scope 1+2",s3nf:"Scope 3 (non-FLAG)",flag:"FLAG (land-based)"};
  const gap=(y,k)=>{const x=R.find(z=>z.year===y);return x["sim_"+k]-x["tgt_"+k];};
  const ok=k=>gap(2030,k)<=0&&gap(2035,k)<=0;
  const tile=k=>`<div class="card"><div class="row" style="justify-content:space-between"><h3>${lab[k]}</h3><span class="pill ${ok(k)?'ok':gap(2030,k)<=0?'wa':'no'}">${ok(k)?'met 2030 & 2035':gap(2030,k)<=0?'met 2030, short 2035':'short in 2030'}</span></div>
     ${lineChart([{name:"No action",pts:R.map(r=>[r.year,r["bau_"+k]]),color:"var(--muted)",dash:1,w:2},{name:"Your plan",pts:R.map(r=>[r.year,r["sim_"+k]]),color:"var(--water)",w:3},{name:"SBTi target",pts:R.map(r=>[r.year,r["tgt_"+k]]),color:"var(--rape)",w:3}],{width:420,height:210,x0:2025,x1:2035,yFmt:v=>fmt(v/1000,0)+"k"})}
     <p class="small">2030: <b class="num">${gap(2030,k)<=0?'met by '+fmt(-gap(2030,k)):fmt(gap(2030,k))+' t short'}</b> · 2035: <b class="num">${gap(2035,k)<=0?'met by '+fmt(-gap(2035,k)):fmt(gap(2035,k))+' t short'}</b></p></div>`;
  const allOk=["s12","s3nf","flag"].every(ok);
  return `${reviewBar("targets","Base year, SBTi targets and the measure plan.")}
  <section style="display:flex;flex-direction:column;gap:10px"><div class="kick">SBTi near-term targets · base year 2025 adjusted for Foodhills</div>
    <h1>${allOk?'This plan <em>meets every target</em>.':'Find the <em>cheapest plan</em> that meets every target.'}</h1>
    <p class="lead">Targets follow the SBTi minimum rates (Scope 1+2 −4.2 %/yr, Scope 3 −2.5 %/yr, FLAG −3.03 %/yr). Measures start with those cheaper than the carbon price. Press <b>Find cheapest plan</b> to close every gap at least cost. Structural changes and better data are never counted as reductions.</p></section>
  <div class="row"><label for="scen" class="small muted">Policy scenario</label><select id="scen" onchange="simScen=this.value;simDefault();render()">${DATA.pathway.scenarios.map(s=>`<option value="${s}" ${s===simScen?'selected':''}>${esc(SCEN[s]||s)}</option>`).join("")}</select>
    <button class="btn" onclick="simDefault();render()">Measures below carbon price (€${fmt(cp)}/t)</button><button class="btn pri" onclick="simAuto()">Find cheapest plan</button>
    ${Object.values(simScale).some(v=>v>1)?`<span class="pill wa" data-tip="Scaled beyond the design estimate in the lever catalogue. An expert must confirm the extra potential exists.">${Object.values(simScale).filter(v=>v>1).length} measures scaled up, validate</span>`:''}<span class="pill">${Object.keys(simSel).filter(k=>simSel[k]).length} measures · ${fmt(ab)} t/yr · €${fmt(cost/1e6,2)}M/yr · avg €${fmt(ab?cost/ab:0)}/t</span></div>
  <div class="grid g3">${tile("s12")}${tile("s3nf")}${tile("flag")}</div>
  <details class="acc"><summary><span class="ic">${Object.keys(simSel).filter(k=>simSel[k]).length}</span><span class="tt"><b>Measures in the plan</b><span>Switch measures on or off, or scale them, and watch the charts change</span></span><span></span></summary><div class="body">${table(L.slice().sort((a,b)=>mm[a.id]-mm[b.id]),[
    {h:"On",f:r=>`<input type="checkbox" aria-label="${esc(r.name)}" ${simSel[r.id]?"checked":""} onchange="simSel['${r.id}']=this.checked;render()">`},
    {h:"Measure",f:r=>`<b>${esc(r.name)}</b> <span class="tag">${r.id}</span>`},{h:"Counts toward",f:r=>({s12:"Scope 1+2",s3nf:"Scope 3",flag:"FLAG"})[sKey(r)]},{h:"t/yr",n:1,f:r=>fmt(r.abatement*(simScale[r.id]||1))},{h:"€ per t",n:1,f:r=>fmt(mm[r.id])},{h:"From",k:"start"},{h:"Confidence",k:"confidence"},
    {h:"Scale",f:r=>`<select aria-label="scale" onchange="simScale['${r.id}']=+this.value;render()">${[0.5,1,1.5,2].map(v=>`<option value="${v}" ${(simScale[r.id]||1)===v?'selected':''}>${v}×</option>`).join("")}</select>${(simScale[r.id]||1)>1?' <span class="pill wa">beyond design, validate</span>':''}`}],{max:40})}</div></details>
  <details class="more"><summary>Base year, targets and cost curve</summary>${(()=>{const b=DATA.pathway.base;return table([
      {o:"2025 as reported",s12:b.reported_2025.s1+b.reported_2025.s2m,s3:b.reported_2025.s3,f:b.reported_2025.flag,n:"Foodhills only in December, not comparable"},
      {o:"2025 adjusted (recommended)",s12:b.adjusted_2025.s1+b.adjusted_2025.s2m,s3:b.adjusted_2025.s3,f:b.adjusted_2025.flag,n:"full year of Foodhills; SBTi V2 prefers the latest complete year"},
      {o:"2019 recalculated",s12:b.recalc_2019.s1+b.recalc_2019.s2m,s3:b.recalc_2019.s3,f:null,n:"grain trade and Foodhills estimated; no FLAG split possible"}],
      [{h:"Base year option",k:"o"},{h:"Scope 1+2",n:1,f:r=>fmt(r.s12)},{h:"Scope 3",n:1,f:r=>fmt(r.s3)},{h:"FLAG",n:1,f:r=>fmt(r.f)},{h:"Note",k:"n"}]);})()}
    <p class="small muted" style="margin:8px 0 14px">${esc(DATA.pathway.foodhills_adjustment.basis)}</p>
    ${table(DATA.pathway.levers.slice().sort((a,b)=>(a.cost??1e9)-(b.cost??1e9)),[{h:"Id",k:"id"},{h:"Measure",k:"name"},{h:"Kind",f:r=>`<span class="pill ${r.kind==='abatement'?'':'wa'}">${r.kind==='abatement'?'reduction':r.kind}</span>`},{h:"t/yr",n:1,f:r=>fmt(r.abatement)},{h:"Range",n:1,f:r=>fmt(r.low)+"–"+fmt(r.high)},{h:"€/t",n:1,f:r=>r.cost==null?"–":fmt(r.cost)},{h:"Basis",k:"basis"}],{max:40})}</details>`;
});

// ============ RISK & NATURE ============
let crScen="ssp245";
page("risk","Risk & nature",()=>{
  const C=DATA.climate, eurR=s=>(C.euro||[]).filter(r=>r.scenario===s), sum=(rows,k)=>rows.reduce((a,r)=>a+(r[k]||0),0);
  const today=eurR("historical"), fut=eurR(crScen), c2=C.c2.filter(r=>r.scenario===crScen);
  const N=DATA.nature, pr=N.priority.slice().sort((a,b)=>a.priority_rank-b.priority_rank), maxS=Math.max(...pr.map(r=>r.priority_score));
  const byId=Object.fromEntries(pr.map(r=>[r.catchment_id,r]));
  const adap=(C.adaptation||[]).filter(r=>r.scenario==="ssp245"&&r.net_benefit_eur>0).slice(0,3);
  const hedgeToday=C.hedge.note.match(/cuts expected shortfall cost (\d+)/), h245=Math.round(100*(C.hedge.cut245||0));
  // nature map
  const feats=N.geo.features.filter(f=>f.properties.region==="FI_SW");const pts=feats.flatMap(f=>f.geometry.coordinates[0]);
  const lx=Math.min(...pts.map(p=>p[0])),hx=Math.max(...pts.map(p=>p[0])),ly=Math.min(...pts.map(p=>p[1])),hy=Math.max(...pts.map(p=>p[1]));
  const W=560,H=440,k=Math.cos((ly+hy)/2*Math.PI/180),sc=Math.min(W/((hx-lx)*k),H/(hy-ly)),P=p=>[((p[0]-lx)*k*sc).toFixed(1),((hy-p[1])*sc).toFixed(1)];
  const top5=new Set(pr.slice(0,5).map(r=>r.catchment_id));
  let map=`<svg class="chart" viewBox="0 0 ${((hx-lx)*k*sc).toFixed(0)} ${((hy-ly)*sc).toFixed(0)}" role="img" aria-label="Catchment priority map">`;
  feats.forEach(f=>{const r=byId[f.properties.catchment_id]||{},t=(r.priority_score||0)/maxS;map+=`<path d="M${f.geometry.coordinates[0].map(P).join("L")}Z" fill="${top5.has(f.properties.catchment_id)?'#ae3f2c':r.priority_score>0?`color-mix(in srgb,#2f6e9f ${Math.round(20+80*t)}%,#e2edf5)`:'#eceee6'}" stroke="#fbfcf8" stroke-width="1" data-tip="${esc(`<b>${f.properties.catchment_id}</b> · ${f.properties.receiving_water_type}, ${f.properties.ecological_status_class} status<br>${fmt(r.apetit_p_to_water_kg)} kg P · ${fmt(r.apetit_n_to_water_kg)} kg N from contract parcels<br>rank ${r.priority_rank}`)}"/>`;});
  N.hotspots.filter(h=>h.lon>=lx&&h.lon<=hx&&h.lat>=ly&&h.lat<=hy).forEach(h=>{const [x,y]=P([h.lon,h.lat]);map+=`<circle cx="${x}" cy="${y}" r="3.5" fill="#f0bd16" stroke="#141f19" stroke-width=".8" data-tip="${esc(`<b>${h.parcel_id}</b> ${h.crop}, ${fmt(h.area_ha,1)} ha · ${fmt(h.p_kg,1)} kg P<br>→ ${h.recommended}`)}"/>`;});
  map+=`</svg>`;
  return `${reviewBar("risk","Climate risk to contract crops and nutrient priorities.")}
  <section style="display:flex;flex-direction:column;gap:10px"><div class="kick">Physical climate risk · SBTN nature priorities</div>
    <h1>Weather risk is <em>already here</em>. Nutrient pressure sits in a few catchments.</h1>
    <p class="lead">Yield models learned from 15 seasons of farm data (6.8 % backtest error) price the bad years in euros. Under every climate scenario 2041–60 looks much like today, so the priority is managing bad years now.</p></section>
  <div class="grid g4">
    <div class="card kpi"><div class="l">Expected shortfall cost, today</div><div class="v num">${eur(sum(today,"exp_extra_cost_eur"))}/yr</div><div class="small muted">1-in-10 year: ${eur(sum(today,"p90_extra_cost_eur"))} ${src("C/c3_euro_risk.csv (historical)")}</div></div>
    <div class="card kpi"><div class="l">Same, 2041–60</div><div class="v num">${eur(sum(fut,"exp_extra_cost_eur"))}/yr</div><div class="small muted">${esc(SSP[crScen])} · 1-in-10: ${eur(sum(fut,"p90_extra_cost_eur"))}</div></div>
    <div class="card kpi"><div class="l">Pea from Finland and Sweden</div><div class="v num">−${hedgeToday?hedgeToday[1]:'44'} %</div><div class="small muted">expected pea shortfall cost today; −${h245} % under SSP2-4.5</div></div>
    <div class="card kpi"><div class="l">Contract phosphorus to water</div><div class="v num">${fmt(N.metrics.total_p_kg/1000,1)} t P</div><div class="small muted">top-50 fields carry ${fmt(N.hotspots.reduce((a,h)=>a+h.p_kg,0)/N.metrics.total_p_kg*100,0)} % ${src("D/d1_metrics.json")}</div></div>
  </div>
  <details class="acc"><summary><span class="ic">☁</span><span class="tt"><b>Climate risk to the contract crops</b><span>Bad-year chances by crop and climate scenario, and the adaptation that pays back</span></span><span></span></summary><div class="body">
  <div class="row"><span class="small muted">Climate scenario</span><div class="seg" role="group" aria-label="Climate scenario">${Object.keys(SSP).map(s=>`<button aria-pressed="${s===crScen}" onclick="crScen='${s}';render()">${esc(SSP[s])}</button>`).join("")}</div></div>
  <div class="grid g2">
    <div class="card"><h3>Chance of a bad year (below 80 % of normal), 2041–60</h3>${barH(c2,{width:560,label:r=>`${CROP[r.crop]||r.crop}, ${REGION[r.region]||r.region}`,value:r=>100*r.p_bad_year,fmtV:v=>fmt(v,0)+" %",color:()=>"var(--rape)",tipFn:r=>`${CROP[r.crop]} ${REGION[r.region]}: mean yield ${fmt(r.mean_yield_change_pct,1)} % vs 1991–2020`})}</div>
    <div class="card"><h3>Adaptation that pays back</h3>${adap.map(a=>`<div class="opt"><span><b>${esc(String(a.option).replace(/_/g," "))}</b> · ${esc(CROP[a.crop]||a.crop)}, ${esc(REGION[a.region]||a.region)}</span><b class="num">+${eur(a.net_benefit_eur)}/yr</b></div>`).join("")}<p class="small muted" style="margin-top:8px">Irrigation costed at €250/ha/yr; replace with Apetit's figures. ${src("C/c3_adaptation.csv")}</p></div>
  </div>
  </div></details>
  <details class="acc"><summary><span class="ic">P</span><span class="tt"><b>Nature: where phosphorus reaches water</b><span>Top 5 catchments ${pr.slice(0,5).map(r=>r.catchment_id).join(", ")} · map, hotspot fields and a costed programme</span></span><span></span></summary><div class="body">
  <div class="grid g2">
    <div class="card"><h3>Where contract fields put most phosphorus into water</h3><div class="legend" style="margin:6px 0"><span><i style="background:#ae3f2c"></i>Top 5 catchments</span><span><i style="background:#2f6e9f"></i>Higher priority</span><span><i style="background:#f0bd16;border-radius:50%"></i>Hotspot field</span></div>${map}</div>
    <div class="card"><h3>Programme for the top 5 catchments</h3>${table(N.programme,[{h:"Catchment",k:"catchment_id"},{h:"Fields",n:1,k:"contract_parcels"},{h:"kg P now",n:1,f:r=>fmt(r.p_kg)},{h:"kg P avoided",n:1,f:r=>fmt(r.p_avoided_kg)},{h:"€/yr",n:1,f:r=>fmt(r.eur_yr)},{h:"€ per kg P",n:1,f:r=>fmt(r.eur_per_kg_p)}])}
      <p class="small muted" style="margin-top:8px">Measures: buffer strips, catch crops, gypsum, phosphorus draw-down. Every field measure waits for an agronomist's review.</p></div>
  </div>
  </div></details>
  <details class="more"><summary>All climate and nature tables</summary>${table(fut,[{h:"Region",f:r=>esc(REGION[r.region]||r.region)},{h:"Crop",f:r=>esc(CROP[r.crop]||r.crop)},{h:"Contracted t",n:1,f:r=>fmt(r.contracted_t)},{h:"Expected shortfall t",n:1,f:r=>fmt(r.exp_shortfall_t)},{h:"Expected €/yr",n:1,f:r=>fmt(r.exp_extra_cost_eur)},{h:"1-in-10 €",n:1,f:r=>fmt(r.p90_extra_cost_eur)},{h:"Extra t CO2e (imports)",n:1,f:r=>fmt(r.exp_extra_tco2e)}])}
    <div style="height:12px"></div>${table(pr,[{h:"Rank",n:1,k:"priority_rank"},{h:"Catchment",k:"catchment_id"},{h:"Region",f:r=>esc(REGION[r.region]||r.region)},{h:"kg P",n:1,f:r=>fmt(r.apetit_p_to_water_kg)},{h:"kg N",n:1,f:r=>fmt(r.apetit_n_to_water_kg)},{h:"Score",n:1,f:r=>fmt(r.priority_score,2)}],{max:45})}
    <div style="height:12px"></div>${table(N.d2.slice(0,15),[{h:"#",n:1,k:"rank"},{h:"Material",k:"name_en"},{h:"Origin",k:"origin"},{h:"t CO2e",n:1,f:r=>fmt(r.tco2e)},{h:"EUDR",f:r=>r.eudr?"in scope":"–"},{h:"Why it matters",k:"rationale"}])}</details>`;
});

// ============ METHOD (footer) ============
page("method","Method",()=>{const log=store.get("audit",[]);
  return `<section style="display:flex;flex-direction:column;gap:10px"><div class="kick">How it works</div><h1>Method, scores and audit log</h1></section>
  <div class="grid g2"><div class="card"><h3>How expert review works</h3><ol class="small" style="padding-left:18px;margin:8px 0 0">
    <li>The agent proposes; it never overwrites source data. Each correction records the old and new value, the rule, evidence and confidence.</li>
    <li>Low-confidence flags and changes that move a category are routed to an expert.</li>
    <li>Rejecting a correction or checking a farm's soil changes the inventory and FLAG figures straight away.</li>
    <li>Each module stays Draft until a named reviewer approves it. The board memo is locked until all four are approved.</li>
    <li>Everything reproduces from the raw files with one command: <span class="tag">python run_all.py &lt;package&gt;</span> (about 2 minutes, identical outputs).</li></ol></div>
  <div class="card"><h3>Auto-scored results (public dev keys and backtests)</h3>${table(DATA.scores,[{h:"Task",k:"task"},{h:"Navigator",n:1,f:r=>esc(r.ours)},{h:"Baseline",n:1,f:r=>esc(r.baseline)},{h:"How measured",k:"how"}])}
    <p class="small muted" style="margin-top:8px">Forecast tasks carry real uncertainty; nobody should expect 100 % there.</p></div></div>
  <div class="card"><h3>Production path on Apetit's Microsoft stack</h3>${table(DATA.stack,[{h:"Layer",k:"layer"},{h:"Hackathon",k:"now"},{h:"Apetit production",k:"prod"}])}</div>
  <div class="card"><h3>Assumptions and limits</h3><ul class="small" style="padding-left:18px;margin:8px 0 0">${DATA.assumptions.map(a=>`<li>${esc(a)}</li>`).join("")}</ul></div>
  <div class="card"><div class="row"><h3>Audit log in this browser (${log.length})</h3><span class="sp"></span><button class="btn sm" onclick="exportAudit()">Export audit log</button></div>${table(log.slice().reverse(),[{h:"Time",f:r=>esc(r.ts.slice(0,19).replace("T"," "))},{h:"Reviewer",k:"reviewer"},{h:"Action",k:"action"},{h:"Target",k:"target"},{h:"Detail",k:"detail"}],{max:200})}</div>`;
},{hidden:true});
function exportAudit(){const txt=JSON.stringify({exported:new Date().toISOString(),approvals:store.get("approvals",{}),decisions:dqDec(),soil_checks:soilDec(),log:store.get("audit",[])},null,2);
  showModal("Audit log (JSON)",txt);}
function showModal(title,txt){document.getElementById("modal")?.remove();const m=document.createElement("div");m.id="modal";
  m.innerHTML=`<div style="position:fixed;inset:0;background:rgba(0,0,0,.45);z-index:200;display:flex;align-items:center;justify-content:center" onclick="if(event.target===this)this.parentNode.remove()"><div class="card" style="width:min(860px,92vw)"><div class="row"><b>${esc(title)}</b><span class="sp"></span><button class="btn pri sm" id="cpy">Copy</button><button class="btn sm" onclick="document.getElementById('modal').remove()">Close</button></div><textarea style="width:100%;height:60vh;margin-top:8px;font:13px/1.5 var(--mono);border:1px solid var(--line);border-radius:8px;padding:8px" readonly></textarea></div></div>`;
  document.body.appendChild(m);m.querySelector("textarea").value=txt;m.querySelector("#cpy").onclick=async()=>{try{await navigator.clipboard.writeText(m.querySelector("textarea").value);toast("Copied");}catch(e){m.querySelector("textarea").select();toast("Press Ctrl/Cmd+C to copy");}};}

// ============ ASK NAVIGATOR (copilot) ============
let chat=[],busy=false,SAMPLE=null;
(async()=>{try{if(window.claude&&window.claude.use){SAMPLE=await window.claude.use("sample");renderAsk();if(current==="brief")render();}}catch(e){SAMPLE=null;}})();
function tokenize(s){return (s.toLowerCase().match(/[a-zåäöü0-9%]+/g)||[]).filter(w=>w.length>2&&!STOP.has(w));}
const STOP=new Set("the and what was were how many which for from with that this are does did per all incl after why our should".split(" "));
function retrieve(q,k=4){const qt=tokenize(q),docs=DATA.kb,N=docs.length,df={};docs.forEach(d=>new Set(d._t||(d._t=tokenize(d.title+" "+d.text))).forEach(w=>df[w]=(df[w]||0)+1));
  return docs.map(d=>{let s=0;const tf={};d._t.forEach(w=>tf[w]=(tf[w]||0)+1);qt.forEach(w=>{if(tf[w])s+=(1+Math.log(tf[w]))*Math.log(1+N/(df[w]||1));});return {d,s:s/Math.sqrt(d._t.length+20)};}).filter(x=>x.s>0).sort((a,b)=>b.s-a.s).slice(0,k).map(x=>x.d);}
const r1=v=>typeof v==="number"?Math.round(v*10)/10:v;
const TOOLS=[
 {name:"search_evidence",description:"Full-text search over computed results, inventory lines, levers, catchments, climate results, framework digest and method docs. Returns snippets with an evidence reference to cite.",inputSchema:{type:"object",properties:{query:{type:"string"}},required:["query"]},execute:({query})=>retrieve(query,6).map(d=>({title:d.title,text:d.text.slice(0,900),evidence:d.evidence}))},
 {name:"get_inventory",description:"2025 GHG inventory KPIs and category totals (tCO2e), including any changes from the reviewer's decisions. Optional category substring returns its top line items.",inputSchema:{type:"object",properties:{category:{type:"string"}}},
  execute:({category})=>{const L=live();return {kpi:{scope1:r1(DATA.kpi.s1),scope2_market:r1(DATA.kpi.s2m),scope3:r1(DATA.kpi.s3),flag:r1(DATA.kpi.flag),flag_share:r1(DATA.kpi.flag_share*100)+"%",organic_soil_t:r1(DATA.kpi.org_soil_t)},after_review:{total:r1(L.total),flag:r1(L.flag),change:r1(L.delta)},categories:DATA.inventory.categories.map(c=>({scope:c.scope,category:c.category,tco2e:r1(c.tco2e)})),lines:category?DATA.inventory.lines.filter(l=>l.category.includes(category)||String(l.line_item).includes(category)).sort((a,b)=>b.tco2e-a.tco2e).slice(0,25):undefined,evidence:"A/lines_long.csv; submissions/A2_inventory_2025_submission.csv"};}},
 {name:"get_farms",description:"Contract-farm emissions ranking for 2025 (Finland): farms making half of emissions, peat (organic soil) emissions per farm, soil-check status, visit route.",inputSchema:{type:"object",properties:{farm_id:{type:"string"}}},
  execute:({farm_id})=>({half_n:HALF,total_t:F.total_t,peat_t:F.org_t,route_km:F.route.km_road,days:F.route.days,farms:(farm_id?FL.filter(f=>f.id===farm_id):FL.slice(0,HALF)).map(f=>({id:f.id,rank:f.rank,t:f.t,peat_t:f.org,peat_ha:f.peat_ha_map,reported_soil:f.reported,soil_check:soilState(f.id)})),evidence:"A/farm_footprints_2025.csv; data/01_master/parcels.csv"})},
 {name:"get_levers",description:"Decarbonisation measures: abatement t/yr, €/t, start year, confidence, basis.",inputSchema:{type:"object",properties:{}},execute:()=>DATA.pathway.levers.map(l=>({id:l.id,name:l.name,kind:l.kind,abatement:l.abatement,eur_per_t:l.cost,start:l.start,confidence:l.confidence,basis:l.basis}))},
 {name:"get_pathway",description:"SBTi pathway row for an NGFS scenario (net_zero_2050, below_2c, low_demand, delayed_transition, fragmented_world, ndcs, current_policies) and a year 2025–2035: no-action, with-measures and target values for s12, s3nf, flag and the gaps.",inputSchema:{type:"object",properties:{scenario:{type:"string"},year:{type:"number"}},required:["scenario","year"]},execute:({scenario,year})=>({row:DATA.pathway.rows.find(r=>r.scenario===scenario&&r.year===year)||"not found",base:DATA.pathway.base,evidence:"B/pathways.csv; B/b_results.json"})},
 {name:"get_climate_risk",description:"Climate yield risk by region, crop and scenario (historical, ssp126, ssp245, ssp585): yield change, bad-year probability, € shortfall cost, adaptation, FI–SE hedge.",inputSchema:{type:"object",properties:{crop:{type:"string"},scenario:{type:"string"}}},execute:({crop,scenario})=>{const f=r=>(!crop||r.crop===crop)&&(!scenario||r.scenario===scenario);return {c2:DATA.climate.c2.filter(f),euro:DATA.climate.euro.filter(f),adaptation:DATA.climate.adaptation.filter(f).slice(0,10),hedge:DATA.climate.hedge,evidence:"submissions/C2_*.csv; C/c3_euro_risk.csv"};}},
 {name:"get_nature",description:"SBTN catchment priorities, top-5 programme, hotspot fields and value-chain materiality screening.",inputSchema:{type:"object",properties:{catchment_id:{type:"string"}}},execute:({catchment_id})=>({metrics:DATA.nature.metrics,priority:DATA.nature.priority.filter(r=>!catchment_id||r.catchment_id===catchment_id).sort((a,b)=>a.priority_rank-b.priority_rank).slice(0,12),programme:DATA.nature.programme,d2_top:DATA.nature.d2.slice(0,8).map(d=>({name:d.name_en,origin:d.origin,tco2e:d.tco2e,rationale:d.rationale})),evidence:"submissions/D1_*.csv; D/d2_materiality.csv"})},
 {name:"get_data_errors",description:"2025 data errors found by the data-quality agent, with old and new value, reason, confidence, impact and the reviewer's decision. Optional issue_type filter.",inputSchema:{type:"object",properties:{issue_type:{type:"string"}}},execute:({issue_type})=>{const by={};DATA.cards.forEach(c=>by[c.type]=(by[c.type]||0)+1);return {counts:by,draft_check:DATA.dq.draft_check,errors:DATA.cards.filter(c=>!issue_type||c.type===issue_type).slice(0,20).map(c=>({...c,decision:dqDec()[c.key]||"pending"})),evidence:"A/corrections_log.csv; submissions/A1_issues_submission.csv"};}}];
const SYS=`You are the Climate & Nature Navigator copilot for Apetit (Finnish food company: frozen vegetables, rapeseed oil, contract farmers in Finland and Sweden). The data is a synthetic twin (Since AI 2026 package); say so if the user may mistake it for real figures.
Rules: 1) Use the tools for facts; never answer numbers from memory and never invent figures. 2) Cite evidence for claims as [evidence: ...] using the strings the tools return. 3) Follow GHG Protocol, SBTi (incl. FLAG), SBTN and NGFS logic; method changes and structural changes are never reductions. 4) If the tools have nothing relevant, say so and suggest asking an expert. 5) Be short and decision-oriented: the answer first, then 2–4 supporting points, then evidence. Plain text, no markdown headings. 6) Answer in the language of the question.`;
const EX=["Why is our pea footprint so much higher than the calculator says?","Which farms should our advisers visit first?","Which measures close the FLAG gap cheapest?","Is soy protein isolate in EUDR scope?","Mitä ilmastoriskit maksavat herneelle?"];
const md=s=>esc(s).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>");
function trimSentence(t,n=700){if(t.length<=n)return t;const cut=t.slice(0,n),i=Math.max(cut.lastIndexOf(". "),cut.lastIndexOf(".\n"));return (i>200?cut.slice(0,i+1):cut)+" …";}
function renderAsk(){const mode=SAMPLE?"claude":"retrieval";$("#aimode").innerHTML=mode==="claude"?'<span class="pill ok">Claude, live</span>':'<span class="pill wa" data-tip="No language model in this view; answers are the best matching evidence">evidence search</span>';
  $("#chat").innerHTML=chat.length?chat.map(m=>`<div class="msg ${m.r}">${m.r==="a"?md(m.t):esc(m.t)}${m.tools?`<div class="ev">tools: ${esc(m.tools)}</div>`:""}${m.ev?`<div class="ev">evidence: ${esc(m.ev)}</div>`:""}</div>`).join("")
    :`<p class="small muted">Answers come from Navigator's own tables and the framework documents, with sources. In production this runs on Azure OpenAI.</p>${EX.map(x=>`<button class="btn sm" style="text-align:left" onclick="$('#q').value=this.textContent;ask()">${esc(x)}</button>`).join("")}`;
  const c=$("#chat");c.scrollTop=c.scrollHeight;}
async function ask(){const q=$("#q").value.trim();if(!q||busy)return;$("#q").value="";chat.push({r:"u",t:q});audit("copilot_question","",q);
  if(SAMPLE){busy=true;const msg={r:"a",t:"Thinking…",tools:""};chat.push(msg);renderAsk();const used=[];
    const tools=TOOLS.map(t=>({...t,execute:inp=>{used.push(t.name);msg.tools=[...new Set(used)].join(", ");return t.execute(inp||{});}}));
    const hist=chat.filter(m=>m!==msg).slice(-8).map(m=>({role:m.r==="u"?"user":"assistant",content:m.t}));hist[hist.length-1].content=SYS+"\n\nQuestion: "+q;
    try{const res=await SAMPLE(hist,{tools,modelTier:"default",onText:({text})=>{msg.t=text;renderAsk();}});msg.t=res.text||msg.t;}
    catch(e){const h=retrieve(q)[0];msg.t=(e.code==="not_granted"?"AI access was not granted in this view. ":"The AI call failed. ")+(h?"Best evidence found:\n\n"+trimSentence(h.text):"");msg.ev=h?.evidence;}
    busy=false;renderAsk();return;}
  const hits=retrieve(q);chat.push(hits.length?{r:"a",t:trimSentence(hits[0].text)+(hits.length>1?`\n\nRelated: ${hits.slice(1).map(x=>x.title).join(" · ")}`:""),ev:hits[0].evidence}:{r:"a",t:"I found no evidence for that in the data. I will not guess; please rephrase or ask an expert."});renderAsk();}
async function aiMemo(){if(!SAMPLE||!allApproved())return;const L=live();
  const facts={kpi:DATA.kpi,after_review:{total:L.total,flag:L.flag,peat_verified_t:L.verifiedPeat,peat_removed_t:L.removedPeat},actions:DATA.actions,farms:{half_n:HALF,total_t:F.total_t,peat_t:F.org_t,route_km:F.route.km_road,days:F.route.days},base:DATA.pathway.base,targets:DATA.pathway.targets.filter(t=>[2030,2035].includes(t.year)),hedge:DATA.climate.hedge,nature:DATA.nature.metrics,approvals:store.get("approvals",{}),assumptions:DATA.assumptions};
  showModal("Board memo (draft)","Drafting…");
  try{const res=await SAMPLE(`Write a one-page board memo (max 400 words) for Apetit's management titled "Climate & nature: decisions for Q1 2027". Sections: Situation (3 bullets) / Decisions requested (numbered; owner, t CO2e, €) / Risks and assumptions / Approvals (who approved what, when). Use ONLY the facts in this JSON and round sensibly. State that figures come from a synthetic data twin.\nFACTS:\n${JSON.stringify(facts).slice(0,60000)}`,{cache:false,onText:({text})=>{const t=document.querySelector("#modal textarea");if(t)t.value=text;}});
    const t=document.querySelector("#modal textarea");if(t)t.value=res.text;audit("board_memo","brief","");}catch(e){const t=document.querySelector("#modal textarea");if(t)t.value="The AI call failed: "+(e.message||e.code);}}
const openAsk=()=>{$("#drawer").classList.add("on");$("#drawer").setAttribute("aria-hidden","false");$("#scrim").classList.add("on");renderAsk();setTimeout(()=>$("#q").focus(),50);};
const closeAsk=()=>{$("#drawer").classList.remove("on");$("#drawer").setAttribute("aria-hidden","true");$("#scrim").classList.remove("on");};
$("#askBtn").onclick=openAsk;$("#closeAsk").onclick=closeAsk;$("#scrim").onclick=closeAsk;$("#askGo").onclick=ask;
$("#q").addEventListener("keydown",e=>{if(e.key==="Enter")ask();});document.addEventListener("keydown",e=>{if(e.key==="Escape")closeAsk();});

{const ORDER=["brief","add","data","farms","targets","risk","method"];PAGES.sort((a,b)=>ORDER.indexOf(a.id)-ORDER.indexOf(b.id));}
