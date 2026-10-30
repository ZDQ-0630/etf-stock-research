// Conservative US regular-close gate. Source attestations are inputs, not proof of independence.
const holidays=new Set(['2026-01-01','2026-01-19','2026-02-16','2026-04-03','2026-05-25','2026-06-19','2026-07-03','2026-09-07','2026-11-26','2026-12-25']);
const early=new Set(['2026-11-27','2026-12-24']);
const epoch=s=>typeof s==='string' && /(?:Z|[+-]\d\d:\d\d)$/.test(s)?Date.parse(s):NaN;
const parts=t=>Object.fromEntries(new Intl.DateTimeFormat('en-CA',{timeZone:'America/New_York',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit',hourCycle:'h23'}).formatToParts(new Date(t)).filter(x=>x.type!=='literal').map(x=>[x.type,x.value]));
const day=p=>`${p.year}-${p.month}-${p.day}`;
function isOpen(d){const w=new Date(d+'T12:00:00Z').getUTCDay();return w!==0&&w!==6&&!holidays.has(d)}
function previousDay(d){return new Date(Date.parse(d+'T12:00:00Z')-86400000).toISOString().slice(0,10)}
function latestSession(now){let p=parts(now),d=day(p);if(!d.startsWith('2026-'))return null;for(let i=0;i<8;i++){if(!d.startsWith('2026-'))return null;let close=early.has(d)?13:16;if(isOpen(d)&&(d!==day(p)||Number(p.hour)>=close))return d;d=previousDay(d)}return null}
function host(url){try{let u=new URL(url);return u.protocol==='https:'?u.hostname.toLowerCase().replace(/^www\./,''):null}catch{return null}}
function rawHash(v){return typeof v==='string'&&/^[a-f0-9]{64}$/i.test(v)}
export function validateClose(symbol,quotes,calendar,now=Date.now()){
 const bad=reason=>({ok:false,status:'unverified',reason});
 if(!Number.isFinite(now))return bad('invalid clock');
 const latest=latestSession(now);if(!latest)return bad('calendar supported only for 2026; manual update required');
 if(!calendar||calendar.source_url!=='https://www.nyse.com/trade/hours-calendars'||!rawHash(calendar.source_sha256)||calendar.unplanned_closure_reviewed!==true)return bad('missing official calendar evidence and exceptional-closure review');
 const check=epoch(calendar.checked_at);if(!Number.isFinite(check)||check>now||now-check>24*3600000)return bad('calendar exceptional-closure review is stale or future');
 if(!Array.isArray(quotes?.observations))return bad('requires two distinct close observations');
 const all=quotes.observations.filter(x=>x?.symbol===symbol);if(all.length!==2)return bad('requires two distinct close observations');
 let hosts=all.map(x=>host(x.source_url));if(hosts.some(x=>!x)||hosts[0]===hosts[1]||!all[0].provider_id||!all[1].provider_id||all[0].provider_id===all[1].provider_id)return bad('distinct source identities required; ownership independence still requires review');
 for(const q of all){
  const t=epoch(q.timestamp),retrieved=epoch(q.retrieved_at),hour=early.has(latest)?13:16;
  if(!Number.isFinite(t))return bad('invalid close timestamp');
  const p=parts(t);
  if(q.session!=='official_regular_close'||q.trade_date!==latest||!isOpen(q.trade_date)||day(p)!==latest||Number(p.hour)!==hour||Number(p.minute)!==0||Number(p.second)!==0)return bad('not the latest completed US regular-session close');
  if(!Number.isFinite(retrieved)||retrieved<t||retrieved>now||now-retrieved>24*3600000||now-t>96*3600000)return bad('quote or retrieval is stale, future, or inconsistent');
  if(!rawHash(q.source_sha256)||typeof q.price!=='number'||!Number.isFinite(q.price)||q.price<=0)return bad('missing source hash or valid price');
 }
 if(Math.abs(all[0].price-all[1].price)>Math.max(.01,all[0].price*.001))return bad('source close prices differ by more than 0.1% or one cent');
 return {ok:true,status:'provisionally_checked',price:all[0].price,timestamp:all[0].timestamp,trade_date:latest,providers:all.map(q=>({provider_id:q.provider_id,source_url:q.source_url,source_sha256:q.source_sha256,retrieved_at:q.retrieved_at,price:q.price})),limitations:'Calendar and source content, extraordinary closures, exchange-specific settlement and provider independence require independent review; hashes do not establish truth.'};
}
