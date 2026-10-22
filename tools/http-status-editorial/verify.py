from pathlib import Path
from bs4 import BeautifulSoup
import subprocess,http.client,time,json
R=Path(r'C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\http-status-style')
s=BeautifulSoup((R/'articles/3004.wp.html').read_text(encoding='utf-8'),'html.parser')
node=s.select('pre code.language-javascript')[0].get_text()
Path('header-server.mjs').write_text(node,encoding='utf-8')
p=subprocess.Popen(['node','header-server.mjs'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW)
try:
 for _ in range(40):
  try:
   conn=http.client.HTTPConnection('127.0.0.1',3000,timeout=2);conn.request('GET','/');conn.getresponse().read();conn.close();break
  except OSError:time.sleep(.1)
 result=[]
 for size in (100,20000):
  conn=http.client.HTTPConnection('127.0.0.1',3000,timeout=3);conn.request('GET','/',headers={'X-Demo':'x'*size});resp=conn.getresponse();result.append([size,resp.status]);resp.read();conn.close()
 assert result==[[100,200],[20000,431]],result
 checks={'header_size_test':result,'notes':'Node header example tested; nginx, Express and Spring configuration fragments checked against docs, not executed.'}
 for f in (R/'articles').glob('*.html'):
  doc=BeautifulSoup(f.read_text(encoding='utf-8'),'html.parser')
  assert 'PLANNING NOTE' not in doc.get_text() and not doc.select('.toc')
  for code in doc.select('pre code'):
   text=code.get_text()
   if text.startswith('HTTP/1.1') and '\n\n' in text:
    body=text.split('\n\n',1)[1]
    if body.startswith('{'):json.loads(body)
 (R/'checks.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
 print(json.dumps(checks))
finally:p.terminate();p.communicate(timeout=5)
