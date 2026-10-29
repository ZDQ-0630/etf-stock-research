/* Stock research UI: facts, vendor estimates and user-adopted scenarios stay separate. */
(()=>{'use strict';
const $=id=>document.getElementById(id),data=window.STOCK_DATA,KEY='stock_research_scenarios_v1';
const finite=x=>typeof x==='number'&&Number.isFinite(x),fmt=x=>finite(x)?x.toLocaleString('en-US',{maximumFractionDigits:4}):'未验证';
function calculate({price,eps,pe,years,hurdle}){
 if(![price,eps,pe,years,hurdle].every(finite))throw Error('需要完整、有限的价格、EPS、倍数、年数和目标回报。');
 if(price<=0||eps<=0||pe<=0)throw Error('价格、退出EPS与PE须为正；负EPS不适用PE模型。');
 if(years<3||years>20||!Number.isInteger(years)||hurdle<=-1)throw Error('持有年数须为3–20的整数，目标年化须大于−100%。');
 const terminal=eps*pe,factor=(1+hurdle)**years;
 const result={terminal,annualized:(terminal/price)**(1/years)-1,max_entry:terminal/factor,required_eps:price*factor/pe};
 if(!Object.values(result).every(Number.isFinite)||factor<=0)throw Error('输入超出可计算范围。');
 return result;
}
window.StockResearchMath={calculate,storage_key:KEY};
if(!$('stockSelect'))return;
const node=(tag,text,cls)=>{const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n};
function source(parent,value){const url=typeof value==='string'?value:value?.url??value?.source_url;const label=typeof value==='object'?value?.name??value?.label??value?.title:null;if(!url){parent.append(node('span',' 来源未验证'));return}try{const u=new URL(url);if(!['https:','http:'].includes(u.protocol))throw Error();const a=node('a',label||'原始来源');a.href=u.href;a.target='_blank';a.rel='noopener noreferrer';parent.append(a)}catch{parent.append(node('span',String(label||url)))}}
function paragraph(parent,text,src){const p=node('p',text);if(src){p.append(' · ');source(p,src)}parent.append(p)}
function table(parent,headers,rows){const wrap=node('div',null,'tablewrap'),t=node('table'),head=node('thead'),tr=node('tr');headers.forEach(v=>tr.append(node('th',v)));head.append(tr);t.append(head);const body=node('tbody');rows.forEach(row=>{const r=node('tr');row.forEach(v=>r.append(node('td',v)));body.append(r)});t.append(body);wrap.append(t);parent.append(wrap);return body}
const companies=(data?.companies??[]).filter(c=>typeof c.symbol==='string');let selected=null;let inputs=[];
function clear(){ $('stockResults').replaceChildren();$('stockError').textContent='';window.lastStockResearch=null }
function number(el){return el.value.trim()===''?NaN:Number(el.value)}
function saved(){try{return JSON.parse(localStorage.getItem(KEY)||'{}')}catch{return {}}}
function save(){try{const all=saved();all[selected.symbol]={hurdle:$('stockHurdle').value,years:$('stockYears').value,rows:inputs.map(r=>({eps:r.eps.value,pe:r.pe.value,label:r.label.textContent}))};localStorage.setItem(KEY,JSON.stringify(all))}catch{$('stockError').textContent='浏览器无法保存；当前计算仍可使用。'}}
function compute(){clear();save();const price=selected.quote?.price,years=number($('stockYears')),hurdle=number($('stockHurdle'))/100;
 if(!finite(hurdle)){ $('stockError').textContent='请先填写你的目标年化回报；不会用默认目标替你判断。';return }
 const rows=[],errors=[];inputs.forEach((r,i)=>{if(!r.eps.value.trim()&&!r.pe.value.trim())return;try{const out=calculate({price,eps:number(r.eps),pe:number(r.pe),years,hurdle});rows.push({label:r.label.textContent,...out})}catch(e){errors.push(`情景${i+1}：${e.message}`)}});
 if(!rows.length&&!errors.length)errors.push('尚未采用情景：可载入分析情景或自行填写EPS与倍数。');
 $('stockError').textContent=errors.join(' ');
 if(rows.length){table($('stockResults'),['情景','退出毛价格 USD','价格年化','条件买价 USD','以当前价买入所需退出EPS'],rows.map(r=>[r.label,fmt(r.terminal),fmt(r.annualized*100)+'%',fmt(r.max_entry),fmt(r.required_eps)]));paragraph($('stockResults'),'计算忽略交易费、分红、税款和汇率，仅为条件价格算术；不构成个股推荐，也不是底部预测。');window.lastStockResearch={symbol:selected.symbol,price_date:selected.quote?.date,years,hurdle,rows}}
}
function render(){clear();selected=companies.find(c=>c.symbol===$('stockSelect').value);if(!selected)return;for(const id of ['stockFacts','stockForecasts','stockAssumptions'])$(id).replaceChildren();
 const facts=$('stockFacts'),q=selected.quote??{},a=selected.actuals??{};
 facts.append(node('h2',selected.symbol+' · '+(selected.name??'')));
 paragraph(facts,`行情：${fmt(q.price)} USD · 日期 ${q.date??'未验证'} · 时间 ${q.timestamp??'未验证'} · 时段 ${q.session??'未验证'}`,q.source);
 paragraph(facts,`财报事实 · 期间 ${a.period??'未验证'} · 单位 ${a.unit??'未验证'}；EPS须另核对每股/ADR口径。`,a.source_url);
 table(facts,['指标','披露值'],[['营收',fmt(a.revenue)],['经营利润',fmt(a.operating_income)],['经营利润率',finite(a.operating_margin)?fmt(a.operating_margin*100)+'%':'未验证'],['每股收益 EPS',fmt(a.eps)],['经营现金流',fmt(a.cfo)],[a.capex_label??'资本开支',fmt(a.capex)],[a.fcf_label??'自由现金流',fmt(a.fcf)]]);
 paragraph(facts,'缺失/限制：'+((selected.missing??[]).join('；')||'未列明不代表数据完整。'));paragraph(facts,'数据取回时间：'+(data.retrieved_at??'未验证')+'。取回时间不等于预测形成时间。');
 const forecasts=$('stockForecasts');forecasts.append(node('h2','数据商预测 · 尚未采用为分析假设'));
 if(!(selected.forecasts??[]).length)paragraph(forecasts,'暂无可展示的预测。');
 for(const f of selected.forecasts??[]){const implied=finite(q.price)&&q.price>0&&finite(f.eps_mean)&&f.eps_mean>0?` · 现价/该财年预测EPS ${fmt(q.price/f.eps_mean)}倍（按该预测财年EPS计算，不是统一NTM/TTM市盈率；口径未验证时仅算术参考）`:'';paragraph(forecasts,`${f.start??'未知'}—${f.end??'未知'} · EPS ${fmt(f.eps_mean)} · ${f.analysts??'未知'}家 · 口径 ${f.basis??'未验证'} · 预测asOf ${f.asof??'未验证'}${implied}`,f.source)}
 const section=$('stockAssumptions');section.append(node('h2','你采用的条件情景'));paragraph(section,'退出EPS必须与股价、倍数对应同一币种和每股/ADR单位。数据商预测不会自动填入；以下分析情景不等于市场一致预期。');
 const controls=node('div',null,'formgrid');for(const[id,label,value]of [['stockYears','持有年数','3'],['stockHurdle','目标年化回报 %','']]){const field=node('div',null,'field'),l=node('label',label);l.htmlFor=id;const input=node('input');input.id=id;input.type='number';input.step='any';input.value=value;field.append(l,input);controls.append(field)}section.append(controls);
 const body=table(section,['情景','退出EPS USD/同一股份','退出PE','分析依据'],[]);inputs=[];
 for(let i=0;i<3;i++){const tr=node('tr'),label=node('td',selected.scenarios?.[i]?.label??`情景${i+1}`),epstd=node('td'),petd=node('td'),eps=node('input'),pe=node('input');for(const [el,suffix,title]of [[eps,'eps','退出EPS'],[pe,'pe','退出PE']]){el.type='number';el.step='any';el.id=`stock_${i}_${suffix}`;el.setAttribute('aria-label',`情景${i+1} ${title}`)}epstd.append(eps);petd.append(pe);const rationale=node('td',selected.scenarios?.[i]?.rationale??'尚无来源化分析情景');tr.append(label,epstd,petd,rationale);body.append(tr);inputs.push({eps,pe,label})}
 const load=node('button','载入分析情景','button secondary');load.id='loadStockScenarios';load.type='button';section.append(load);paragraph(section,'公式：退出价=退出EPS×PE；价格年化=(退出价/现价)^(1/年数)−1；条件买价=退出价/(1+目标回报)^年数；所需EPS=现价×(1+目标回报)^年数/PE。');
 const old=saved()[selected.symbol];if(old&&Array.isArray(old.rows)){if(typeof old.years==='string')$('stockYears').value=old.years;if(typeof old.hurdle==='string')$('stockHurdle').value=old.hurdle;inputs.forEach((r,i)=>{if(typeof old.rows[i]?.eps==='string')r.eps.value=old.rows[i].eps;if(typeof old.rows[i]?.pe==='string')r.pe.value=old.rows[i].pe});paragraph(section,'已恢复此标的的浏览器本地输入（未独立核实）；修改输入后重新计算。')}
 load.onclick=()=>{clear();inputs.forEach((r,i)=>{const s=selected.scenarios?.[i];r.eps.value=s?.source_type==='analysis_assumption'&&finite(s.terminal_eps)?s.terminal_eps:'';r.pe.value=s?.source_type==='analysis_assumption'&&finite(s.terminal_pe)?s.terminal_pe:''});const years=selected.scenarios?.filter(s=>s.source_type==='analysis_assumption').map(s=>s.years);if(years?.length&&years.every(y=>y===years[0])&&finite(years[0]))$('stockYears').value=years[0];compute()};
 section.oninput=compute;
}
$('stockSelect').replaceChildren();for(const c of companies){const opt=node('option',c.symbol+' · '+(c.name??''));opt.value=c.symbol;$('stockSelect').append(opt)}const requestedStock=new URLSearchParams(location.search).get('symbol');if(companies.some(c=>c.symbol===requestedStock))$('stockSelect').value=requestedStock;$('stockSelect').onchange=render;if(companies.length)render();else $('stockError').textContent='个股数据尚未载入，未生成研究结果。';
})();
