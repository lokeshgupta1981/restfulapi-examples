from pathlib import Path
import json,subprocess,threading,shlex,urllib.request
from http.server import ThreadingHTTPServer,BaseHTTPRequestHandler
from bs4 import BeautifulSoup
R=Path(r'C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\resources-drafts')
BASE=Path(__file__).resolve().parent
jq=BASE/'bin/jq.exe'
fixture=BASE/'response.json'
cases=[(['-r','.data[0].name'], 'Ada'),(['.meta.total'],'3'),(['-r','.data[].name'],'Ada\nLin\nSam'),(['[.data[] | select(.active == true) | .name]'],['Ada','Sam']),(['.data | map(select(.total >= 10) | {id, total})'],[{'id':101,'total':12.5},{'id':103,'total':20}]),(['.data | map({id, name, team: (.team.name // "Unassigned")})'],[{'id':101,'name':'Ada','team':'Platform'},{'id':102,'name':'Lin','team':'Unassigned'},{'id':103,'name':'Sam','team':'API'}]),(['.data | length'],'3'),(['[.data[].total] | add'],'40.5'),(['-r','(["id","name"], (.data[] | [.id, .name])) | @csv'],'"id","name"\n101,"Ada"\n102,"Lin"\n103,"Sam"'),(['--arg','wanted','Ada','.data[] | select(.name == $wanted)'],{'id':101,'name':'Ada','active':True,'total':12.5,'team':{'name':'Platform'}}),(['--argjson','minimum','10','[.data[] | select(.total >= $minimum)]'],[{'id':101,'name':'Ada','active':True,'total':12.5,'team':{'name':'Platform'}},{'id':103,'name':'Sam','active':True,'total':20,'team':{'name':'API'}}]),(['-e','.meta.total == 3'],'true')]
for args,want in cases:
 r=subprocess.run([str(jq),*args,str(fixture)],capture_output=True,text=True,check=True)
 got=r.stdout.strip()
 assert (json.loads(got)==want if isinstance(want,(list,dict)) else got==want),(args,got)
seen=[]
class Echo(BaseHTTPRequestHandler):
 def log_message(self,*a):pass
 def run(self):
  n=int(self.headers.get('Content-Length','0'));body=self.rfile.read(n).decode('utf-8',errors='replace')
  seen.append({'method':self.command,'path':self.path,'body':body,'type':self.headers.get('Content-Type')})
  code=400 if self.path.startswith('/error') else 200
  data=json.dumps(seen[-1]).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 do_GET=run;do_POST=run;do_PUT=run;do_PATCH=run;do_DELETE=run;do_HEAD=run
server=ThreadingHTTPServer(('127.0.0.1',0),Echo);threading.Thread(target=server.serve_forever,daemon=True).start()
url='http://127.0.0.1:'+str(server.server_port)
for name in ('order.json','replacement.json','patch.json'):(BASE/name).write_text('{"quantity":2}',encoding='utf-8')
(BASE/'report.pdf').write_bytes(b'example file bytes')
curl_cases=[['--json','{"sku":"BOOK-7","quantity":2}',url+'/orders'],['--json','@order.json',url+'/orders'],['--request','PUT','--json','@replacement.json',url+'/products/7'],['--request','PATCH','-H','Content-Type: application/merge-patch+json','--data-binary','@patch.json',url+'/products/7'],['--request','DELETE',url+'/products/7'],['--get',url+'/products','--data-urlencode','q=tea & coffee','--data-urlencode','limit=10'],['-F','file=@report.pdf','-F','category=monthly',url+'/uploads']]
try:
 for args in curl_cases:subprocess.run(['curl.exe','--silent','--show-error',*args],cwd=BASE,capture_output=True,check=True)
 assert seen[0]['method']=='POST' and json.loads(seen[0]['body'])['sku']=='BOOK-7'
 assert [x['method'] for x in seen[2:5]]==['PUT','PATCH','DELETE']
 assert 'q=tea' in seen[5]['path'] and '%26' in seen[5]['path']
 assert 'multipart/form-data; boundary=' in seen[6]['type'] and 'monthly' in seen[6]['body']
 r=subprocess.run(['curl.exe','--silent','--show-error','--fail-with-body',url+'/error'],capture_output=True,text=True)
 assert r.returncode==22 and json.loads(r.stdout)['path']=='/error'
finally:server.shutdown();server.server_close()
# Read-only public samples; do not send real keys or perform public writes.
public=[]
for u in ['https://jsonplaceholder.typicode.com/posts/1','https://jsonplaceholder.typicode.com/users','https://dummyjson.com/products?limit=2&skip=0','https://httpbin.org/get','https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current=temperature_2m']:
 try:
  with urllib.request.urlopen(u,timeout=20) as response:
   obj=json.load(response);public.append({'url':u,'status':response.status,'json_type':type(obj).__name__})
 except Exception as e:public.append({'url':u,'error':str(e)})
report={'jq_version':subprocess.check_output([str(jq),'--version'],text=True).strip(),'jq_cases_passed':len(cases),'curl_local_cases_passed':len(curl_cases)+1,'public_reads':public,'limits':'Configuration snippets and product migration workflows were documented, not fully installed or exercised. Hosted LLM calls were not made.'}
(R/'checks.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
