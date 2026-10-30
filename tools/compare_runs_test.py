import json,subprocess,sys,tempfile,unittest
from pathlib import Path
class Tests(unittest.TestCase):
 def test_comparison_and_changed_method_block(self):
  with tempfile.TemporaryDirectory(dir='.') as root:
   cur=Path(root)/'cur';old=Path(root)/'old';cur.mkdir();old.mkdir();out=Path(root)/'result.json'
   def fixture(price,stamp,eps):
    scenario={'id':'reference','hurdle':.1,'terminal_eps':10,'terminal_pe':20,'years':3,'current':{'annualized':.1,'max_entry':150}}
    d={'bin':'5–10%','n':20,'nonoverlap':2,'censored':3,'downside':[-.2,-.1,0],'returns':[-.1,.1,.2]};risk={'symbol':'QQQM','status':'computed_for_research_only','current':{'date':stamp[:10],'dd':-.08},'distribution':{'126':d,'252':d,'3y':d}}
    research={'schema':'etf.cloud.daily_research.v1','stock_core_sha256':'stock','script_sha256':'script','baseline_sha256':'baseline','history_core_sha256':'history','risk_script_sha256':'risk','frozen_history_sha256':'frozen','computed_at':stamp,'rows':[{'symbol':'AAA','status':'computed_for_research_only','date':stamp[:10],'price':price,'scenarios':[scenario]}],'risk':[risk]}
    snap={'forecasts':{'AAA':{'rows':[{'fiscal_end':'Dec 2028','vendor_eps':eps,'vendor_asof':None}]}}}
    return research,snap
   for path,price,stamp,eps in [(old,100,'2026-10-28T10:00:00Z',10),(cur,90,'2026-10-29T10:00:00Z',9)]:
    r,s=fixture(price,stamp,eps);(path/'research-only.json').write_text(json.dumps(r),encoding='utf8');(path/'snapshot.json').write_text(json.dumps(s))
   cmd=[sys.executable,'tools/compare_runs.py',str(cur),str(old),str(out)];r=subprocess.run(cmd,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr);d=json.loads(out.read_text(encoding='utf8'));self.assertEqual(d['status'],'partial_comparison_only');self.assertEqual(d['stocks'][0]['current_price'],90);self.assertTrue(d['stocks'][0]['different_trading_date']);self.assertEqual(d['risk'][0]['distribution']['3y']['current']['nonoverlap'],2);self.assertIsNone(d['fundamental'][0]['vendor_asof']);out.unlink()
   f=cur/'research-only.json';r=json.loads(f.read_text(encoding='utf8'));r['risk'][0]['distribution']['3y']['bin']='10–15%';f.write_text(json.dumps(r),encoding='utf8');subprocess.run(cmd,check=True,capture_output=True);self.assertEqual(json.loads(out.read_text(encoding='utf8'))['risk'][0]['distribution']['3y']['status'],'different_drawdown_buckets_not_directly_comparable');out.unlink()
   f=cur/'research-only.json';r=json.loads(f.read_text(encoding='utf8'));r['script_sha256']='changed';f.write_text(json.dumps(r),encoding='utf8');subprocess.run(cmd,check=True,capture_output=True);self.assertEqual(json.loads(out.read_text(encoding='utf8'))['status'],'blocked')
if __name__=='__main__':unittest.main()
