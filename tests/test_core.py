import unittest
from datetime import datetime
from advisor.core import match,calendar,chunks,retrieve,validate_policy,extract_file
from advisor.exporting import ics
class CoreTests(unittest.TestCase):
    def policy(self):
        return {'name':'研发专项','funding_wan':80,'funding_quote':'最高80万元','conditions':[{'field':'patents','op':'>=','value':2,'quote':'发明专利不少于2项'},{'field':'rd_ratio','op':'>=','value':4,'quote':'研发占比不低于4%'}],'deadlines':[{'label':'网报','date':'2026-11-15T17:00:00+08:00','quote':'网报2026年11月15日17:00'}],'attachments':['专利证书'],'unmodeled_conditions':[]}
    def test_numeric_boundary(self):
        p=self.policy();self.assertEqual(match(p,{'patents':2,'rd_ratio':4})['qualification'],'符合形式条件');r=match(p,{'patents':1,'rd_ratio':3.9});self.assertEqual(r['match_score'],0);self.assertAlmostEqual(r['checks'][1]['gap'],.1)
    def test_unknown_never_qualifies(self):
        r=match(self.policy(),{'patents':2});self.assertEqual(r['qualification'],'待核实');self.assertEqual(r['match_score'],50)
    def test_unmodeled_hard_condition(self):
        p=self.policy();p['unmodeled_conditions']=['无失信记录'];self.assertEqual(match(p,{'patents':3,'rd_ratio':5})['qualification'],'待核实')
    def test_evidence_rejects_hallucinated_threshold(self):
        p=self.policy();text='研发专项；最高80万元；发明专利不少于2项；研发占比不低于4%；网报2026年11月15日17:00';validate_policy({'projects':[p]},text);p['conditions'][0]['value']=5
        with self.assertRaises(ValueError):validate_policy({'projects':[p]},text)
    def test_deadline_at_and_after(self):
        p=self.policy();self.assertEqual(calendar([p],datetime.fromisoformat('2026-11-15T17:00:00+08:00'))[0]['status'],'即将截止');self.assertEqual(calendar([p],datetime.fromisoformat('2026-11-15T17:00:01+08:00'))[0]['status'],'已截止')
    def test_date_timezone_required(self):
        p=self.policy();p['deadlines'][0]['date']='2026-11-15T17:00:00'
        with self.assertRaises(ValueError):validate_policy({'projects':[p]},'研发专项；最高80万元；发明专利不少于2项；研发占比不低于4%；网报2026年11月15日17:00')
    def test_rag_retrieves_local_source(self):
        index=chunks('申报要求专利证书。\n研发费用比例为4%。','P');self.assertIn('专利',retrieve(index,'专利证书')[0]['text']);self.assertTrue(index[0]['id'].startswith('P'))
    def test_ics_utc_and_alarms(self):
        text=ics({'calendar':calendar([self.policy()])}).decode();self.assertIn('DTSTART:20261115T090000Z',text);self.assertEqual(text.count('BEGIN:VALARM'),3)
    def test_utf8_and_empty_input(self):
        self.assertEqual(extract_file('a.txt','政策'.encode()),'政策')
        with self.assertRaises(ValueError):extract_file('a.txt',b'')
        with self.assertRaises(ValueError):extract_file('a.exe',b'content')
if __name__=='__main__':unittest.main()
