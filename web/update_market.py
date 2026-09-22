import json, re, html as htmlmod, urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urljoin, unquote

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36"
OUT = Path(__file__).with_name("data.json")
BAGHDAD = ZoneInfo("Asia/Baghdad")
TELEGRAM_URL = "https://t.me/s/dollariraqi"
SHFAQ_ECON = "https://www.shafaq.com/en/tags/Baghdad"
ALSUMARIA_ECON = "https://www.alsumaria.tv/economy-news"
ARABRATES_URL = "https://arabrates.net/iq/currency/usd/"

def fetch(url):
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept-Language": "ar-IQ,ar;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
    })
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read(5*1024*1024).decode("utf-8","replace")

def strip(s):
    s = re.sub(r"(?is)<script.*?</script>|<style.*?</style>", " ", s)
    s = re.sub(r"(?s)<[^>]*>", "\n", s)
    s = htmlmod.unescape(s).replace("\u200f"," ").replace("\u200e"," ")
    return re.sub(r"\s+"," ",s).strip()

def norm_price(s):
    s=s.strip().replace("،",",")
    # 1,580.00 -> 1580.00
    if "," in s and "." in s:
        s=s.replace(",","")
    elif "," in s:
        return int(s.replace(",",""))
    if "." in s:
        a,b=s.rsplit(".",1)
        if len(b)==2:
            return int(round(float(s)*100))
        return int(s.replace(".",""))
    n=int(s)
    return n*100 if 1000 <= n <= 9999 else n

def iso_dt(s):
    if not s: return None
    try:
        return datetime.fromisoformat(s.replace("Z","+00:00"))
    except Exception:
        return None

def age_minutes(iso):
    d=iso_dt(iso)
    if not d: return 10**9
    if d.tzinfo is None: d=d.replace(tzinfo=BAGHDAD)
    return (datetime.now(BAGHDAD)-d.astimezone(BAGHDAD)).total_seconds()/60

def same_baghdad_day(iso):
    d=iso_dt(iso)
    if not d: return False
    if d.tzinfo is None: d=d.replace(tzinfo=BAGHDAD)
    return d.astimezone(BAGHDAD).date()==datetime.now(BAGHDAD).date()

def parse_market(text,name):
    for p in [
        rf"{name}\s*([0-9]{{3,4}}(?:\.[0-9]{{2}})?)\s*\|\s*([0-9]{{3,4}}(?:\.[0-9]{{2}})?)",
        rf"{name}\s*([0-9]{{1,3}}(?:[,،][0-9]{{3}}))\s*\|\s*([0-9]{{1,3}}(?:[,،][0-9]{{3}}))",
    ]:
        m=re.search(p,text)
        if m:
            return {"buy":norm_price(m.group(1)),"sell":norm_price(m.group(2))}
    return None

def parse_telegram_baghdad(body):
    chunks=body.split("tgme_widget_message_wrap")
    for raw in reversed(chunks):
        txt=strip(raw)
        if "كفاح" not in txt or "حارثية" not in txt:
            continue
        k=parse_market(txt,"كفاح")
        h=parse_market(txt,"حارثية")
        if not (k and h):
            continue
        dm=re.search(r'datetime="([^"]+)"',raw)
        tm=re.search(r"تحديث\s*([0-9]{1,2}:[0-9]{2})",txt)
        return {
            "kifah":k,
            "harithiya":h,
            "published_at":dm.group(1) if dm else "",
            "source_time":tm.group(1) if tm else "",
            "source":"Telegram @dollariraqi",
            "source_url":TELEGRAM_URL,
        }
    return None

def anchor_candidates(body, base, must_words):
    out=[]
    for href,inner in re.findall(r'(?is)<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',body):
        title=strip(inner)
        decoded=unquote(href)
        hay=(title+" "+decoded).lower()
        if all(w in hay for w in must_words):
            url=urljoin(base,htmlmod.unescape(href))
            if url not in out: out.append(url)
    return out

def parse_article_iso(body):
    for p in [
        r'(20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d))',
        r'(20\d\d-\d\d-\d\d)\s*[|]\s*(\d\d:\d\d)',
    ]:
        m=re.search(p,body)
        if m:
            if len(m.groups())==1: return m.group(1)
            return m.group(1)+"T"+m.group(2)+":00+03:00"
    return ""

def parse_common_baghdad_price(txt):
    pats=[
        r"Al[- ]Kifah\s+and\s+Al[- ]Harithiya[^0-9]{0,220}([0-9]{3}[,،][0-9]{3})",
        r"Al[- ]Kifah\s+and\s+Al[- ]Harithiya[^0-9]{0,220}([0-9]{6})",
        r"بورصتي\s+الكفاح\s+والحارثية[^0-9]{0,180}([0-9]{3}[,،][0-9]{3})",
        r"بورصتي\s+الكفاح\s+والحارثية[^0-9]{0,180}([0-9]{6})",
        r"بورصتي\s+الكفاح\s+والحارثية[^0-9]{0,180}([0-9]{3,4}(?:\.[0-9]{2})?)",
    ]
    for p in pats:
        m=re.search(p,txt,re.I)
        if m:
            n=norm_price(m.group(1))
            if 120000<=n<=220000: return n
    return 0

def latest_shafaq():
    try:
        listing=fetch(SHFAQ_ECON)
        candidates=anchor_candidates(listing,"https://www.shafaq.com",["dollar","baghdad"])
        if not candidates:
            candidates=anchor_candidates(listing,"https://www.shafaq.com",["usd","baghdad"])
        for url in candidates[:12]:
            body=fetch(url)
            txt=strip(body)
            price=parse_common_baghdad_price(txt)
            published=parse_article_iso(body)
            if price:
                return {
                    "kifah":{"buy":price,"sell":price},
                    "harithiya":{"buy":price,"sell":price},
                    "published_at":published,
                    "source":"Shafaq News",
                    "source_url":url,
                    "note":"سعر بورصتي الكفاح والحارثية المنشور من مراسل شفق",
                }
    except Exception:
        pass
    return None

def latest_alsumaria():
    try:
        listing=fetch(ALSUMARIA_ECON)
        candidates=anchor_candidates(listing,"https://www.alsumaria.tv",["الدولار"])
        for url in candidates[:15]:
            body=fetch(url)
            txt=strip(body)
            if "الكفاح" not in txt or "الحارثية" not in txt: continue
            price=parse_common_baghdad_price(txt)
            published=parse_article_iso(body)
            if price:
                return {
                    "kifah":{"buy":price,"sell":price},
                    "harithiya":{"buy":price,"sell":price},
                    "published_at":published,
                    "source":"Alsumaria",
                    "source_url":url,
                    "note":"سعر بورصتي الكفاح والحارثية المنشور من السومرية",
                }
    except Exception:
        pass
    return None

def arabrates_daily():
    try:
        body=fetch(ARABRATES_URL)
        txt=strip(body)
        bm=re.search(r"شراء السوق[^0-9]{0,120}([0-9]{1,3}(?:,[0-9]{3})(?:\.[0-9]{1,2})?|[0-9]{3,4}(?:\.[0-9]{1,2})?)",txt)
        sm=re.search(r"بيع السوق[^0-9]{0,120}([0-9]{1,3}(?:,[0-9]{3})(?:\.[0-9]{1,2})?|[0-9]{3,4}(?:\.[0-9]{1,2})?)",txt)
        if not (bm and sm): return None
        buy=norm_price(bm.group(1)); sell=norm_price(sm.group(1))
        if not (120000<=buy<=220000 and 120000<=sell<=220000): return None
        now=datetime.now(BAGHDAD)
        return {
            "kifah":{"buy":buy,"sell":sell},
            "harithiya":{"buy":buy,"sell":sell},
            "published_at":now.replace(hour=0,minute=0,second=0,microsecond=0).isoformat(),
            "source":"ArabRates",
            "source_url":ARABRATES_URL,
            "note":"تحديث يومي لسوق الكفاح والحارثية",
        }
    except Exception:
        return None

def choose_usd():
    tg=None
    try: tg=parse_telegram_baghdad(fetch(TELEGRAM_URL))
    except Exception: pass

    sh=latest_shafaq()

    if tg and age_minutes(tg.get("published_at",""))<=90:
        meta={
            "source":tg["source"],"source_url":tg["source_url"],
            "published_at":tg.get("published_at",""),"state":"live",
            "note":"المصدر اللحظي الرئيسي","source_time":tg.get("source_time",""),
        }
        if sh and same_baghdad_day(sh.get("published_at","")):
            meta["verification"]={
                "source":"Shafaq News","price":sh["kifah"]["sell"],
                "published_at":sh.get("published_at",""),"source_url":sh.get("source_url",""),
            }
        return tg["kifah"],tg["harithiya"],meta

    if sh and same_baghdad_day(sh.get("published_at","")):
        meta={
            "source":sh["source"],"source_url":sh["source_url"],
            "published_at":sh.get("published_at",""),"state":"backup",
            "note":"Telegram غير حديث؛ تم استخدام شفق اليوم","source_time":"",
        }
        if tg:
            meta["telegram_last"]={
                "published_at":tg.get("published_at",""),
                "kifah":tg.get("kifah"),"harithiya":tg.get("harithiya"),
            }
        return sh["kifah"],sh["harithiya"],meta

    al=latest_alsumaria()
    if al and same_baghdad_day(al.get("published_at","")):
        return al["kifah"],al["harithiya"],{
            "source":al["source"],"source_url":al["source_url"],
            "published_at":al.get("published_at",""),"state":"backup",
            "note":"Telegram وشفق غير حديثين؛ تم استخدام السومرية","source_time":"",
        }

    ar=arabrates_daily()
    if ar:
        return ar["kifah"],ar["harithiya"],{
            "source":ar["source"],"source_url":ar["source_url"],
            "published_at":ar.get("published_at",""),"state":"backup",
            "note":"آخر fallback يومي","source_time":"",
        }

    if tg:
        return tg["kifah"],tg["harithiya"],{
            "source":tg["source"],"source_url":tg["source_url"],
            "published_at":tg.get("published_at",""),"state":"stale",
            "note":"آخر سعر Telegram متوفر لكنه قديم","source_time":tg.get("source_time",""),
        }
    return None,None,{"source":"Unavailable","source_url":"","published_at":"","state":"stale","note":"لا يوجد مصدر متاح","source_time":""}

def parse_kukh_latest(body):
    blocks=body.split("tgme_widget_message_wrap")
    for raw in reversed(blocks):
        txt=strip(raw)
        if "سعر الان" not in txt and "سعر الصرف" not in txt:
            continue
        sm=re.search(r"البيع[\.\s]*([0-9]{3}(?:[,،][0-9]{3}))",txt)
        bm=re.search(r"(?:الشراء|لشراء)[\.\s]*([0-9]{3}(?:[,،][0-9]{3}))",txt)
        if sm and bm:
            sell=int(sm.group(1).replace(",","").replace("،",""))
            buy=int(bm.group(1).replace(",","").replace("،",""))
            if 120000<=buy<=220000 and 120000<=sell<=220000:
                tm=re.search(r'datetime="([^"]+)"',raw)
                return {"buy":buy,"sell":sell,"source":"https://t.me/s/Kukh_alomlat","published_at":tm.group(1) if tm else ""}
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
    "kukh":old.get("kukh",{}),
    "gold":old.get("gold",{}),
    "usd_meta":old.get("usd_meta",{}),
    "usd_source_time":old.get("usd_source_time",""),
}

try:
    k,h,meta=choose_usd()
    if k and h:
        data["kifah"]=k
        data["harithiya"]=h
        data["usd_meta"]=meta
        data["usd_source_time"]=meta.get("source_time","")
    else:
        errors.append("usd-all-sources")
except Exception as e:
    errors.append("usd:"+type(e).__name__)

try:
    kr=parse_kukh_latest(fetch("https://t.me/s/Kukh_alomlat"))
    if kr: data["kukh"]=kr
    else: errors.append("kukh-parse")
except Exception as e:
    errors.append("kukh:"+type(e).__name__)

try:
    gtxt=strip(fetch("https://mithqaly.com/%D8%A7%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/"))
    k21=get_gold(gtxt,"21"); k24=get_gold(gtxt,"24")
    k18=round(k24*0.75) if k24 else (round(k21*(18/21)) if k21 else 0)
    if not k24 and k21: k24=round(k21*(24/21))
    if k21 and k24: data["gold"]={"k18":k18,"k21":k21,"k24":k24}
    else: errors.append("gold-parse")
except Exception as e:
    errors.append("gold:"+type(e).__name__)

data["updated_at"]=datetime.now(BAGHDAD).isoformat()
data["error"]=", ".join(errors) if errors else ""
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data,ensure_ascii=False))
