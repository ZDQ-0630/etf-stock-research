import json,unittest
from datetime import datetime,timezone
import cloud_snapshot as c
class SnapshotTests(unittest.TestCase):
 def test_completed_session_and_early_close(self):
  self.assertEqual(c.latest_date(datetime.fromisoformat('2026-11-27T17:59:00+00:00')),'2026-11-25')
  self.assertEqual(c.latest_date(datetime.fromisoformat('2026-11-27T18:00:00+00:00')),'2026-11-25')
  self.assertEqual(c.latest_date(datetime.fromisoformat('2026-11-27T18:15:00+00:00')),'2026-11-27')
  with self.assertRaises(ValueError):c.latest_date(datetime.fromisoformat('2027-01-05T12:00:00+00:00'))
 def test_nasdaq_fiscal_data_and_missing(self):
  raw=json.dumps({'data':{'symbol':'AAA','tradesTable':{'rows':[{'date':'10/29/2026','close':'$1,234.56'}]}}}).encode()
  self.assertEqual(c.parse_nasdaq(raw,'AAA','2026-10-29'),1234.56)
  self.assertIsNone(c.parse_nasdaq(raw,'AAA','2026-10-28'))
  self.assertIsNone(c.parse_nasdaq(raw,'BBB','2026-10-29'))
 def test_yahoo_date_converted_in_exchange_timezone(self):
  timestamp=int(datetime.fromisoformat('2026-10-29T13:30:00+00:00').timestamp())
  raw=json.dumps({'chart':{'result':[{'meta':{'symbol':'AAA','currency':'USD'},'timestamp':[timestamp],'indicators':{'quote':[{'close':[90]}]}}]}}).encode()
  self.assertEqual(c.parse_yahoo(raw,'AAA','2026-10-29'),90)
  self.assertIsNone(c.parse_yahoo(raw,'BBB','2026-10-29'))
 def test_forecast_does_not_invent_asof(self):
  raw=json.dumps({'data':{'symbol':'aaa','yearlyForecast':{'asOf':None,'rows':[{'fiscalEnd':'Dec 2028','consensusEPSForecast':5,'noOfEstimates':3}]}}}).encode()
  r=c.forecasts(raw,'AAA',{'forecasts':[{'end':'Dec 2028','eps_mean':4}]})
  self.assertIsNone(r['rows'][0]['vendor_asof']);self.assertEqual(r['rows'][0]['difference'],1);self.assertEqual(r['scenario_updates'],'none; no automatic adoption')
 def test_treasury_real_and_missing(self):
  raw=b'<feed xmlns="http://www.w3.org/2005/Atom" xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"><entry><updated>2026-10-29T19:00:00Z</updated><d:NEW_DATE>2026-10-29T00:00:00</d:NEW_DATE><d:TC_10YEAR>2.63</d:TC_10YEAR></entry></feed>'
  self.assertEqual(c.treasury(raw,'TC_10YEAR')[0]['value_pct'],2.63);self.assertEqual(c.treasury(raw,'BC_10YEAR'),[])
 def test_fred_retry_and_missing_remain_blocked(self):
  calls=[]
  def fail(*args,**kwargs):calls.append(1);raise TimeoutError('test timeout')
  record,body=c.get(('fred_DGS10','https://example.com'),opener=fail,pause=lambda n:None)
  self.assertFalse(record['ok']);self.assertIsNone(body);self.assertEqual(len(calls),3);self.assertEqual(len(record['attempts']),3)
  calls.clear();record,body=c.get(('yahoo_AAA','https://example.com'),opener=fail,pause=lambda n:None)
  self.assertEqual(len(calls),1)
if __name__=='__main__':unittest.main()
