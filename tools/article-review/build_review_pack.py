from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from markdownify import markdownify
import re,json,html,zipfile

ROOT=Path('C:\\Users\\lokes\\OneDrive\\Documents\\ChatGPT\\restfulapi\\ai-drafts-review')
PACK=ROOT/'review-pack'
for name in ('articles','markdown','wordpress-ready','images'):(PACK/name).mkdir(parents=True,exist_ok=True)
inventory=json.loads((ROOT/'manifest.json').read_text())
metadata={
 '3076':('Diagnose startup, process, timeout and HTTP failures in an MCP connection.','Troubleshooting','Find the failing layer; reproduce the exact command; verify a fix with Inspector.'),
 '3063':('Publish and validate a useful Markdown index for API documentation.','Documentation','Choose the documentation links; generate the index; validate the published files.'),
 '3010':('Choose an MCP transport and understand the 2026 stateless request model.','Protocol','Choose a transport; compare message framing; plan safe migration and retries.'),
 '2770':('Convert an OpenAPI document into a reviewed, task-focused MCP tool catalog.','Implementation','Generate tools; remove risky operations; test schemas, pagination and approval.'),
 '3041':('Decide where model and tool gateway controls belong in an agent platform.','Comparison','Distinguish the traffic; choose gateway roles; trace identity and token budgets.'),
 '3045':('Choose CLI or MCP access by execution environment, permissions and task cost.','Comparison','Compare equivalent outputs; measure context cost; constrain either interface.'),
 '3064':('Protect MCP trust boundaries, credentials, state handles and sensitive actions.','Security','Identify attack paths; enforce server checks; review tool changes and approval.'),
 '3059':('Understand the editor-to-agent contract and run an ACP v1 example.','Protocol','Follow initialization and updates; negotiate capabilities; verify file permission flows.'),
 '3038':('Follow an interactive MCP view from a tool result to a sandboxed host UI.','Implementation','Connect a UI resource; understand visibility; validate bridge and permission boundaries.'),
 '2780':('Build and test a remote MCP resource server protected by OAuth tokens.','Security','Discover metadata; validate audience and scopes; distinguish scope consent from action approval.'),
 '3062':('Choose or migrate between Responses and Chat Completions request models.','Comparison','Select a state policy; map tools and output items; verify migration behavior.'),
 '3060':('Track long MCP operations with task handles, polling and cooperative cancellation.','Protocol','Handle task result shapes; answer input requests; plan durable storage and recovery.'),
 '3066':('Connect independent agents through A2A discovery, tasks and artifacts.','Protocol','Read an Agent Card; follow task states; secure results and callbacks.'),
 '3051':('Choose tools, resources or prompts by the intended interaction and output.','Protocol','Choose a primitive; test each catalog; follow resource links and elicitation.'),
 '3020':('Combine reusable skill instructions with authorized MCP tools and live data.','Comparison','Distinguish packaging from execution; load skills safely; enforce workflow permissions.'),
 '3046':('Evaluate the API subset an OpenAI-compatible endpoint actually implements.','Compatibility','Switch endpoint configuration; test required features; check errors and stream completion.')
}

CSS='''*{box-sizing:border-box}html{scroll-behavior:smooth}body{margin:0;background:#f6f7f9;color:#1c2635;font:18px/1.7 system-ui,Arial,sans-serif}a{color:#175b9c;text-underline-offset:3px}header,main,footer{max-width:1160px;margin:auto;padding:28px}header{border-bottom:1px solid #d9e1eb}h1{font-size:2.25rem;line-height:1.2;letter-spacing:-.025em}h2{font-size:1.65rem;line-height:1.3;margin-top:2em}h3{font-size:1.25rem;line-height:1.4;margin-top:1.7em}.article{max-width:850px;background:white;border:1px solid #e2e7ed;border-radius:12px;padding:38px;margin:28px auto}.reviewbar{font-size:14px;color:#536379}p{margin:1em 0}figure{margin:28px 0}img{max-width:100%;height:auto!important;width:100%!important;display:block}figcaption{font-size:.88rem;color:#536379;text-align:center;margin-top:10px}pre{padding:20px;overflow:auto;max-height:650px;background:#15202f;color:#ecf1f8;border-radius:8px;font-size:14px;line-height:1.55;white-space:pre}code{font-family:Consolas,monospace}table{border-collapse:collapse;min-width:100%;font-size:16px}th,td{border:1px solid #d4dce7;padding:10px 12px;text-align:left;vertical-align:top}th{background:#eef3f9}figure.wp-block-table{overflow-x:auto}ul,ol{padding-left:1.5em}blockquote{border-left:4px solid #1764aa;padding-left:20px;margin-left:0}.cards{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}.card{background:white;border:1px solid #dce3ec;border-radius:10px;padding:22px}.card h2{font-size:1.25rem;margin:10px 0}.card p{font-size:16px}.tag{font-size:12px;letter-spacing:.04em;text-transform:uppercase;color:#536379}.toc{border-left:3px solid #dce6f3;padding-left:20px;font-size:15px}.toc li{margin:5px 0}.search{width:100%;padding:14px;border:1px solid #b8c7da;border-radius:6px;font:inherit;margin-bottom:24px}.links{font-size:14px;display:flex;gap:14px;flex-wrap:wrap}@media(max-width:740px){header,main,footer{padding:18px}.cards{grid-template-columns:1fr}.article{padding:20px;margin:0;border:0;border-radius:0}h1{font-size:1.8rem}body{font-size:17px}}@media print{.reviewbar,.toc,.links,footer{display:none}body{background:white}.article{border:0;margin:0;padding:0;max-width:none}pre{white-space:pre-wrap;max-height:none;color:black;background:#f3f3f3}a{color:black}h2,h3,figure{break-inside:avoid}}'''
(PACK/'review.css').write_text(CSS,encoding='utf-8')

def slugify(title):
    return re.sub(r'[^a-z0-9]+','-',title.lower()).strip('-')

manifest=[]; cards=[]; briefs=[]
for item in inventory:
    post=item['id']; title=item['title']; description,kind,success=metadata[post]
    slug=slugify(title)
    raw=(ROOT/'articles'/(post+'.wp.html')).read_text(encoding='utf-8')
    soup=BeautifulSoup(raw,'html.parser')
    images=soup.select('img'); featured=images[0].get('src') if images else None
    for image in images:
        name=Path(urlsplit(image['src']).path).name
        data=(ROOT/'images'/name).read_bytes(); (PACK/'images'/name).write_bytes(data)
        image['src']='../images/'+name
        image.attrs.pop('srcset',None); image.attrs.pop('sizes',None)
        image['loading']='lazy'; image['decoding']='async'
    # Strip Gutenberg comments only in readable exports, retaining original ready-to-save payload separately.
    body=re.sub(r'<!--.*?-->','',str(soup),flags=re.S)
    page_soup=BeautifulSoup(body,'html.parser')
    headings=page_soup.select('h2,h3')
    toc=[]
    for n,h in enumerate(headings):
        if not h.get('id'):h['id']='section-'+str(n+1)
        if h.name=='h2':toc.append('<li><a href="#'+h['id']+'">'+html.escape(h.get_text())+'</a></li>')
    body=str(page_soup)
    words=len(page_soup.get_text(' ',strip=True).split())
    nav='<div class="reviewbar"><a href="../index.html">All AI articles</a> / Review copy</div>'
    toc_html='<nav class="toc" aria-label="Article sections"><ol>'+''.join(toc)+'</ol></nav>'
    page='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>'+html.escape(title)+'</title><link rel="stylesheet" href="../review.css"></head><body><main><div class="article">'+nav+'<h1>'+html.escape(title)+'</h1>'+toc_html+'<article>'+body+'</article></div></main></body></html>'
    (PACK/'articles'/(slug+'.html')).write_text(page,encoding='utf-8')
    (PACK/'markdown'/(slug+'.md')).write_text('# '+title+'\n\n'+markdownify(body,heading_style='ATX',strong_em_symbol='*'),encoding='utf-8')
    (PACK/'wordpress-ready'/(slug+'.wp.html')).write_text(raw,encoding='utf-8')
    links='<div class="links"><a href="articles/'+slug+'.html">Read article</a><a href="markdown/'+slug+'.md">Markdown</a><a href="wordpress-ready/'+slug+'.wp.html">WordPress source</a></div>'
    cards.append('<section class="card" data-search="'+html.escape((title+' '+kind).lower())+'"><span class="tag">'+kind+' / '+f'{words:,}'+' words / '+str(len(images))+' visuals</span><h2><a href="articles/'+slug+'.html">'+html.escape(title)+'</a></h2><p>'+description+'</p>'+links+'</section>')
    manifest.append({**item,'slug':slug,'words':words,'images':len(images),'featured_image_candidate':featured,'review_file':'articles/'+slug+'.html','status':'ready for editorial review'})
    briefs.append({'title':title,'intent':description,'article_type':kind,'outline':[h.get_text(' ',strip=True) for h in headings if h.name=='h2'],'success':success,'scope_note':'Focus on the named concept and its existing running example. Link to sibling articles for the wider REST API and MCP foundations.'})

intro='<header><div class="tag">REST API Tutorial / AI / Editorial review</div><h1>AI articles ready for review</h1><p>Sixteen complete articles with explanations, examples and diagrams. Prepared October 22, 2026. WordPress remains unchanged.</p><div class="links"><a href="review-notes.md">Review notes and verification limits</a><a href="article-manifest.json">Article manifest</a></div></header>'
script='''<script>document.querySelector('#filter').addEventListener('input',function(){const q=this.value.toLowerCase();document.querySelectorAll('.card').forEach(card=>card.hidden=!card.dataset.search.includes(q));});</script>'''
index='<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>AI Articles - Review Pack</title><link rel="stylesheet" href="review.css"></head><body>'+intro+'<main><label for="filter">Find an article</label><input class="search" id="filter" type="search" placeholder="Search by topic"><div class="cards">'+''.join(cards)+'</div></main><footer>Open an article to read it. Markdown and WordPress-ready files are included for editing and later import.</footer>'+script+'</body></html>'
(PACK/'index.html').write_text(index,encoding='utf-8')
(PACK/'article-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(ROOT/'reader-briefs.json').write_text(json.dumps(briefs,indent=2),encoding='utf-8')
(ROOT/'REVIEW.md').write_text('# AI draft articles for review\n\nPrepared October 22, 2026. All sixteen articles are local review copies. WordPress was not changed.\n\n'+ '\n'.join('- ['+x['title']+'](review-pack/'+x['review_file']+')' for x in manifest)+'\n',encoding='utf-8')
if (ROOT/'review-notes.md').exists(): (PACK/'review-notes.md').write_bytes((ROOT/'review-notes.md').read_bytes())
with zipfile.ZipFile(ROOT/'ai-articles-review.zip','w',zipfile.ZIP_DEFLATED) as z:
    for p in PACK.rglob('*'):
        if p.is_file():z.write(p,'ai-articles-review/'+p.relative_to(PACK).as_posix())
print('Built',len(manifest),'complete articles,',sum(x['words'] for x in manifest),'words,',sum(x['images'] for x in manifest),'images')
