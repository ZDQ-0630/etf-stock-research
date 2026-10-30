// Descriptive price-risk state only. Never mutates frozen history or estimates a bottom.
export function riskFor(symbol,snapshot,history,M){
 const bad=reason=>({symbol,status:'blocked',reason});const rows=history?.series?.[symbol],tail=snapshot.history_tail?.[symbol],date=snapshot.latest_scheduled_session;
 if(!Array.isArray(rows)||!rows.length||!Array.isArray(tail)||tail.length<2)return bad('Insufficient frozen history or paired dates');
 const cutoff=history.price_cutoff,last=rows.at(-1);if(last[0]!==cutoff||!date||date<cutoff||date>M.CALENDAR.end||cutoff<M.CALENDAR.start)return bad('Frozen date or reviewed calendar mismatch');
 if(M.lastComplete(new Date(snapshot.started_at))!==date)return bad('Session date does not match calendar at retrieval');
 const q=snapshot.prices.find(x=>x.symbol===symbol);if(!q||q.agreement!==true||q.session_date!==date||!q.sources?.nasdaq?.sha256||!q.sources?.yahoo?.sha256)return bad('Latest two-source observation missing');
 const byDate=new Map();for(const p of tail){if(byDate.has(p.date))return bad('Duplicate paired dates');if(typeof p.nasdaq!=='number'||typeof p.yahoo!=='number'||p.nasdaq<=0||p.yahoo<=0||p.agreement!==true||Math.abs(p.nasdaq-p.yahoo)>Math.max(.01,p.nasdaq*.001))return bad('Paired source disagreement');byDate.set(p.date,p)}
 const historic=new Map(rows),overlap=tail.filter(p=>historic.has(p.date));if(overlap.length<2)return bad('Less than two overlapping frozen observations');
 for(const p of overlap){const original=historic.get(p.date);if(Math.abs(original-p.nasdaq)>Math.max(.02,original*.001))return bad('Frozen history and current source disagree');}
 const added=[];for(let d=new Date(cutoff+'T00:00:00Z');;){d=new Date(d.valueOf()+86400000);const iso=d.toISOString().slice(0,10);if(iso>date)break;const weekday=d.getUTCDay();if(weekday===0||weekday===6||M.CALENDAR.holidays.includes(iso))continue;const p=byDate.get(iso);if(!p)return bad('Missing paired scheduled session '+iso);added.push([iso,p.nasdaq]);if(added.length>100)return bad('Too many new observations for this short-history adapter');}
 const states=M.states(rows),after=M.states([...rows,...added]);return {symbol,status:'computed_for_research_only',frozen:states.at(-1),current:after.at(-1),overlap_count:overlap.length,added_count:added.length,scope:'Observed date-only prices; unadjusted source basis and unusual exchange closures remain unverified; not a bottom forecast.'};
}
