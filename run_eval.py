"""Eval runner for the prospect scorer. Usage: python run_eval.py --model M --prompt your_prompt.txt --runs 3 --tag NAME"""
import json, os, sys, time, argparse, urllib.request, concurrent.futures as cf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cases import C
# The prompt returns a profile code; map your prompt's codes to these profile names.
PERSONA={"medical":"Medical professionals","lawyers":"Lawyers","founders":"Founders","academics":"Academics","diaspora_finance":"Diaspora finance","allocators":"Allocators / other"}
BAND={"hot":(7,10),"warm":(4,6),"cold":(0,3)}
def key():
    for line in open(os.environ.get("EVAL_ENV",os.path.join(os.path.dirname(os.path.abspath(__file__)),".env"))):
        if line.startswith("ANTHROPIC_API_KEY="): return line.split("=",1)[1].strip()
def user_msg(c):
    _,f,l,title,org,loc,head,about,ind=c[:9]; name=(f+" "+l).strip()
    return (f"Name: {name or 'Unknown'}\nTitle: {title or 'Unknown'}\nOrganisation: {org or 'Unknown'}\nLocation: {loc or 'Unknown'}\n"
            f"Industry: {ind or 'Not provided'}\nCompany Size: Not provided\nCompany Revenue: Not provided\n"
            f"LinkedIn Headline: {head or 'Not provided'}\nBio/Summary: {about or 'Not provided'}\nConnections: Not provided")
def call(model, system, user, k, tries=4):
    body=json.dumps({"model":model,"max_tokens":1200,"system":system,"messages":[{"role":"user","content":user}]}).encode()
    for t in range(tries):
        try:
            req=urllib.request.Request("https://api.anthropic.com/v1/messages",data=body,headers={"x-api-key":k,"anthropic-version":"2023-06-01","content-type":"application/json"})
            d=json.load(urllib.request.urlopen(req,timeout=120))
            return "".join(b.get("text","") for b in d["content"]), d.get("usage",{})
        except Exception as e:
            if t==tries-1: return f"__ERROR__ {e}", {}
            time.sleep(5*(t+1))
def parse(txt):
    try: return json.loads(txt.replace("```json","").replace("```","").strip())
    except Exception: return None
def apply_cap(out):
    """Code-side rule: no quoted evidence of personal capital means the verdict cannot be hot."""
    if out and out.get("verdict")=="hot" and not str(out.get("capital_evidence","")).strip():
        out=dict(out); out["verdict"]="warm"; out["overall"]=min(out.get("overall",6),6); out["capped"]=True
    return out
def grade(c, out):
    exp_v, exp_p = c[9], c[10]
    if out is None: return {"valid":False,"verdict_ok":False,"band_ok":False,"profile_ok":False,"got_verdict":None,"got_score":None,"got_profile":None}
    insufficient = out.get("data_quality")=="insufficient" or out.get("verdict")=="uncontactable"
    gv = "uncontactable" if insufficient else out.get("verdict")
    sc = out.get("overall"); gp = PERSONA.get(out.get("persona"), out.get("persona"))
    band_ok = (exp_v=="uncontactable" and insufficient) or (exp_v in BAND and isinstance(sc,(int,float)) and BAND[exp_v][0]<=sc<=BAND[exp_v][1] and not insufficient)
    return {"valid":True,"verdict_ok":gv==exp_v,"band_ok":band_ok,"profile_ok": True if exp_v=="uncontactable" else gp==exp_p,
            "got_verdict":gv,"got_score":sc,"got_profile":gp}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--model",required=True); ap.add_argument("--prompt",required=True)
    ap.add_argument("--runs",type=int,default=3); ap.add_argument("--tag",required=True); ap.add_argument("--workers",type=int,default=6); ap.add_argument("--capcode",action="store_true")
    a=ap.parse_args(); system=open(a.prompt).read(); k=key()
    jobs=[(c,r) for c in C for r in range(a.runs)]
    def one(j):
        c,r=j; txt,usage=call(a.model,system,user_msg(c),k); out=parse(txt)
        if a.capcode: out=apply_cap(out)
        return {"id":c[0],"run":r,"expected_verdict":c[9],"expected_profile":c[10],"tests":c[11],"raw":txt,"usage":usage,"capped":bool(out and out.get("capped")),**grade(c,out)}
    t0=time.time()
    with cf.ThreadPoolExecutor(a.workers) as ex: res=list(ex.map(one,jobs))
    os.makedirs("results",exist_ok=True)
    json.dump({"model":a.model,"prompt":a.prompt,"runs":a.runs,"seconds":round(time.time()-t0),"results":res},open(f"results/{a.tag}.json","w"),indent=1)
    print(summary(res))
def summary(res):
    n=len(res); f=lambda k: sum(r[k] for r in res)/n
    by={}
    for r in res: by.setdefault(r["id"],[]).append(r)
    consistent=sum(len({x["got_verdict"] for x in v})==1 for v in by.values())/len(by)
    tin=sum(r["usage"].get("input_tokens",0) for r in res); tout=sum(r["usage"].get("output_tokens",0) for r in res)
    return json.dumps({"calls":n,"valid_json":round(f("valid"),3),"verdict_acc":round(f("verdict_ok"),3),"score_in_band":round(f("band_ok"),3),
        "profile_acc":round(f("profile_ok"),3),"consistent_cases":round(consistent,3),"input_tokens":tin,"output_tokens":tout})
if __name__=="__main__": main()
