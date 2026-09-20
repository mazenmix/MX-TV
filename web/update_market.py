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



def parse_direct_rate_text(txt):
    if any(w in txt for w in ["المسافرين","المسافر","الحجاج","السعر الرسمي"]):
        return None
    if not ("شراء" in txt and "بيع" in txt):
        return None
    m=re.search(r"شراء\s*([0-9]{3}(?:[.,][0-9]{3})?|[0-9]{4,6})[^0-9]{0,40}بيع\s*([0-9]{3}(?:[.,][0-9]{3})?|[0-9]{4,6})",txt)
    if not m:
        return None
    def conv(v):
        v=v.replace(",",".")
        if "." in v:
            a,b=v.rsplit(".",1)
            if len(b)==3:
                return int(a+b)
            if len(b)==2:
                return int(round(float(v)*100))
        n=int(v)
        return n*100 if 1000 <= n <= 9999 else n
    buy,sell=conv(m.group(1)),conv(m.group(2))
    if 120000 <= buy <= 220000 and 120000 <= sell <= 220000:
        return {"buy":buy,"sell":sell}
    return None

def telegram_direct_rate(url):
    body=fetch(url)
    chunks=body.split("tgme_widget_message_wrap")
    paused=False
    for chunk in reversed(chunks):
        txt=strip(chunk)
        if "إيقاف النشر" in txt or "ايقاف النشر" in txt or "أيقاف النشر" in txt:
            paused=True
        rate=parse_direct_rate_text(txt)
        if rate and ("الدولار" in txt or "USD" in txt.upper()):
            dm=re.search(r'datetime="([^"]+)"',chunk)
            rate["published_at"]=dm.group(1) if dm else ""
            rate["paused_after"]=paused
            return rate
    return None

def website_direct_rate(url):
    body=fetch(url)
    txt=strip(body)
    return parse_direct_rate_text(txt)

def make_exchange(name,area,source_name,source_url,status="غير منشور",state="none",buy=None,sell=None,published_at=""):
    return {
        "name":name,"area":area,"source_name":source_name,"source_url":source_url,
        "status":status,"state":state,"buy":buy,"sell":sell,"published_at":published_at
    }

def collect_exchanges():
    ex={
      "taif":make_exchange("شركة الطيف للصيرفة","الكرادة داخل / بغداد","الموقع الرسمي + Forex Board","https://taif.money/","لوحة Forex موجودة؛ السعر النقدي غير قابل للقراءة آلياً حالياً"),
      "finjan":make_exchange("شركة الفنجان للصرافة","الكرادة / فروع بغداد","Telegram الرسمي","https://t.me/s/alfenganexchange","آخر سعر رسمي منشور · النشر متوقف","stale",161000,162250),
      "qand":make_exchange("شركة القند للصرافة","المنصور","Telegram الرسمي","https://t.me/s/alqand_iq"),
      "sama":make_exchange("شركة سما بغداد للصرافة","السعدون / فروع بغداد","الموقع الرسمي","https://samabaghdad-ex.iq/","الموقع ينشر سعر 1320 الرسمي؛ لا ينشر شراء/بيع السوق"),
      "atheer":make_exchange("شركة الأثير للصرافة","العرصات الهندية","الموقع الرسمي","https://al-atheer.iq/","لا يوجد شراء/بيع سوق منشور"),
      "mayar":make_exchange("شركة الميار للصرافة","ساحة كهرمانة","الموقع الرسمي","https://almayarex.com/","لا يوجد شراء/بيع سوق منشور"),
      "karbala":make_exchange("شركة كربلاء للصيرفة","الحارثية / مقابل معرض بغداد الدولي","Facebook الرسمي","https://www.facebook.com/karbala.exchange","لا يوجد سعر سوق علني قابل للقراءة حالياً"),
      "rayyan":make_exchange("شركة الريان للصرافة","المنصور / شارع 14 رمضان","Telegram الرسمي","https://t.me/s/rayyanexco","ينشر دولار المسافرين؛ لا ينشر سعر السوق النقدي"),
      "zahra":make_exchange("صيرفة الزهراء","الكرادة / شارع محمد كبة","غير موثق","", "لم أجد مصدراً رسمياً موثقاً")
    }
    for key,url in [
        ("finjan","https://t.me/s/alfenganexchange"),
        ("qand","https://t.me/s/alqand_iq"),
        ("rayyan","https://t.me/s/rayyanexco"),
    ]:
        try:
            r=telegram_direct_rate(url)
            if r:
                ex[key]["buy"]=r["buy"]; ex[key]["sell"]=r["sell"]
                ex[key]["published_at"]=r.get("published_at","")
                if r.get("paused_after"):
                    ex[key]["status"]="آخر سعر رسمي منشور · النشر متوقف"
                    ex[key]["state"]="stale"
                else:
                    ex[key]["status"]="سعر مباشر من المصدر"
                    ex[key]["state"]="live"
        except Exception:
            pass
    # Official websites: only populate when they explicitly expose both cash buy and sell.
    for key,url in [
        ("sama","https://samabaghdad-ex.iq/"),
        ("atheer","https://al-atheer.iq/"),
        ("mayar","https://almayarex.com/"),
    ]:
        try:
            r=website_direct_rate(url)
            if r:
                ex[key]["buy"]=r["buy"]; ex[key]["sell"]=r["sell"]
                ex[key]["status"]="سعر مباشر من الموقع الرسمي"
                ex[key]["state"]="live"
        except Exception:
            pass
    return ex

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
    "usd_source_time":old.get("usd_source_time",""),
    "exchanges":old.get("exchanges",{}),
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

try:
    data["exchanges"]=collect_exchanges()
except Exception as e:
    errors.append("exchange-sources:"+type(e).__name__)


new_error=", ".join(errors) if errors else ""
old_core={
    "kifah":old.get("kifah",{}),
    "harithiya":old.get("harithiya",{}),
    "gold":old.get("gold",{}),
    "exchanges":old.get("exchanges",{}),
    "error":old.get("error",""),
}
new_core={
    "kifah":data.get("kifah",{}),
    "harithiya":data.get("harithiya",{}),
    "gold":data.get("gold",{}),
    "exchanges":data.get("exchanges",{}),
    "error":new_error,
}
data["updated_at"]=(datetime.now(BAGHDAD).isoformat()
                    if new_core != old_core or not old.get("updated_at")
                    else old["updated_at"])
data["error"]=new_error
OUT.write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps(data,ensure_ascii=False))
