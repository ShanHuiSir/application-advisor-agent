import unittest,tempfile,os,sys,json,sqlite3,uuid,io,zipfile
from unittest.mock import patch
from pathlib import Path
os.environ['ADVISOR_DATA_DIR']=tempfile.mkdtemp(prefix='advisor-test-')
import app
from advisor.exporting import export
class ServiceTests(unittest.TestCase):
 def setUp(self):
  with sqlite3.connect(app.DB) as db:db.execute('DELETE FROM runs');db.execute('DELETE FROM alerts')
  self.run={'id':uuid.uuid4().hex,'projects':[{'name':'虚构项目','deadlines':[{'label':'网报','date':'2026-11-15T17:00:00+08:00','quote':'2026年11月15日17:00'}]}],'source_hashes':{'policy':'test'}}
 def test_persistence(self):
  app.save(self.run);self.assertEqual(app.read(self.run['id']),self.run)
 def test_alert_deduplication_and_thresholds(self):
  app.save(self.run)
  from advisor.core import calendar
  from datetime import datetime
  def at(date):return lambda projects:calendar(projects,datetime.fromisoformat(date))
  with patch('app.calendar',at('2026-11-10T17:00:00+08:00')):app.check_alerts();app.check_alerts()
  with sqlite3.connect(app.DB) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM alerts').fetchone()[0],1)
  with patch('app.calendar',at('2026-11-13T17:00:00+08:00')):app.check_alerts();app.check_alerts()
  with sqlite3.connect(app.DB) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM alerts').fetchone()[0],2)
 def test_expired_never_alerts(self):
  app.save(self.run)
  with patch('app.calendar',return_value=[{'status':'已截止','days_left':-1}]):app.check_alerts()
  with sqlite3.connect(app.DB) as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM alerts').fetchone()[0],0)
 def test_export_hashes_and_complete_word(self):
  root=Path(__file__).resolve().parents[1];run=json.loads((root/'docs/验收成果/真实模型验收.json').read_text());data=export(run)
  import hashlib
  from docx import Document
  with zipfile.ZipFile(io.BytesIO(data)) as z:
   self.assertEqual(len(z.namelist()),7)
   for name,h in json.loads(z.read('SHA256.json')).items():self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),h)
   d=Document(io.BytesIO(z.read('项目申报书草稿.docx')));text='\n'.join(p.text for p in d.paragraphs)
   for s in run['draft']['sections']:
    self.assertIn(s['heading'],text)
    for para in s['body'].split('\n'):
     if para.strip():self.assertIn(para.strip(),text)
 def test_missing_source_field(self):
  with self.assertRaises(KeyError):app.dispatch('/api/analyze',{})
if __name__=='__main__':unittest.main()
