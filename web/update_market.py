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
    return re.sub(r"\s+"," ",s).strip()

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

def parse_market(text,name):
    for p in [
        rf"{name}\s*([0-9]{{3,4}}(?:\.[0-9]{{2}})?)\s*\|\s*([0-9]{{3,4}}(?:\.[0-9]{{2}})?)",
        rf"{name}\s*([0-9]{{1,3}}(?:,[0-9]{{3}}))\s*\|\s*([0-9]{{1,3}}(?:,[0-9]{{3}}))",
    ]:
        m=re.search(p,text)
        if m:
            return {"buy":norm_price(m.group(1)),"sell":norm_price(m.group(2))}
    return None

def parse_baghdad_same_post(body):
    blocks=re.findall(r'(?is)<div[^>]+class="[^"]*tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>',body)
    for raw in reversed(blocks):
        txt=strip(raw)
        if "كفاح" not in txt or "حارثية" not in txt:
            continue
        k=parse_market(txt,"كفاح")
        h=parse_market(txt,"حارثية")
        if k and h:
            tm=re.search(r"تحديث\s*([0-9]{1,2}:[0-9]{2})",txt)
            return k,h,(tm.group(1) if tm else "")
    # Safe fallback: use the whole page only if both can be parsed.
    txt=strip(body)
    k=parse_market(txt,"كفاح")
    h=parse_market(txt,"حارثية")
    return k,h,""


def parse_baghdad_retail_from_shafaq():
    base="https://shafaq.com"
    cat=fetch(base+"/ar/%D8%A7%D9%82%D8%AA%D8%B5%D9%80%D8%A7%D8%AF")
    anchors=re.findall(r'(?is)<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>',cat)
    candidates=[]
    for href,inner in anchors:
        title=strip(inner)
        if "الدولار" in title and "بغداد" in title:
            url=href if href.startswith("http") else base+href
            if url not in candidates:
                candidates.append(url)
    for url in candidates[:8]:
        try:
            txt=strip(fetch(url))
            sm=re.search(r'سعر البيع[^0-9]{0,120}([0-9]{3}(?:[,،]?[0-9]{3}))',txt)
            bm=re.search(r'سعر الشراء[^0-9]{0,120}([0-9]{3}(?:[,،]?[0-9]{3}))',txt)
            if sm and bm:
                sell=int(sm.group(1).replace(",","").replace("،",""))
                buy=int(bm.group(1).replace(",","").replace("،",""))
                if 120000 <= buy <= 200000 and 120000 <= sell <= 200000:
                    return {"buy":buy,"sell":sell,"source":"Shafaq News Baghdad retail market"}
        except Exception:
            pass
    return None

def get_gold(txt,k):
    m=re.search(rf"مثقال ذهب عيار\s*{k}[^0-9]{{0,100}}([0-9]{{1,3}}(?:,[0-9]{{3}}){{1,2}})\s*د\.ع",txt)
    return int(m.group(1).replace(",","")) if m else 0

old={}
if OUT.exists():
    try: old=json.loads(OUT.read_text(encoding="utf-8"))
    except Exception: old={}

errors=[]
data={
    "kifah":old.get("kifah",{}),
    "harithiya":old.get("harithiya",{}),
    "gold":old.get("gold",{}),
    "retail_baghdad":old.get("retail_baghdad",{}),
    "usd_source_time":old.get("usd_source_time",""),
}

try:
    body=fetch("https://t.me/s/dollariraqi")
    k,h,src_time=parse_baghdad_same_post(body)
    if k and h:
        data["kifah"]=k
        data["harithiya"]=h
        data["usd_source_time"]=src_time
    else:
        errors.append("usd-parse")
except Exception as e:
    errors.append("usd:"+type(e).__name__)

try:
    retail=parse_baghdad_retail_from_shafaq()
    if retail:
        data["retail_baghdad"]=retail
    else:
        errors.append("retail-parse")
except Exception as e:
    errors.append("retail:"+type(e).__name__)

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
        errors.append("gold-parse")
except Exception as e:
    errors.append("gold:"+type(e).__name__)

new_error=", ".join(errors) if errors else ""
old_core={
    "kifah":old.get("kifah",{}),
    "harithiya":old.get("harithiya",{}),
    "gold":old.get("gold",{}),
    "retail_baghdad":old.get("retail_baghdad",{}),
    "error":old.get("error",""),
}
new_core={
    "kifah":data.get("kifah",{}),
    "harithiya":data.get("harithiya",{}),
    "gold":data.get("gold",{}),
    "retail_baghdad":data.get("retail_baghdad",{}),
    "error":new_error,
}
data["updated_at"]=(datetime.now(BAGHDAD).isoformat()
                    if new_core != old_core or not old.get("updated_at")
                    else old["updated_at"])
data["error"]=new_error
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data,ensure_ascii=False))
