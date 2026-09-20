import json, re, html as htmlmod, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"
OUT = Path(__file__).with_name("data.json")
BAGHDAD = ZoneInfo("Asia/Baghdad")

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent":UA,"Accept-Language":"ar-IQ,ar;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(4*1024*1024).decode("utf-8","replace")

def strip(s):
    s = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]*>", "\n", s)
    s = htmlmod.unescape(s).replace("\u200f"," ").replace("\u200e"," ")
    return re.sub(r"\s+"," ",s)

def norm_price(s):
    s=s.strip()
    if "," in s:
        return int(s.replace(",",""))
    if "." in s:
        a,b=s.rsplit(".",1)
        if len(b)==2:
            return int(round(float(s)*100))
        return int(s.replace(".",""))
    n=int(s)
    return n*100 if 1000 <= n <= 9999 else n

def parse_market(txt,name):
    patterns=[
        rf"{name}\s*([0-9]{{3,4}}(?:\.[0-9]{{2}})?)\s*\|\s*([0-9]{{3,4}}(?:\.[0-9]{{2}})?)",
        rf"{name}\s*([0-9]{{1,3}}(?:,[0-9]{{3}}))\s*\|\s*([0-9]{{1,3}}(?:,[0-9]{{3}}))",
    ]
    found=[]
    for p in patterns:
        found += re.findall(p,txt)
    if not found:
        return None
    buy,sell=found[-1]
    return {"buy":norm_price(buy),"sell":norm_price(sell)}

def get_gold(txt,k):
    m=re.search(rf"مثقال ذهب عيار\s*{k}[^0-9]{{0,100}}([0-9]{{1,3}}(?:,[0-9]{{3}}){{1,2}})\s*د\.ع",txt)
    return int(m.group(1).replace(",","")) if m else 0

old={}
if OUT.exists():
    try: old=json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: old={}

errors=[]
data={"kifah":old.get("kifah",{}),"harithiya":old.get("harithiya",{}),"gold":old.get("gold",{})}

try:
    t=strip(fetch("https://t.me/s/dollariraqi"))
    k=parse_market(t,"كفاح")
    h=parse_market(t,"حارثية")
    if k: data["kifah"]=k
    else: errors.append("kifah")
    if h: data["harithiya"]=h
    else: errors.append("harithiya")
except Exception as e:
    errors.append("usd:"+type(e).__name__)

try:
    gtxt=strip(fetch("https://mithqaly.com/%D8%A7%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/"))
    k21=get_gold(gtxt,"21")
    k24=get_gold(gtxt,"24")
    if k24:
        k18=round(k24*0.75)
    elif k21:
        k18=round(k21*(18/21)); k24=round(k21*(24/21))
    else:
        k18=0
    if k21 and k24:
        data["gold"]={"k18":k18,"k21":k21,"k24":k24}
    else:
        errors.append("gold")
except Exception as e:
    errors.append("gold:"+type(e).__name__)

data["updated_at"]=datetime.now(BAGHDAD).isoformat()
data["error"]=", ".join(errors) if errors else ""
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data,ensure_ascii=False))
