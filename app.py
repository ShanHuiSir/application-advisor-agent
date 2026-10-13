"""Local-only desktop service, with durable jobs and periodic reminders."""
import base64,json,os,sqlite3,threading,uuid,time,sys,traceback
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse
from advisor.core import load_env,extract_file,analyze,generate,answer,calendar,china_now
from advisor.exporting import export,ics
ROOT=Path(__file__).resolve().parent
DATA=Path(os.environ.get('ADVISOR_DATA_DIR',str(ROOT/'runtime')));DATA.mkdir(parents=True,exist_ok=True)
load_env(ROOT)
DB=DATA/'advisor.sqlite'
with sqlite3.connect(DB) as db:
    db.execute('CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, data TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY, data TEXT NOT NULL)')
JOBS={};LOCK=threading.Lock()
def save(run):
    with sqlite3.connect(DB) as db:db.execute('INSERT OR REPLACE INTO runs VALUES (?,?)',(run['id'],json.dumps(run,ensure_ascii=False)))
def read(id):
    with sqlite3.connect(DB) as db:r=db.execute('SELECT data FROM runs WHERE id=?',(id,)).fetchone()
    if not r:raise ValueError('记录不存在')
    return json.loads(r[0])
def enqueue(fn):
    id=uuid.uuid4().hex;JOBS[id]={'status':'running','message':'Agent正在调用模型并核验原文，通常需要30至120秒'}
    def work():
        try:JOBS[id]={'status':'done','result':fn()}
        except Exception as e:JOBS[id]={'status':'error','message':str(e)}
    threading.Thread(target=work,daemon=True).start();return {'job_id':id}
def check_alerts():
    with sqlite3.connect(DB) as db:rows=db.execute('SELECT id,data FROM runs').fetchall()
    for rid,data in rows:
        run=json.loads(data)
        for e in calendar(run['projects']):
            # A persisted reminder is emitted once per threshold and policy source.
            if e['status']=='已截止' or e['days_left']>7:continue
            threshold=1 if e['days_left']<=1 else (3 if e['days_left']<=3 else 7)
            id=run['source_hashes']['policy']+e['project']+e['label']+str(threshold)
            info={**e,'run_id':rid,'reminder_days':threshold,'raised_at':china_now().isoformat(),'read':False}
            with sqlite3.connect(DB) as db:db.execute('INSERT OR IGNORE INTO alerts VALUES (?,?)',(id,json.dumps(info,ensure_ascii=False)))
def reminder_loop():
    while True:
        try:check_alerts()
        except Exception:pass
        time.sleep(60)
def dispatch(path,p):
    if path=='/api/config':
        key=p.get('key','').strip()
        if not key:raise ValueError('Key为空')
        os.environ['DEEPSEEK_API_KEY']=key
        if p.get('remember'): (ROOT/'.env').write_text('DEEPSEEK_API_KEY='+key+'\nDEEPSEEK_MODEL=deepseek-chat\n')
        return {'configured':True}
    if path=='/api/analyze':
        policy=extract_file(p['policy']['name'],base64.b64decode(p['policy']['data'],validate=True))
        profile=extract_file(p['profile']['name'],base64.b64decode(p['profile']['data'],validate=True))
        def fn():
            run=analyze(policy,profile);run['id']=uuid.uuid4().hex;run['source_names']=[p['policy']['name'],p['profile']['name']];run['source_inputs']={'policy':policy,'profile':profile};save(run);return run
        return enqueue(fn)
    if path=='/api/generate':
        run=read(p['run_id'])
        def fn():
            result=generate(run,p['project'],p.get('guidance',''));save(result);return result
        return enqueue(fn)
    if path=='/api/ask':return enqueue(lambda:answer(read(p['run_id']),p['question']))
    if path=='/api/reminders/check':check_alerts();return {'checked_at':china_now().isoformat()}
    if path=='/api/alerts/read':
        with sqlite3.connect(DB) as db:
            for aid,data in db.execute('SELECT id,data FROM alerts').fetchall():
                obj=json.loads(data);obj['read']=True;db.execute('UPDATE alerts SET data=? WHERE id=?',(json.dumps(obj,ensure_ascii=False),aid))
        return {'ok':True}
    raise ValueError('未知操作')
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,obj,status=200,ctype='application/json; charset=utf-8'):
        data=obj if isinstance(obj,bytes) else json.dumps(obj,ensure_ascii=False).encode()
        self.send_response(status);self.send_header('Content-Type',ctype);self.send_header('Content-Length',str(len(data)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();self.wfile.write(data)
    def do_GET(self):
        path=urlparse(self.path).path
        try:
            if path=='/api/config':return self.send({'configured':bool(os.environ.get('DEEPSEEK_API_KEY')),'model':os.environ.get('DEEPSEEK_MODEL','deepseek-chat')})
            if path.startswith('/api/jobs/'):return self.send(JOBS.get(path.rsplit('/',1)[1],{'status':'error','message':'任务不存在；服务重启后请查看历史记录'}))
            if path=='/api/history':
                with sqlite3.connect(DB) as db:rows=db.execute('SELECT data FROM runs ORDER BY rowid DESC LIMIT 30').fetchall()
                return self.send([{'id':r['id'],'name':r['profile']['name'],'created_at':r['created_at'],'has_draft':'draft' in r} for r in [json.loads(x[0]) for x in rows]])
            if path=='/api/alerts':
                with sqlite3.connect(DB) as db:rows=db.execute('SELECT data FROM alerts ORDER BY rowid DESC LIMIT 30').fetchall()
                return self.send([json.loads(r[0]) for r in rows])
            if path.startswith('/api/runs/'):
                r=read(path.rsplit('/',1)[1]);r['calendar']=calendar(r['projects']);return self.send(r)
            if path.startswith('/api/export/'):
                r=read(path.rsplit('/',1)[1]);return self.send(export(r),ctype='application/zip')
            if path.startswith('/api/calendar/'):
                return self.send(ics(read(path.rsplit('/',1)[1])),ctype='text/calendar; charset=utf-8')
            if path=='/api/samples':return self.send({'policy':(ROOT/'samples/虚构省级科技项目指南.txt').read_text(),'profile':(ROOT/'samples/虚构企业基础档案.json').read_text()})
            target=ROOT/'web'/('index.html' if path=='/' else path.lstrip('/'))
            if not target.resolve().is_relative_to((ROOT/'web').resolve()) or not target.is_file():return self.send({'error':'不存在'},404)
            ctype={'html':'text/html; charset=utf-8','css':'text/css; charset=utf-8','js':'text/javascript; charset=utf-8'}.get(target.suffix[1:],'application/octet-stream')
            self.send(target.read_bytes(),ctype=ctype)
        except ValueError as e:self.send({'error':str(e)},400)
        except Exception:self.send({'error':'读取失败，请检查文件或依赖'},500)
    def do_POST(self):
        origin=self.headers.get('Origin');expected=f'http://{self.headers.get("Host")}'
        if self.headers.get('X-Local-Client')!='advisor' or (origin and origin!=expected):return self.send({'error':'仅允许本地客户端调用'},403)
        try:
            n=int(self.headers.get('Content-Length','0'))
            if n>34*1024*1024:raise ValueError('请求过大')
            p=json.loads(self.rfile.read(n));self.send(dispatch(urlparse(self.path).path,p))
        except (ValueError,KeyError,TypeError) as e:self.send({'error':str(e)},400)
        except Exception:self.send({'error':'处理失败，请检查输入格式'},500)
def serve(port=8891):
    threading.Thread(target=reminder_loop,daemon=True).start()
    server=ThreadingHTTPServer(('127.0.0.1',port),Handler);print(f'申报参谋 http://127.0.0.1:{port}',flush=True);server.serve_forever()
if __name__=='__main__':serve(int(os.environ.get('ADVISOR_PORT','8891')))
