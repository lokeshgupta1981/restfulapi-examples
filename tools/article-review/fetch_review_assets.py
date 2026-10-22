from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
import json, requests, zipfile, io
from bs4 import BeautifulSoup

root=Path('C:\\Users\\lokes\\OneDrive\\Documents\\ChatGPT\\restfulapi\\ai-drafts-review')
images=root/'images'; images.mkdir(exist_ok=True)
urls=set()
for p in (root/'originals').glob('*.html'):
    urls.update(i['src'] for i in BeautifulSoup(p.read_text(encoding='utf-8'),'html.parser').select('img[src]'))
def fetch(url):
    p=images/Path(urlsplit(url).path).name
    if not p.exists():
        r=requests.get(url,timeout=45); r.raise_for_status(); p.write_bytes(r.content)
    return {'url':url,'file':p.name,'bytes':p.stat().st_size}
with ThreadPoolExecutor(max_workers=2) as pool:
    result=list(pool.map(fetch,sorted(urls)))
(root/'asset-manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('Downloaded',len(result),'article images')
target=Path('C:\\Users\\lokes\\IdeaProjects\\restfulapi-examples')
if not target.exists():
    r=requests.get('https://codeload.github.com/lokeshgupta1981/restfulapi-examples/zip/refs/heads/main',timeout=90)
    r.raise_for_status()
    target.mkdir()
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        for item in z.infolist():
            relative=Path(*Path(item.filename).parts[1:])
            out=(target/relative).resolve()
            if not out.is_relative_to(target.resolve()): raise ValueError('Archive path outside source directory')
            if item.is_dir(): out.mkdir(parents=True,exist_ok=True)
            else:
                out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(z.read(item))
    print('Downloaded example repository snapshot')
