from pathlib import Path
from bs4 import BeautifulSoup
import json,re,html
R=Path(r'C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\resources-drafts')
assets=json.loads((R/'overview-images.json').read_text(encoding='utf-8'))
backup=R/'before-overview';backup.mkdir(exist_ok=True)
heading={'3075':'Which Free LLM API Should You Choose?','3056':'Which Postman Alternative Should You Choose?','2990':'Which Practice API Should You Choose?','3069':'Which jq Filter Fits Your Task?','3035':'Which curl Pattern Fits Your Request?','3047':'Which Content-Type Fits Your Body?'}
lead={'3075':'Choose by the workload and permitted data use first. The overview separates a renewing allowance from an evaluation offer and local inference; the sections below explain limits, compatibility and fallback.','3056':'Choose by how the team stores, reviews and runs requests. The overview gives a starting choice for each workflow; the later sections explain the trade-offs and migration checks.','2990':'Choose the behavior you need to practice: reading fixtures, inspecting requests, using authentication or working with persistent state. The sections below explain what each service can prove.','3069':'Start with the result you need from the response. This overview maps common tasks to a filter pattern; the worked examples below use one shared JSON fixture.','3035':'Start with the operation you need to perform. This overview maps common API tasks to curl options; the sections below show complete commands and explain the important limits.','3047':'Choose from the actual body format, then check its framing and encoding. This overview groups the main choices; the detailed sections below list specific media types and examples.'}
for a in assets:
 id=a['id'];f=R/'articles'/f'{id}.wp.html';old=backup/f.name
 if not old.exists():old.write_bytes(f.read_bytes())
 raw=old.read_text(encoding='utf-8')
 if id in ('3075','3056','2990'):
  raw=re.sub(r'<!-- wp:table[^>]*-->\s*<figure.*?</figure>\s*<!-- /wp:table -->','',raw,count=1,flags=re.S)
 if id=='3075':
  raw=re.sub(r'<!-- wp:table[^>]*-->\s*<figure(?:(?!<!-- /wp:table -->).)*?<th>Need</th>.*?</figure>\s*<!-- /wp:table -->','',raw,count=1,flags=re.S)
  raw=re.sub(r'<!-- wp:image[^>]*-->\s*<figure(?:(?!<!-- /wp:image -->).)*?which-free-llm-api-to-use.png.*?</figure>\s*<!-- /wp:image -->','',raw,count=1,flags=re.S)
  raw=raw.replace('As checked on October 22, 2026, the free options fall into three groups.','The options below separate renewing allowances, evaluation access and local inference. Provider details were checked on October 22, 2026.')
 # Keep anchor IDs stable while updating displayed section numbers.
 raw=re.sub(r'(<h[23][^>]*>)(\d+)(\.\d+)?([. ])',lambda m:m[1]+str(int(m[2])+1)+(m[3] or '')+m[4],raw)
 raw=re.sub(r'>([Ss]ection) (\d+)(\.\d+)?<',lambda m:'>'+m[1]+' '+str(int(m[2])+1)+(m[3] or '')+'<',raw)
 overview='<!-- wp:heading -->\n<h2 class="wp-block-heading">1. '+heading[id]+'</h2>\n<!-- /wp:heading -->\n\n<!-- wp:paragraph -->\n<p>'+lead[id]+'</p>\n<!-- /wp:paragraph -->\n\n<!-- wp:image '+json.dumps({'id':int(a['mediaId']),'sizeSlug':'full','linkDestination':'none'})+' -->\n<figure class="wp-block-image size-full"><img src="'+a['url']+'" alt="'+html.escape(a['alt'],quote=True)+'" class="wp-image-'+a['mediaId']+'"/></figure>\n<!-- /wp:image -->'
 # Two short intro paragraphs precede the overview; the rest expands its choices.
 paras=list(re.finditer(r'<!-- wp:paragraph -->.*?<!-- /wp:paragraph -->',raw,flags=re.S))
 assert len(paras)>=2
 at=paras[1].end();raw=raw[:at]+'\n\n'+overview+raw[at:]
 doc=BeautifulSoup(raw,'html.parser');first=doc.find('h2');n=first.find_next('h2')
 contents=[]
 for sibling in first.next_siblings:
  if getattr(sibling,'name',None)=='h2':break
  contents.append(str(sibling))
 chunk=BeautifulSoup(''.join(contents),'html.parser')
 assert chunk.select('img') and not chunk.select('table'),id
 assert 'PLANNING NOTE' not in doc.get_text() and not doc.select('.toc')
 f.write_text(raw,encoding='utf-8')
 print(id,first.get_text(),len(doc.select('img')),'images')
