"""Which decoders accept which input? Run: python3 decoder_matrix.py"""
import base64
cases={"std padded":"PDw/Pz8+Pg==","std no pad":"PDw/Pz8+Pg","url padded":"PDw_Pz8-Pg==","url no pad":"PDw_Pz8-Pg","bad char":"PDw*Pz8+Pg=="}
for name,f in [("b64decode",base64.b64decode),("b64decode validate",lambda s:base64.b64decode(s,validate=True)),("urlsafe_b64decode",base64.urlsafe_b64decode)]:
    r=[]
    for k,v in cases.items():
        try: out=f(v); r.append(f"{k}=ok({out!r})")
        except Exception as e: r.append(f"{k}=ERR")
    print(name,"|"," ".join(r))
