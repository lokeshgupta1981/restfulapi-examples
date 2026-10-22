"""Local, disposable example checks. No provider API calls or browser automation."""
from pathlib import Path
from contextlib import contextmanager
import os, sys, subprocess, time, urllib.request, socket, json, traceback

ROOT=Path('C:\\Users\\lokes\\OneDrive\\Documents\\ChatGPT\\restfulapi\\ai-drafts-review')
PY=str(ROOT.parent/'.venv-drafts-review/Scripts/python.exe')
SOURCE=Path('C:\\Users\\lokes\\IdeaProjects\\restfulapi-examples'); LOGS=ROOT/'checks'; LOGS.mkdir(exist_ok=True)
LINKS=json.loads((ROOT/'example-links.json').read_text())
REPORT=json.loads((LOGS/'verification.json').read_text()) if (LOGS/'verification.json').exists() else {}
ENV=os.environ.copy()
for name in list(ENV):
    if name.startswith(('OPENAI_','ANTHROPIC_','GEMINI_','GOOGLE_API','LLM_')): ENV.pop(name)
ENV.update(PYTHONIOENCODING='utf-8',PYTHONUTF8='1',PYTHON=PY,OPENAI_API_KEY='demo-key',
           OPENAI_BASE_URL='http://127.0.0.1:8000/v1',MODEL='echo-1',NO_PROXY='127.0.0.1,localhost')
ENV['PATH']=str(Path(PY).parent)+os.pathsep+ENV.get('PATH','')
NOWINDOW=getattr(subprocess,'CREATE_NO_WINDOW',0)

def run(folder,args,label,env=None,input=None,expected=0,timeout=90):
    command=[PY,*args] if args[0].endswith('.py') or args[0]=='-m' else args
    result=subprocess.run(command,cwd=folder,env=ENV|(env or {}),input=input,
                          capture_output=True,text=True,timeout=timeout,creationflags=NOWINDOW)
    (LOGS/(label+'.txt')).write_text(result.stdout+'\nSTDERR\n'+result.stderr,encoding='utf-8')
    if result.returncode!=expected:
        raise RuntimeError(f'{label}: exit {result.returncode}; see log')
    return result.stdout

@contextmanager
def server(folder,module,port,path='/docs',env=None,direct=False):
    for attempt in range(20):
        with socket.socket() as probe: busy=probe.connect_ex(('127.0.0.1',port))==0
        if not busy: break
        time.sleep(.2)
    if busy: raise RuntimeError(f'Port {port} already in use')
    logfile=(LOGS/(folder.name+'-'+str(port)+'.server.log')).open('w',encoding='utf-8')
    args=[PY,module] if direct else [PY,'-m','uvicorn',module,'--host','127.0.0.1','--port',str(port),'--log-level','warning']
    process=subprocess.Popen(args,cwd=folder,env=ENV|(env or {}),stdout=logfile,stderr=subprocess.STDOUT,creationflags=NOWINDOW)
    try:
        deadline=time.monotonic()+30
        while True:
            if process.poll() is not None: raise RuntimeError(f'Server exited: {folder.name}')
            try:
                urllib.request.urlopen(f'http://127.0.0.1:{port}{path}',timeout=1).close(); break
            except urllib.error.HTTPError:
                break  # A protected or disabled docs route still proves this server is accepting HTTP.
            except Exception:
                if time.monotonic()>deadline: raise RuntimeError(f'Server did not become ready: {folder.name}')
                time.sleep(.15)
        yield
    finally:
        process.terminate()
        try: process.wait(timeout=8)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        logfile.close()

def check(post):
    folder=SOURCE/LINKS[post][0].split('/')[-1]
    if post=='3010':
        run(folder,['client.py','stdio'],post+'-stdio')
        with server(folder,'http_server:app',8000):
            run(folder,['client.py','http'],post+'-http')
            run(folder,['client.py','http-errors'],post+'-http-errors')
    elif post=='3020': run(folder,['demo.py'],post+'-demo')
    elif post=='3051': run(folder,['client.py'],post+'-demo')
    elif post=='3059':
        run(folder,['mini_editor.py','--yes','add timeouts to weather.py'],post+'-allow')
        run(folder,['mini_editor.py','add timeouts to weather.py'],post+'-reject',input='reject\n')
    elif post=='3060':
        with server(folder,'server:app',8000): run(folder,['client.py'],post+'-demo')
    elif post=='3062':
        with server(folder,'stub_server:app',8000):
            run(folder,['chat_demo.py'],post+'-chat',env={'MODEL':'gpt-6-astra'})
            run(folder,['responses_demo.py'],post+'-responses',env={'MODEL':'gpt-6-astra'})
    elif post=='3063':
        run(folder,['generate.py'],post+'-generate')
        with server(folder,'serve.py',8000,path='/docs/llms.txt',direct=True):
            run(folder,['validate.py','http://127.0.0.1:8000/docs/llms.txt'],post+'-validate')
    elif post=='3045': run(folder,['measure.py'],post+'-measure')
    elif post=='3066':
        with server(folder,'expense_agent:app',9999,path='/.well-known/agent-card.json'):
            run(folder,['client.py'],post+'-http')
            run(folder,['sdk_client.py'],post+'-sdk')
    elif post=='2780':
        with server(folder,'auth_server.py',9420,path='/.well-known/oauth-authorization-server',direct=True):
            with server(folder,'mcp_server.py',9410,path='/.well-known/oauth-protected-resource/mcp',direct=True):
                run(folder,['client.py'],post+'-oauth')
    elif post=='2770':
        with server(folder,'helpdesk_api:app',8080,env={'HELPDESK_API_TOKEN':'dev-token-123'}):
            run(folder,['compare_tools.py'],post+'-catalogs',env={'HELPDESK_API_TOKEN':'dev-token-123'})
            run(folder,['call_tools.py'],post+'-calls',env={'HELPDESK_API_TOKEN':'dev-token-123'})
    elif post=='3046':
        with server(folder,'server:app',8000):
            run(folder,['switch_demo.py'],post+'-switch')
            run(folder,['check_compat.py'],post+'-strict',env={'BURST_KEY':'burst-key'})
        with server(folder,'server:app',8001,env={'LENIENT':'1'}):
            run(folder,['check_compat.py'],post+'-lenient',env={'OPENAI_BASE_URL':'http://127.0.0.1:8001/v1','BURST_KEY':'burst-key'})
    elif post=='3041':
        with server(folder,'backends:app',9001):
            with server(folder,'gateway:app',8000):
                run(folder,['demo.py','chat','vk-support-123','fast','Customer says the invoice total is wrong.'],post+'-model')
                flag=folder/'alpha_down.flag'; flag.write_text('')
                try: run(folder,['demo.py','chat','vk-support-123','fast','Refund request for order 1042.'],post+'-fallback')
                finally: flag.unlink(missing_ok=True)
                run(folder,['demo.py','tools','mcp-support-token'],post+'-tools')
                run(folder,['demo.py','call','mcp-support-token','crm__search_customers','{"query":"Ana"}'],post+'-allowed')
                run(folder,['demo.py','call','mcp-support-token','crm__delete_customer','{"id":"c-7"}'],post+'-denied')
    elif post=='3064':
        token=run(folder,['tokens.py','--sub','alice','--scope','cart:write'],post+'-mint').strip()
        other=run(folder,['tokens.py','--sub','alice','--scope','cart:write','--aud','https://api.example.com'],post+'-mint-wrong-aud').strip()
        with server(folder,'server:app',8000):
            run(folder,['client_guard.py','pin','--token',token],post+'-pin')
            run(folder,['client_guard.py','check','--token',token],post+'-check')
            run(folder,['client_guard.py','call','create_cart','--token',other],post+'-wrong-aud')
            run(folder,['client_guard.py','call','create_cart','--token',token,'--origin','http://evil.example'],post+'-origin')
        with server(folder,'server:app',8000,env={'RUG_PULL':'1'}):
            run(folder,['client_guard.py','check','--token',token],post+'-changed',expected=1)
    elif post=='3076':
        for scenario in ('good','missing-command','missing-key','missing-key-fixed','stdout-text','slow'):
            limit='10000' if scenario in ('good','missing-key-fixed') else '4000'
            output=run(folder/'client',['node','check.mjs',scenario],post+'-'+scenario,env={'TIMEOUT_MS':limit},timeout=30)
            if scenario in ('good','missing-key-fixed'):
                assert 'result:' in output,output
            else: assert '['+scenario+']' in output,output
    elif post=='3038':
        # HTTP contract check here; UI checked with the approved browser tool separately.
        with server(folder,'server:app',8000,path='/host'):
            assert b'iframe' in urllib.request.urlopen('http://127.0.0.1:8000/host').read()
    else: raise ValueError(post)

order=['3051','3020','3063','3010','3060','3062','3046','3041','3064','3066','3059','3045','2780','2770','3076','3038']
if len(sys.argv)>1: order=sys.argv[1:]
for post in order:
    started=time.monotonic()
    try:
        check(post); REPORT[post]={'status':'passed','seconds':round(time.monotonic()-started,2)}
    except Exception as error:
        REPORT[post]={'status':'failed','error':str(error),'seconds':round(time.monotonic()-started,2)}
        (LOGS/(post+'-failure.txt')).write_text(traceback.format_exc(),encoding='utf-8')
    print(post,REPORT[post],flush=True)
    (LOGS/'verification.json').write_text(json.dumps(REPORT,indent=2),encoding='utf-8')
