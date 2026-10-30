import json,unittest
from datetime import datetime,timezone
import cloud_snapshot as c
class SnapshotTests(unittest.TestCase):
 def test_completed_session_and_early_close(self):
  self.assertEqual(c.latest_date(datetime.fromisoformat('2026-11-27T17:59:00+00:00')),'2026-11-25')
  self.assertEqual(c.latest_date(datetime.fromisoformat('2026-11-27T18:00:00+00:00')),'2026-11-27')
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
if __name__=='__main__':unittest.main()
