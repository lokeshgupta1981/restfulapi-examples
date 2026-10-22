from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urldefrag
from bs4 import BeautifulSoup
import requests, json
root=Path('C:\\Users\\lokes\\OneDrive\\Documents\\ChatGPT\\restfulapi\\ai-drafts-review')
links={}
for p in (root/'articles').glob('*.wp.html'):
    for a in BeautifulSoup(p.read_text(encoding='utf-8'),'html.parser').select('a[href]'):
        url=urldefrag(a['href'])[0]
        if url.startswith('https://'): links.setdefault(url,[]).append(p.name)
def check(url):
    try:
        response=requests.get(url,timeout=25,headers={'User-Agent':'Mozilla/5.0'},allow_redirects=True)
        return {'url':url,'status':response.status_code,'final_url':response.url,'articles':links[url]}
    except Exception as e: return {'url':url,'error':type(e).__name__,'articles':links[url]}
with ThreadPoolExecutor(max_workers=2) as pool:
    results=list(pool.map(check,links))
(root/'link-check.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print('Checked',len(results),'URLs;',sum(r.get('status')==200 for r in results),'returned HTTP 200')
print(json.dumps([r for r in results if r.get('status')!=200],indent=2))
