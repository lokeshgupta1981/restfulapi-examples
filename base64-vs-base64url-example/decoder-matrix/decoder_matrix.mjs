// Which decoders accept which input? Run: node decoder_matrix.mjs (Node.js 25+ for fromBase64)
const cases={"std padded":"PDw/Pz8+Pg==","std no pad":"PDw/Pz8+Pg","url padded":"PDw_Pz8-Pg==","url no pad":"PDw_Pz8-Pg","bad char":"PDw*Pz8+Pg=="};
const fns={"Buffer base64":s=>Buffer.from(s,"base64").toString("latin1"),"Buffer base64url":s=>Buffer.from(s,"base64url").toString("latin1"),"atob":s=>atob(s)};
if (Uint8Array.fromBase64){fns["fromBase64"]=s=>new TextDecoder().decode(Uint8Array.fromBase64(s));fns["fromBase64 url"]=s=>new TextDecoder().decode(Uint8Array.fromBase64(s,{alphabet:"base64url"}));}
for (const [n,f] of Object.entries(fns)){const r=[];for(const [k,v] of Object.entries(cases)){try{r.push(`${k}=ok(${JSON.stringify(f(v))})`)}catch(e){r.push(`${k}=ERR`)}}console.log(n,"|",r.join(" "))}
