#!/usr/bin/env python3
"""Findora Portable: offline lost/found tracker, SQLite API, local model bridge."""
import argparse, json, os, sqlite3, threading, time, urllib.request, urllib.error
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

ROOT=Path(__file__).resolve().parent.parent
DB=ROOT/'data'/'findora.db'
WEB=ROOT/'assets'
PORT=8765

SCHEMA='''CREATE TABLE IF NOT EXISTS reports(
 id INTEGER PRIMARY KEY AUTOINCREMENT, kind TEXT NOT NULL CHECK(kind IN ('lost','found')),
 title TEXT NOT NULL, category TEXT NOT NULL, description TEXT NOT NULL,
 color TEXT DEFAULT '', brand TEXT DEFAULT '', location TEXT DEFAULT '',
 date_text TEXT NOT NULL, contact TEXT DEFAULT '', status TEXT DEFAULT 'open',
 created_at TEXT DEFAULT CURRENT_TIMESTAMP);
CREATE TABLE IF NOT EXISTS match_feedback(id INTEGER PRIMARY KEY AUTOINCREMENT, lost_id INTEGER, found_id INTEGER, feedback TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP);'''
def connect():
 c=sqlite3.connect(DB,timeout=8); c.row_factory=sqlite3.Row; return c
def init_db():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with connect() as c: c.executescript(SCHEMA)
def all_reports():
 with connect() as c: return [dict(r) for r in c.execute("SELECT * FROM reports ORDER BY created_at DESC, id DESC")]
def norm(s): return (s or '').strip().lower()
def score_pair(l,f):
 if l['kind']!='lost' or f['kind']!='found': return 0,[]
 reasons=[]; score=0
 if norm(l['category'])==norm(f['category']): score+=35; reasons.append('Same category (+35)')
 else: return 0,['Category differs (rejected)']
 for field,pts,label in [('color',15,'Color'),('brand',15,'Brand'),('location',20,'Location')]:
  a,b=norm(l.get(field)),norm(f.get(field))
  if a and b:
   if a==b: score+=pts; reasons.append(f'{label} match (+{pts})')
   elif a in b or b in a: score+=pts//2; reasons.append(f'{label} partial match (+{pts//2})')
   else: reasons.append(f'{label} differs')
 a,b=norm(l['description']),norm(f['description'])
 if a and b:
  from difflib import SequenceMatcher
  sim=SequenceMatcher(None,a,b).ratio()
  pts=round(sim*25); score+=pts; reasons.append(f'Description similarity (+{pts})')
 # Dates: penalize beyond a 30-day span, hard reject beyond 30 days
 try:
  from datetime import date
  delta=abs((date.fromisoformat(l['date_text'])-date.fromisoformat(f['date_text'])).days)
  if delta>30: return 0,reasons+['Dates more than 30 days apart (rejected)']
  if delta<=3: score+=10; reasons.append('Dates close (+10)')
  elif delta<=14: score+=5; reasons.append('Dates within 2 weeks (+5)')
 except Exception: pass
 return min(100,score),reasons
def matches():
 reports=all_reports(); lost=[r for r in reports if r['kind']=='lost' and r['status']=='open']; found=[r for r in reports if r['kind']=='found' and r['status']=='open']; out=[]
 for l in lost:
  for f in found:
   s,why=score_pair(l,f)
   if s>=45: out.append({'score':s,'lost':l,'found':f,'reasons':why})
 return sorted(out,key=lambda x:x['score'],reverse=True)
class Handler(SimpleHTTPRequestHandler):
 def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(WEB),**kwargs)
 def log_message(self,*args): pass
 def send_json(self,obj,status=200):
  b=json.dumps(obj,ensure_ascii=False).encode(); self.send_response(status); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(b))); self.send_header('Cache-Control','no-store'); self.end_headers(); self.wfile.write(b)
 def body(self):
  n=int(self.headers.get('Content-Length','0')); return json.loads(self.rfile.read(n) or b'{}')
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/api/reports': self.send_json(all_reports()); return
  if p=='/api/matches': self.send_json(matches()); return
  if p=='/api/status':
   model=ROOT/'models'/'qwen-7b-q5.gguf'; self.send_json({'ai_model_ready':model.exists() and model.stat().st_size>4500000000,'ai_endpoint':'http://127.0.0.1:8081/v1/chat/completions'}); return
  if p=='/api/health': self.send_json({'ok':True,'name':'Findora'}); return
  if p=='/': self.path='/index.html'
  return super().do_GET()
 def do_POST(self):
  p=urlparse(self.path).path; data=self.body()
  if p=='/api/reports':
   required=['kind','title','category','description','date_text']
   if any(not str(data.get(k,'')).strip() for k in required): self.send_json({'error':'Fill in all required fields.'},400); return
   if data.get('kind') not in ('lost','found'): self.send_json({'error':'Invalid report type'},400); return
   with connect() as c:
    cur=c.execute('INSERT INTO reports(kind,title,category,description,color,brand,location,date_text,contact) VALUES(?,?,?,?,?,?,?,?,?)',tuple(data.get(k,'') for k in ['kind','title','category','description','color','brand','location','date_text','contact']))
    rid=cur.lastrowid
   self.send_json({'ok':True,'id':rid}); return
  if p=='/api/report/status':
   try:
    with connect() as c: c.execute('UPDATE reports SET status=? WHERE id=?',(data.get('status','closed'),int(data['id'])))
    self.send_json({'ok':True})
   except Exception as e: self.send_json({'error':str(e)},400)
   return
  if p=='/api/chat':
   prompt=str(data.get('message','')).strip()
   if not prompt: self.send_json({'error':'Enter a message.'},400); return
   context={'reports':len(all_reports()),'matches':matches()[:5]}
   system=('You are Findora, an offline lost-and-found assistant. Help users find items, create useful descriptions, explain matching results, and guide them. '
           'Do not invent report data. Current local snapshot: '+json.dumps(context,ensure_ascii=False)+' . Be concise and clear.')
   payload={'model':'local-model','messages':[{'role':'system','content':system},{'role':'user','content':prompt}],'temperature':0.3,'max_tokens':500}
   req=urllib.request.Request('http://127.0.0.1:8081/v1/chat/completions',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'})
   try:
    with urllib.request.urlopen(req,timeout=120) as r: result=json.loads(r.read())
    answer=result['choices'][0]['message']['content']; self.send_json({'answer':answer,'source':'local model'}); return
   except Exception as e:
    self.send_json({'answer':'Local AI model is not running yet. Findora core still works. Run SETUP.bat to install the model, then restart START.bat.\n\nMeanwhile, I can guide you using Findora’s built-in matching rules.','source':'offline fallback','detail':str(e)}); return
  self.send_json({'error':'Unknown endpoint'},404)
def main():
 init_db(); parser=argparse.ArgumentParser(); parser.add_argument('--init-only',action='store_true'); args=parser.parse_args()
 if args.init_only: print('Findora database initialized at',DB); return
 server=ThreadingHTTPServer(('127.0.0.1',PORT),Handler); print(f'Findora running at http://127.0.0.1:{PORT}'); server.serve_forever()
if __name__=='__main__': main()
