from pathlib import Path
import subprocess,os,time,urllib.request,json
repo=Path(r'C:\Users\lokes\IdeaProjects\restfulapi-examples')
project=repo/'free-llm-api-example'
py=Path(r'C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\.venv-drafts-review\Scripts\python.exe')
env=os.environ.copy()
for k in ('GEMINI_API_KEY','GROQ_API_KEY','OPENROUTER_API_KEY','OLLAMA_API_KEY','OPENAI_API_KEY'):env.pop(k,None)
env.update(GROQ_API_KEY='test-key',GROQ_BASE_URL='http://127.0.0.1:8101/v1',OPENROUTER_API_KEY='test-key',OPENROUTER_BASE_URL='http://127.0.0.1:8102/v1')
servers=[]
try:
 for app,port in [('busy',8101),('flaky',8102)]:
  servers.append(subprocess.Popen([str(py),'-m','uvicorn','mock_provider:'+app,'--host','127.0.0.1','--port',str(port)],cwd=project,env=env,stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=subprocess.CREATE_NO_WINDOW))
 for port in (8101,8102):
  for _ in range(60):
   try:
    urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/openapi.json',timeout=1).close();break
   except Exception:time.sleep(.1)
 run=subprocess.run([str(py),'free_llm.py'],cwd=project,env=env,capture_output=True,text=True,timeout=30)
 assert run.returncode==0,(run.stdout,run.stderr)
 assert 'retry-after 3600' in run.stdout and 'HTTP 200 on attempt 2' in run.stdout,run.stdout
 out=Path(r'C:\Users\lokes\OneDrive\Documents\ChatGPT\restfulapi\resources-drafts')
 (out/'llm-mock-check.txt').write_text(run.stdout,encoding='utf-8')
 print(run.stdout)
finally:
 for s in servers:s.terminate();s.communicate(timeout=5)
