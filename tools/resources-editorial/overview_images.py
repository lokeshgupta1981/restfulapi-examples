from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import json,textwrap,re
R=Path(r'C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\resources-drafts')
OUT=R/'images';OUT.mkdir(exist_ok=True)
FONT=Path('C:/Windows/Fonts/segoeui.ttf');BOLD=Path('C:/Windows/Fonts/segoeuib.ttf')
DATA={
'3075':('Choose a free LLM API','free-llm-api-choose-by-workload',[
('Gemini API','Prototype with an eligible Gemini model','Model allowance and data-use terms'),('Groq','Try hosted open-model inference','Account quota and retention controls'),('OpenRouter','Compare models through one API','Free-model availability and host policies'),('Workers AI','Keep inference near a Workers app','Neuron budget and model eligibility'),('Local model','Keep inference on your own hardware','Local-only setup, license and memory'),('Evaluation access','Run a limited provider experiment','Expiry, card requirement and permitted use')]),
'3056':('Choose a Postman alternative','postman-alternatives-choose-by-workflow',[
('Bruno','Review collections with application code','Import fidelity and CLI coverage'),('Hoppscotch','Use web, desktop or self-hosted access','Network path, CORS and operations'),('Insomnia','Choose local, Git or cloud project storage','Storage mode and migration behavior'),('Yaak','Use a local desktop workspace with Git','Required protocols, imports and plugins'),('curl / HTTPie','Reproduce small calls in terminal scripts','Assertions, secrets and maintainability')]),
'2990':('Choose an API for practice','fake-rest-api-choose-by-test',[
('JSONPlaceholder','Learn basic reads and client parsing','Fake writes are not durable storage'),('DummyJSON','Practice catalog search and pagination','Product changes are simulated'),('httpbin','Inspect the request your client sent','Synthetic data only; not business tests'),('ReqRes','Practice project data, keys and sessions','Account setup, permissions and quota'),('Open-Meteo','Build a read-only weather project','Changing data, usage and license terms')]),
'3069':('Choose a jq filter','jq-choose-filter-by-task',[
('Read a field','.data[0].name','Check whether the root is an object or array'),('Filter an array','.data[] | select(.active == true)','Use [ ... ] to collect results into an array'),('Reshape output','map({id, name})','Start from the array you want to transform'),('Supply a default','.team.name // "Unassigned"','The fallback replaces null and false'),('Export CSV','[.id, .name] | @csv','Each row must be an array; use -r'),('Use a variable','--arg wanted Ada','Pass data as arguments, not filter source')]),
'3035':('Choose a curl request pattern','curl-choose-request-pattern',[
('Read a resource','curl URL','Use --get with encoded query parameters'),('Send JSON','curl --json @order.json URL','The option does not validate JSON syntax'),('Replace or patch','--request PUT or PATCH','Send the format the endpoint accepts'),('Authenticate','--user or an auth header','Follow the API contract and protect secrets'),('Upload a file','-F "file=@report.pdf"','Let curl generate multipart boundaries'),('Inspect a failure','--dump-header and --write-out','Check HTTP status and curl exit code')]),
'3047':('Choose an API media type','mime-types-choose-content-type',[
('JSON object or array','application/json','One JSON value; use UTF-8'),('Text or CSV','text/plain or text/csv','Document charset and field conventions'),('Known binary file','Use its specific registered type','octet-stream is a generic fallback'),('Simple form fields','application/x-www-form-urlencoded','Name/value pairs; not a file container'),('Fields and files','multipart/form-data','The boundary must match the body'),('Streaming records','Use the documented stream type','NDJSON, JSON-seq and SSE differ')])}
manifest=[]
for id,(title,slug,rows) in DATA.items():
 w=1700; margin=50; top=160; rh=76; height=1100
 im=Image.new('RGB',(w,height),'#f4f7fb');d=ImageDraw.Draw(im)
 titlefont=ImageFont.truetype(str(BOLD),46);font=ImageFont.truetype(str(FONT),29);bold=ImageFont.truetype(str(BOLD),29);small=ImageFont.truetype(str(FONT),23)
 d.text((margin,26),title,fill='#18334f',font=titlefont)
 d.text((margin,94),'Start with your task. Check the constraint before choosing.',fill='#4d6075',font=font)
 widths=[320,624,628];xs=[margin,margin+320,margin+944]
 d.rounded_rectangle((margin,top,w-margin,top+66),radius=12,fill='#183b60')
 labels=['Option / task','Choose or use this','Check first']
 for x,label in zip(xs,labels):d.text((x+20,top+17),label,fill='white',font=bold)
 def lines(text,maxw,f):
  result=[];line=''
  for word in text.split():
   candidate=(line+' '+word).strip()
   if d.textlength(candidate,font=f)>maxw and line:result.append(line);line=word
   else:line=candidate
  if line:result.append(line)
  return result
 y=top+66
 for i,row in enumerate(rows):
  max_lines=max(len(lines(text,widths[col]-42,bold if col==0 else font)) for col,text in enumerate(row))
  rh=30+38*max_lines
  d.rectangle((margin,y,w-margin,y+rh),fill='white' if i%2==0 else '#eaf0f7')
  for col,(x,text) in enumerate(zip(xs,row)):
   f=bold if col==0 else font
   ll=lines(text,widths[col]-42,f)
   assert len(ll)<=3,(id,text,ll)
   for j,line in enumerate(ll):d.text((x+20,y+13+j*38),line,fill='#19344d' if col<2 else '#465d72',font=f)
  d.line((margin,y+rh,w-margin,y+rh),fill='#d8e2ee',width=2)
  y+=rh
 height=y+58
 im=im.crop((0,0,w,height));d=ImageDraw.Draw(im)
 d.text((margin,height-43),'RESTfulAPI.net',fill='#536b82',font=small)
 slug=slug+'-compact';path=OUT/(slug+'.png');im.save(path,optimize=True)
 manifest.append({'id':id,'title':title,'slug':slug,'file':str(path),'rows':rows,'alt':title+'. '+'. '.join(': '.join(row) for row in rows)})
(R/'overview-images.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print('Created',len(manifest),'decision overview images without post numbers')
