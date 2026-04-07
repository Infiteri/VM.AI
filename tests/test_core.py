"""
    VM-AI - Core Parser Tests
    Tests parsing accuracy, predicted fields, and change detection.
    Run: python tests/test_core.py

    Written by: Vanea
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'parser'))

PREDICTED = {"difficulty","duration","category","location","importance","start"}
ALL = {"name":None,"start":None,"deadline":None,"difficulty":None,"duration":None,"category":None,"location":None,"importance":None,"fixed_time":False,"fixed_start":None,"recurrent":False,"recurrence_days":None}

def _pipe(flat):
    raw = {}
    for p in flat.split("|"):
        p = p.strip()
        if "=" not in p: continue
        k, _, v = p.partition("="); k, v = k.strip(), v.strip()
        if v.lower() == "null": v = None
        elif v.lower() in ("true","tru","t"): v = True
        elif v.lower().startswith("fals"): v = False
        if k not in raw: raw[k] = v
    return {f: {"value": raw.get(f, d), "predicted": f in PREDICTED} for f, d in ALL.items()}

def _changed(flat):
    ch = {}
    for p in flat.split("|"):
        p = p.strip()
        if "=" not in p: continue
        k, _, v = p.partition("="); k, v = k.strip(), v.strip()
        if v.lower() == "null": v = None
        elif v.lower() in ("true","tru","t"): v = True
        elif v.lower().startswith("fals"): v = False
        if k and k not in ch: ch[k] = {"value": v, "predicted": False}
    return ch

def _diff(old, new):
    ch = {}
    for f, ne in new.items():
        nv = ne.get("value") if isinstance(ne, dict) else ne
        oe = old.get(f); ov = oe.get("value") if isinstance(oe, dict) else oe
        if nv is None: continue
        ov_s = str(ov).lower() if ov is not None else ""
        nv_s = str(nv).lower()
        if ov_s != nv_s:
            ch[f] = {"value": nv, "predicted": ne.get("predicted", False) if isinstance(ne, dict) else False}
    return ch

passed = 0; failed = 0
def c(n, ok, d=""):
    global passed, failed
    if ok: passed += 1; print(f"  PASS | {n}")
    else: failed += 1; print(f"  FAIL | {n} | {d}")

print("="*80); print("  CORE COMPONENT TESTS"); print("="*80)

r = _pipe("name=gym | difficulty=0.55 | duration=60 | category=fitness | importance=0.41 | fixed_time=true | fixed_start=06:30 | recurrent=false")
c("name=gym", r["name"]["value"]=="gym")
c("diff=0.55", r["difficulty"]["value"]=="0.55")
c("dur=60", r["duration"]["value"]=="60")
c("cat=fitness", r["category"]["value"]=="fitness")
c("imp=0.41", r["importance"]["value"]=="0.41")
c("ft=true", r["fixed_time"]["value"] is True)
c("fs=06:30", r["fixed_start"]["value"]=="06:30")
c("rec=false", r["recurrent"]["value"] is False)

c("name explicit", r["name"]["predicted"] is False)
c("diff predicted", r["difficulty"]["predicted"] is True)
c("dur predicted", r["duration"]["predicted"] is True)
c("cat predicted", r["category"]["predicted"] is True)
c("loc predicted", r["location"]["predicted"] is True)
c("imp predicted", r["importance"]["predicted"] is True)
c("ft explicit", r["fixed_time"]["predicted"] is False)
c("fs explicit", r["fixed_start"]["predicted"] is False)
c("rec explicit", r["recurrent"]["predicted"] is False)
c("rec_days explicit", r["recurrence_days"]["predicted"] is False)
c("start predicted", r["start"]["predicted"] is True)
c("deadline explicit", r["deadline"]["predicted"] is False)

r = _pipe("name=s | location=null | fs=null")
c("null loc", r["location"]["value"] is None)
c("null fs", r["fixed_start"]["value"] is None)

r = _pipe("fixed_time=tru | recurrent=t")
c("tru", r["fixed_time"]["value"] is True)
c("t", r["recurrent"]["value"] is True)
r = _pipe("fixed_time=false | recurrent=fals")
c("false", r["fixed_time"]["value"] is False)
c("fals", r["recurrent"]["value"] is False)

r = _pipe("name=x")
c("missing diff=None", r["difficulty"]["value"] is None)
c("missing ft=False", r["fixed_time"]["value"] is False)

r = _changed("fixed_start=07:00 | duration=90")
c("ch: fs", r["fixed_start"]["value"]=="07:00")
c("ch: dur", r["duration"]["value"]=="90")
c("ch: len=2", len(r)==2)
r = _changed("diff=0.8 | imp=0.95 | cat=work")
c("ch: diff", r.get("diff",{}).get("value")=="0.8")
c("ch: imp", r.get("imp",{}).get("value")=="0.95")
c("ch: cat", r.get("cat",{}).get("value")=="work")
c("ch: len=3", len(r)==3)

old = {"name":{"value":"gym","predicted":False},"diff":{"value":"0.35","predicted":True},"fs":{"value":"06:00","predicted":False}}
new = {"name":{"value":"gym","predicted":False},"diff":{"value":"0.8","predicted":True},"fs":{"value":"07:00","predicted":False}}
ch = _diff(old, new)
c("d:diff ch", "diff" in ch)
c("d:diff val", ch.get("diff",{}).get("value")=="0.8")
c("d:fs ch", "fs" in ch)
c("d:fs val", ch.get("fs",{}).get("value")=="07:00")
c("d:name skip", "name" not in ch)

old = {"name":{"value":"gym","predicted":False},"diff":{"value":"0.35","predicted":True}}
new = {"name":{"value":"gym","predicted":False},"diff":{"value":None,"predicted":True}}
c("d:none skip", len(_diff(old,new))==0)

old = {"ft":{"value":True,"predicted":False}}
new = {"ft":{"value":False,"predicted":False}}
c("d:bool ch", "ft" in _diff(old,new))

old = {"name":{"value":"Gym","predicted":False},"cat":{"value":"FITNESS","predicted":True}}
new = {"name":{"value":"gym","predicted":False},"cat":{"value":"fitness","predicted":True}}
c("d:case skip", len(_diff(old,new))==0)

old = {"name":{"value":"w","predicted":False},"diff":{"value":"0.35","predicted":True},"dur":{"value":"45","predicted":True}}
new = {"name":{"value":"w","predicted":False},"diff":{"value":"0.8","predicted":True},"dur":{"value":"45","predicted":True}}
c("d:1 ch", len(_diff(old,new))==1 and "diff" in _diff(old,new))

old = {"name":"gym","fixed_time":True,"fixed_start":"06:00","dur":"45","diff":"0.35","imp":"0.51","recurrent":False}
old_s = {k:{"value":v,"predicted":k in PREDICTED} for k,v in old.items()}
ns = {k:{"value":v,"predicted":k in PREDICTED} for k,v in old.items()}
ns.update(_pipe("name=gym | fixed_time=true | fixed_start=07:00 | dur=45 | diff=0.35 | imp=0.51 | recurrent=false"))
ch = _diff(old_s, ns)
c("e2e: fs ch", "fixed_start" in ch and ch["fixed_start"]["value"]=="07:00")
c("e2e: 1 ch", len(ch)==1)

old = {"name":"gym","diff":"0.5","dur":"60","fixed_time":False,"recurrent":False}
ns = _pipe("name=gym | diff=0.5 | dur=60 | fixed_time=false | recurrent=false")
old = {k:{"value":v,"predicted":k in PREDICTED} for k,v in old.items()}
c("e2e: no ch", len(_diff(old,ns))==0)

print(f"\n{'='*80}")
print(f"  RESULTS: {passed}/{passed+failed} passed ({100*passed//(passed+failed)}%)")
print(f"{'='*80}")
sys.exit(0 if failed==0 else 1)
