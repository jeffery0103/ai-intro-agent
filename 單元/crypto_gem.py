import json, os, urllib.request, time, sys
def gemini(model, prompt, system=None, temperature=0.2):
    body={"contents":[{"role":"user","parts":[{"text":prompt}]}],"generationConfig":{"temperature":temperature}}
    if system: body["systemInstruction"]={"parts":[{"text":system}]}
    req=urllib.request.Request(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), headers={"Content-Type":"application/json","x-goog-api-key":os.environ["GEMINI_API_KEY"]})
    t=time.time()
    try: d=json.load(urllib.request.urlopen(req,timeout=90))
    except urllib.error.HTTPError as e: return {"error":e.code,"msg":e.read().decode()[:300],"sec":round(time.time()-t,1)}
    except Exception as e: return {"error":type(e).__name__,"msg":str(e)[:200],"sec":round(time.time()-t,1)}
    text="".join(p.get("text","") for p in d["candidates"][0]["content"]["parts"])
    u=d.get("usageMetadata",{})
    return {"text":text,"sec":round(time.time()-t,1),"in":u.get("promptTokenCount"),"out":u.get("candidatesTokenCount"),"think":u.get("thoughtsTokenCount"),"model":d.get("modelVersion")}
if __name__=="__main__":
    for m in sys.argv[1:]:
        print(m, gemini(m,"只回答一個數字:1+1=?"))
