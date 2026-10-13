import sys,json,zipfile,io
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from advisor.core import load_env,analyze,generate
from advisor.exporting import export
ROOT=Path(__file__).resolve().parents[1];load_env(ROOT)
run=analyze((ROOT/'samples/虚构省级科技项目指南.txt').read_text(encoding="utf-8"),(ROOT/'samples/虚构企业基础档案.json').read_text(encoding="utf-8"));run['id']='acceptance-live'
print('匹配结果',[(p['name'],p['match_score'],p['qualification']) for p in run['projects']],flush=True)
assert len(run['projects'])==2
assert run['projects'][0]['match_score']==100
assert run['projects'][0]['qualification']=='符合形式条件'
assert run['projects'][1]['match_score']==60
checks={x['field']:x for x in run['projects'][1]['checks']}
assert checks['patents']['gap']==2 and checks['rd_ratio']['gap']==1.2
run=generate(run,run['projects'][0]['name'],'用口径一致的事实写申报规划，缺失预算与性能目标标记待企业确认。')
assert run['draft']['chinese_characters']>=1000
out=ROOT/'docs/验收成果';out.mkdir(exist_ok=True)
(out/'真实模型验收.json').write_text(json.dumps(run,ensure_ascii=False,indent=2),encoding="utf-8");(out/'真实模型成果整包.zip').write_bytes(export(run))
with zipfile.ZipFile(io.BytesIO(export(run))) as z:
 for n in z.namelist():
  if n in ['项目申报书草稿.docx','佐证附件清单.csv']: (out/n).write_bytes(z.read(n))
print('文案字数',run['draft']['chinese_characters'],'工具调用',len(run['model_calls']),flush=True)
