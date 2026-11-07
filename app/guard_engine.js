/* ===================== NUMBER GUARD ENGINE (port of guard.py) ===================== */
const GUARD = (()=>{
  const med = a => { if(!a.length) return NaN; const s=a.slice().sort((x,y)=>x-y), m=s.length>>1; return s.length%2?s[m]:(s[m-1]+s[m])/2; };
  const near = (x,t,tol=.35) => x>0 && Math.abs(Math.log10(x)-Math.log10(t))<tol;
  const mode = a => { const c={}; a.forEach(v=>c[v]=(c[v]||0)+1); return Object.keys(c).sort().reduce((b,k)=>c[k]>c[b]?k:b, Object.keys(c).sort()[0]); };
  function run(rows, MAT, SUP){
    const t0=performance.now();
    const E=rows.map(r=>{ const q=+r.quantity, a=+r.net_amount, mv=+r.movement_type;
      const kg = r.uom==='TO'?q*1000 : r.uom==='KG'?q : NaN;
      return {...r, quantity:q, net_amount:a, year:+String(r.posting_date).slice(0,4), key:`erp:${r.doc_no}:${r.line_no}`, kg, credit:(q<0||a<0||mv===102||mv===122)}; });
    const bySup={}; E.forEach(r=>(bySup[r.supplier_id]=bySup[r.supplier_id]||[]).push(r));
    const supCur={}, supN={}; for(const s in bySup){supCur[s]=mode(bySup[s].map(r=>r.currency)); supN[s]=bySup[s].length;}
    E.forEach(r=>r.ppk=r.net_amount/r.kg);
    const pm={}; E.filter(r=>r.uom!=='EUR'&&!r.credit&&r.currency==='EUR'&&r.kg>0).forEach(r=>(pm[r.material_id]=pm[r.material_id]||[]).push(r.ppk));
    const medEur={}; for(const m in pm) medEur[m]=med(pm[m]);
    const fx={EUR:1}; ['SEK','USD'].forEach(c=>{ const v=E.filter(r=>r.currency===c&&r.kg>0&&!r.credit).map(r=>r.ppk/medEur[r.material_id]).filter(x=>!isNaN(x)); fx[c]=v.length?med(v):1; });
    E.forEach(r=>{ r.ppkEur=r.ppk/(fx[r.currency]||1); r.r=r.ppkEur/medEur[r.material_id]; });
    const qg={}, qm={}; E.filter(r=>r.kg>0&&!r.credit).forEach(r=>{(qg[r.supplier_id+'|'+r.material_id]=qg[r.supplier_id+'|'+r.material_id]||[]).push(r.kg);});
    E.filter(r=>r.kg>0).forEach(r=>{(qm[r.material_id]=qm[r.material_id]||[]).push(r.kg);});
    const qgm={}; for(const k in qg) qgm[k]=med(qg[k]); const qmm={}; for(const k in qm) qmm[k]=med(qm[k]);
    E.forEach(r=>{ const k=r.supplier_id+'|'+r.material_id; r.qmed=qgm[k]??qmm[r.material_id]; r.qr=r.kg/r.qmed; });
    const sa={}; E.filter(r=>r.uom==='EUR'&&!r.credit).forEach(r=>(sa[r.supplier_id]=sa[r.supplier_id]||[]).push(r.net_amount));
    const supAmt={}; for(const s in sa) supAmt[s]=med(sa[s]);
    const share={}; for(const s in bySup){ const c={}; bySup[s].forEach(r=>c[r.material_id]=(c[r.material_id]||0)+1); for(const m in c) share[s+'|'+m]=c[m]/bySup[s].length; }
    const out=[];
    const add=(r,type,conf,fix,why,impactKg)=>out.push({r,type,conf,fix,why,impactKg});
    for(const r of E){
      if(r.credit) continue;
      if(r.uom==='EUR'&&r.currency==='EUR'){ const ar=r.net_amount/supAmt[r.supplier_id];
        if(near(ar,fx.SEK,.12)) add(r,'currency_error','medium',{f:'currency',from:'EUR',to:'SEK'},{k:'spendSEK',ar,fx:fx.SEK});
        continue; }
      const regM=SUP[r.supplier_id];
      if(regM && regM!==r.material_id && (share[r.supplier_id+'|'+r.material_id]||0)<.15){ add(r,'material_mismatch','medium',{f:'material_id',from:r.material_id,to:regM},{k:'mat',regM}); continue; }
      if(!(r.kg>0)||isNaN(r.r)) continue;
      if(r.uom==='KG'&&r.r>250&&r.qr<.01){ add(r,'unit_error','high',{f:'quantity',from:r.quantity,to:+(r.quantity*1000).toFixed(3)},{k:'unit',ppk:r.ppkEur,norm:medEur[r.material_id],x:r.r},r.quantity*999); continue; }
      if((near(r.r,.1,.25)&&near(r.qr,10,.45))||(near(r.r,10,.25)&&near(r.qr,.1,.45))){ const f=r.r<1?.1:10;
        add(r,'decimal_shift',near(r.r,f,.12)?'high':'medium',{f:'quantity',from:r.quantity,to:+(r.quantity*f).toFixed(3)},{k:'dec',f,x:r.r,qmed:r.qmed},r.kg*(f-1)); continue; }
      if(r.currency==='EUR'&&(supCur[r.supplier_id]==='SEK'||supCur[r.supplier_id]==='USD')&&supN[r.supplier_id]>=2){ add(r,'currency_error','high',{f:'currency',from:'EUR',to:supCur[r.supplier_id]},{k:'supcur',c:supCur[r.supplier_id]}); continue; }
      if(r.currency==='EUR'&&near(r.r,fx.SEK,.12)&&r.qr>.4&&r.qr<2.5){ add(r,'currency_error','medium',{f:'currency',from:'EUR',to:'SEK'},{k:'pSEK',x:r.r,fx:fx.SEK}); continue; }
    }
    // duplicates (stable sort by date)
    const d=E.filter(r=>!r.credit).map((r,i)=>[r,i]).sort((a,b)=>a[0].posting_date<b[0].posting_date?-1:a[0].posting_date>b[0].posting_date?1:a[1]-b[1]).map(x=>x[0]);
    const seen=new Map();
    for(const r of d){ const k=[r.supplier_id,r.material_id,r.quantity.toFixed(3),r.net_amount.toFixed(2)].join('|'); const dt=Date.parse(r.posting_date);
      if(seen.has(k)&&(dt-seen.get(k).dt)/864e5<=31){ const s=seen.get(k); add(r,'duplicate_record','high',{f:'row',from:'row',to:'remove'},{k:'dup',of:s.key,days:Math.round((dt-s.dt)/864e5)},r.kg>0?-r.kg:null); }
      else seen.set(k,{dt,key:r.key}); }
    // impacts
    out.forEach(o=>{ const m=MAT[o.r.material_id]||{}; o.ef=m.ef;
      o.t = (o.impactKg!=null && m.u==='kg' && m.ef!=null) ? o.impactKg*m.ef/1000 : null;
      if(o.type==='currency_error'){ const rate=o.fix.to==='SEK'?fx.SEK:fx.USD; o.eur=o.r.net_amount-o.r.net_amount/rate;
        if(o.r.uom==='EUR'&&m.u==='EUR'&&m.ef!=null) o.t=-o.eur*m.ef/1000; }
      else if(o.type==='duplicate_record') o.eur=o.r.net_amount; else o.eur=0; });
    return {issues:out, fx, medEur, n:E.length, ms:performance.now()-t0};
  }
  function parseCSV(text){
    const rows=[]; let i=0,f='',row=[],q=false;
    while(i<text.length){ const c=text[i];
      if(q){ if(c==='"'){ if(text[i+1]==='"'){f+='"';i++;} else q=false; } else f+=c; }
      else if(c==='"') q=true; else if(c===','){row.push(f);f='';} else if(c==='\n'||c==='\r'){ if(c==='\r'&&text[i+1]==='\n')i++; row.push(f);f=''; if(row.length>1||row[0]!=='')rows.push(row); row=[]; }
      else f+=c; i++; }
    if(f!==''||row.length){row.push(f);rows.push(row);}
    const h=rows.shift().map(s=>s.trim()); return rows.map(r=>Object.fromEntries(h.map((k,j)=>[k,r[j]])));
  }
  return {run, parseCSV};
})();
