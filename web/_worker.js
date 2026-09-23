const TELEGRAM_URL='https://t.me/s/dollariraqi';
const KUKH_URL='https://t.me/s/Kukh_alomlat';
const GOLD_URL='https://mithqaly.com/%D8%A7%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/';
const FALLBACK_URL='https://raw.githubusercontent.com/mazenmix/MX-TV/main/web/data.json';

const UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36';

function decodeEntities(s){
  return s
    .replace(/&nbsp;|&#160;/gi,' ')
    .replace(/&quot;/gi,'"')
    .replace(/&#39;|&apos;/gi,"'")
    .replace(/&lt;/gi,'<')
    .replace(/&gt;/gi,'>')
    .replace(/&amp;/gi,'&')
    .replace(/&#x([0-9a-f]+);/gi,(_,h)=>String.fromCodePoint(parseInt(h,16)))
    .replace(/&#([0-9]+);/g,(_,n)=>String.fromCodePoint(parseInt(n,10)));
}

function stripHtml(s){
  return decodeEntities(
    s.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,' ')
     .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,' ')
     .replace(/<br\s*\/?>/gi,' ')
     .replace(/<[^>]*>/g,' ')
  ).replace(/[\u200e\u200f]/g,' ').replace(/\s+/g,' ').trim();
}

function normPrice(s){
  s=String(s||'').trim().replace(/،/g,',');
  if(s.includes(',') && s.includes('.')) s=s.replace(/,/g,'');
  else if(s.includes(',')) return parseInt(s.replace(/,/g,''),10);
  if(s.includes('.')){
    const parts=s.split('.');
    if(parts[parts.length-1].length===2) return Math.round(parseFloat(s)*100);
    return parseInt(s.replace(/\./g,''),10);
  }
  const n=parseInt(s,10);
  return n>=1000 && n<=9999 ? n*100 : n;
}

function parseMarket(text,name){
  const p=new RegExp(name+'\\s*([0-9]{3,4}(?:\\.[0-9]{2})?|[0-9]{1,3}(?:[,،][0-9]{3}))\\s*\\|\\s*([0-9]{3,4}(?:\\.[0-9]{2})?|[0-9]{1,3}(?:[,،][0-9]{3}))');
  const m=text.match(p);
  if(!m) return null;
  return {buy:normPrice(m[1]),sell:normPrice(m[2])};
}

function parseTelegramBaghdad(body){
  const chunks=body.split('tgme_widget_message_wrap');
  for(let i=chunks.length-1;i>=0;i--){
    const raw=chunks[i];
    const txt=stripHtml(raw);
    if(!txt.includes('كفاح') || !txt.includes('حارثية')) continue;
    const kifah=parseMarket(txt,'كفاح');
    const harithiya=parseMarket(txt,'حارثية');
    if(!kifah || !harithiya) continue;
    const dm=raw.match(/datetime=["']([^"']+)["']/i);
    const tm=txt.match(/تحديث\s*([0-9]{1,2}:[0-9]{2})/);
    return {
      kifah,harithiya,
      published_at:dm?dm[1]:'',
      source_time:tm?tm[1]:'',
      source:'Telegram @dollariraqi',
      source_url:TELEGRAM_URL
    };
  }
  return null;
}

function parseKukhLatest(body){
  const chunks=body.split('tgme_widget_message_wrap');
  for(let i=chunks.length-1;i>=0;i--){
    const raw=chunks[i];
    const txt=stripHtml(raw);
    if(!txt.includes('سعر الان') && !txt.includes('سعر الصرف')) continue;
    const sm=txt.match(/البيع[.\s]*([0-9]{3}(?:[,،][0-9]{3}))/);
    const bm=txt.match(/(?:الشراء|لشراء|شراء)[.\s]*([0-9]{3}(?:[,،][0-9]{3}))/);
    if(!sm || !bm) continue;
    const sell=parseInt(sm[1].replace(/[,،]/g,''),10);
    const buy=parseInt(bm[1].replace(/[,،]/g,''),10);
    if(buy<120000 || buy>220000 || sell<120000 || sell>220000) continue;
    const dm=raw.match(/datetime=["']([^"']+)["']/i);
    return {buy,sell,source:KUKH_URL,published_at:dm?dm[1]:''};
  }
  return null;
}

function getGold(text,k){
  const re=new RegExp('مثقال ذهب عيار\\s*'+k+'[^0-9]{0,120}([0-9]{1,3}(?:[,،][0-9]{3}){1,2})\\s*د\\.?ع');
  const m=text.match(re);
  return m?parseInt(m[1].replace(/[,،]/g,''),10):0;
}

async function fetchText(url){
  const r=await fetch(url,{
    headers:{'User-Agent':UA,'Accept-Language':'ar-IQ,ar;q=0.9,en;q=0.8','Cache-Control':'no-cache'},
    redirect:'follow',
    cf:{cacheTtl:20,cacheEverything:true}
  });
  if(!r.ok) throw new Error('HTTP '+r.status);
  return await r.text();
}

async function fallbackData(){
  try{
    const r=await fetch(FALLBACK_URL+'?t='+Date.now(),{cache:'no-store'});
    if(r.ok) return await r.json();
  }catch(_){}
  return {};
}

function ageMinutes(iso){
  const t=Date.parse(iso||'');
  return Number.isFinite(t)?(Date.now()-t)/60000:1e9;
}

async function marketResponse(){
  const old=await fallbackData();
  const data={
    kifah:old.kifah||{},
    harithiya:old.harithiya||{},
    kukh:old.kukh||{},
    gold:old.gold||{},
    usd_meta:old.usd_meta||{},
    usd_source_time:old.usd_source_time||'',
    updated_at:new Date().toISOString(),
    error:''
  };
  const errors=[];

  try{
    const tg=parseTelegramBaghdad(await fetchText(TELEGRAM_URL));
    if(tg){
      data.kifah=tg.kifah;
      data.harithiya=tg.harithiya;
      data.usd_source_time=tg.source_time||'';
      const state=ageMinutes(tg.published_at)<=90?'live':'stale';
      data.usd_meta={
        source:'Telegram @dollariraqi',
        source_url:TELEGRAM_URL,
        published_at:tg.published_at,
        state,
        note:state==='live'?'Telegram @dollariraqi · مباشر':'Telegram @dollariraqi · آخر منشور متاح من القناة',
        source_time:tg.source_time||''
      };
    }else errors.push('usd-telegram-parse');
  }catch(e){ errors.push('usd-telegram'); }

  try{
    const k=parseKukhLatest(await fetchText(KUKH_URL));
    if(k) data.kukh=k;
    else errors.push('kukh-parse');
  }catch(e){ errors.push('kukh'); }

  try{
    const txt=stripHtml(await fetchText(GOLD_URL));
    let k21=getGold(txt,'21');
    let k24=getGold(txt,'24');
    let k18=k24?Math.round(k24*0.75):(k21?Math.round(k21*(18/21)):0);
    if(!k24 && k21) k24=Math.round(k21*(24/21));
    if(k21 && k24) data.gold={k18,k21,k24};
    else errors.push('gold-parse');
  }catch(e){ errors.push('gold'); }

  data.updated_at=new Date().toISOString();
  data.error=errors.join(', ');

  return new Response(JSON.stringify(data,null,2),{
    status:200,
    headers:{
      'Content-Type':'application/json; charset=utf-8',
      'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0',
      'Pragma':'no-cache',
      'Access-Control-Allow-Origin':'*'
    }
  });
}

export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);
    if(url.pathname==='/api/market'){
      if(request.method==='OPTIONS'){
        return new Response(null,{status:204,headers:{
          'Access-Control-Allow-Origin':'*',
          'Access-Control-Allow-Methods':'GET, OPTIONS',
          'Access-Control-Allow-Headers':'Content-Type'
        }});
      }
      if(request.method!=='GET') return new Response('Method Not Allowed',{status:405});
      return marketResponse();
    }
    return env.ASSETS.fetch(request);
  }
};
