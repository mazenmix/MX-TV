const TELEGRAM_URL='https://t.me/s/dollariraqi';
const KUKH_URL='https://t.me/s/Kukh_alomlat';
const GAILANY_TG_URL='https://t.me/s/gailany_rates';
const HATWAN_URL='https://hatwan.co/en';
const CBI_URL='https://cbi.iq/';
const GOLD_URL='https://mithqaly.com/%D8%A7%D8%B3%D8%B9%D8%A7%D8%B1-%D8%A7%D9%84%D8%B0%D9%87%D8%A8/';
const FALLBACK_URL='https://raw.githubusercontent.com/mazenmix/MX-TV/main/web/data.json';
const BETA_RAW_URL='https://raw.githubusercontent.com/mazenmix/MX-TV/main/web/beta.html';

const UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/153 Safari/537.36';

function decodeEntities(s){
  return String(s||'')
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
    String(s||'').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,' ')
     .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,' ')
     .replace(/<br\s*\/?>/gi,' ')
     .replace(/<[^>]*>/g,' ')
  ).replace(/[\u200e\u200f]/g,' ').replace(/\s+/g,' ').trim();
}

function num(v){
  let s=String(v||'').trim().replace(/،/g,',');
  if(!s) return 0;
  if(/^\d{1,3}(,\d{3})+$/.test(s)) return Number(s.replace(/,/g,''));
  if(/^\d{1,3}(\.\d{3})+$/.test(s)) return Number(s.replace(/\./g,''));
  s=s.replace(/,/g,'');
  const n=Number(s);
  return Number.isFinite(n)?n:0;
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
  const chunks=String(body||'').split('tgme_widget_message_wrap');
  for(let i=chunks.length-1;i>=0;i--){
    const raw=chunks[i];
    const txt=stripHtml(raw);
    if(!txt.includes('كفاح') || !txt.includes('حارثية')) continue;
    const kifah=parseMarket(txt,'كفاح');
    const harithiya=parseMarket(txt,'حارثية');
    if(!kifah || !harithiya) continue;
    const dm=raw.match(/datetime=["']([^"']+)["']/i);
    const tm=txt.match(/تحديث\s*([0-9]{1,2}:[0-9]{2})/);
    return {kifah,harithiya,published_at:dm?dm[1]:'',source_time:tm?tm[1]:'',source:'Telegram @dollariraqi',source_url:TELEGRAM_URL};
  }
  return null;
}

function parseKukhLatest(body){
  const chunks=String(body||'').split('tgme_widget_message_wrap');
  for(let i=chunks.length-1;i>=0;i--){
    const raw=chunks[i];
    const txt=stripHtml(raw);
    if(!txt.includes('سعر الان') && !txt.includes('سعر الصرف')) continue;
    const pairs=[...txt.matchAll(/البيع[.\s]*([0-9][0-9.,]*)[\s\S]{0,90}?(?:لشراء|الشراء|شراء)[.\s]*([0-9][0-9.,]*)/g)];
    if(!pairs.length) continue;
    const p=pairs.map(x=>({sell:num(x[1]),buy:num(x[2])}));
    if(!p[0]?.sell || !p[0]?.buy || p[0].sell<120000 || p[0].buy<120000) continue;
    const dm=raw.match(/datetime=["']([^"']+)["']/i);
    return {
      buy:p[0].buy,sell:p[0].sell,source:'كوخ العملات',source_url:KUKH_URL,published_at:dm?dm[1]:'',
      rates:{USD:p[0]||null,EUR:p[1]||null,TRY:p[2]||null,GBP:p[3]||null,JOD:p[4]||null,AED:p[5]||null,SAR:p[6]||null}
    };
  }
  return null;
}

function parseGailanyLatest(body){
  const chunks=String(body||'').split('tgme_widget_message_wrap');
  for(let i=chunks.length-1;i>=0;i--){
    const raw=chunks[i];
    const txt=stripHtml(raw);
    if(!txt.includes('Gailany Money Exchange') || !txt.includes('USD') || !txt.includes('EUR')) continue;
    if(!txt.includes('Buy') && !txt.includes('بيع')) continue;
    const rate=(code)=>{
      const m=txt.match(new RegExp(code+'\\s*([0-9][0-9.,]*)\\s*[→>\\-]+\\s*([0-9][0-9.,]*)','i'));
      return m?{buy:num(m[1]),sell:num(m[2])}:null;
    };
    const usd=rate('USD');
    if(!usd) continue;
    const dm=raw.match(/datetime=["']([^"']+)["']/i);
    return {source:'Gailany Exchange',source_url:GAILANY_TG_URL,published_at:dm?dm[1]:'',rates:{USD:usd,EUR:rate('EUR'),GBP:rate('GBP'),TRY:rate('TRY'),AED:rate('AED'),SAR:rate('SAR')}};
  }
  return null;
}

function parseHatwan(body){
  const txt=stripHtml(body);
  const rate=(label)=>{
    const pos=txt.indexOf(label);
    if(pos<0) return null;
    const part=txt.slice(pos,pos+850);
    const m=part.match(/Buy\s*([0-9][0-9.,]*)[\s\S]{0,220}?Sell\s*([0-9][0-9.,]*)/i);
    return m?{buy:num(m[1]),sell:num(m[2])}:null;
  };
  const updated=(txt.match(/Updated\s+([^|]{1,40}?)(?=US Dollar|Currency converter|All currencies)/i)||[])[1]||'';
  return {source:'Hatwan Exchange',source_url:HATWAN_URL,updated:updated.trim(),rates:{USD:rate('US Dollar'),EUR:rate('Euro'),GBP:rate('British Pound'),TRY:rate('Turkish Lira'),AED:rate('UAE Dirham'),SAR:rate('Saudi Riyal'),TOMAN:rate('Tuman')}};
}

function parseCbi(body){
  const txt=stripHtml(body).replace(/\|/g,' ');
  const rate=(label,code)=>{
    const patterns=[
      new RegExp(label+'\\s*'+code+'[^0-9]{0,30}([0-9]+(?:[.,][0-9]+)?)','i'),
      new RegExp('\\b'+code+'\\b[^0-9]{0,40}([0-9]+(?:[.,][0-9]+)?)','i')
    ];
    for(const re of patterns){
      const m=txt.match(re);
      if(m){const v=num(String(m[1]).replace(',','.'));if(Number.isFinite(v))return v;}
    }
    return null;
  };
  return {source:'البنك المركزي العراقي',source_url:CBI_URL,rates:{USD:rate('U\\.?S\\.?\\s*dollar','USD'),EUR:rate('Euro','EUR'),GBP:rate('Pound Sterling','GBP'),TRY:rate('Turkish Lira','TRY'),AED:rate('U\\.?A\\.?E\\s*Dirham','AED'),SAR:rate('Saudi Arabian Rial','SAR')}};
}

function getGold(text,k){
  const re=new RegExp('مثقال ذهب عيار\\s*'+k+'[^0-9]{0,120}([0-9]{1,3}(?:[,،][0-9]{3}){1,2})\\s*د\\.?ع');
  const m=text.match(re);
  return m?parseInt(m[1].replace(/[,،]/g,''),10):0;
}

async function fetchText(url){
  const r=await fetch(url,{headers:{'User-Agent':UA,'Accept-Language':'ar-IQ,ar;q=0.9,en;q=0.8','Cache-Control':'no-cache'},redirect:'follow',cf:{cacheTtl:20,cacheEverything:true}});
  if(!r.ok) throw new Error('HTTP '+r.status);
  return await r.text();
}

async function fetchCbiText(){
  const urls=[CBI_URL,CBI_URL+'?lang=en'];
  let lastErr=null;
  for(const url of urls){
    try{
      const r=await fetch(url,{headers:{'User-Agent':UA,'Accept':'text/html,application/xhtml+xml','Accept-Language':'en-US,en;q=0.9,ar-IQ;q=0.8','Cache-Control':'no-cache'},redirect:'follow',cf:{cacheTtl:3600,cacheEverything:true}});
      if(!r.ok){lastErr=new Error('HTTP '+r.status);continue;}
      const body=await r.text();
      if(/\bUSD\b/i.test(stripHtml(body))) return body;
      lastErr=new Error('CBI USD row not found');
    }catch(e){lastErr=e;}
  }
  throw lastErr||new Error('CBI unavailable');
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

async function betaPageResponse(request,env){
  try{
    const r=await fetch(BETA_RAW_URL+'?t='+Date.now(),{cache:'no-store',headers:{'User-Agent':UA,'Cache-Control':'no-cache'}});
    if(r.ok){
      const html=await r.text();
      return new Response(html,{status:200,headers:{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache'}});
    }
  }catch(_){}
  try{
    const u=new URL(request.url);u.pathname='/beta.html';u.search='';
    return await env.ASSETS.fetch(new Request(u.toString(),request));
  }catch(_){}
  return new Response('MX Exchanger Beta temporarily unavailable',{status:503,headers:{'Content-Type':'text/plain; charset=utf-8','Cache-Control':'no-store'}});
}

async function marketResponse(){
  const old=await fallbackData();
  const data={
    kifah:old.kifah||{},harithiya:old.harithiya||{},kukh:old.kukh||{},gold:old.gold||{},usd_meta:old.usd_meta||{},usd_source_time:old.usd_source_time||'',
    kukh_rates:old.kukh_rates||{},gailany:old.gailany||{},hatwan:old.hatwan||{},cbi:{source:'البنك المركزي العراقي',source_url:CBI_URL,rates:{USD:null}},updated_at:new Date().toISOString(),error:''
  };
  const errors=[];
  const jobs=await Promise.allSettled([fetchText(TELEGRAM_URL),fetchText(KUKH_URL),fetchText(GAILANY_TG_URL),fetchText(HATWAN_URL),fetchCbiText(),fetchText(GOLD_URL)]);

  if(jobs[0].status==='fulfilled'){
    const tg=parseTelegramBaghdad(jobs[0].value);
    if(tg){
      data.kifah=tg.kifah; data.harithiya=tg.harithiya; data.usd_source_time=tg.source_time||'';
      const state=ageMinutes(tg.published_at)<=90?'live':'stale';
      data.usd_meta={source:'Telegram @dollariraqi',source_url:TELEGRAM_URL,published_at:tg.published_at,state,note:state==='live'?'Telegram @dollariraqi · مباشر':'Telegram @dollariraqi · آخر منشور متاح من القناة',source_time:tg.source_time||''};
    }else errors.push('usd-telegram-parse');
  }else errors.push('usd-telegram');

  if(jobs[1].status==='fulfilled'){
    const k=parseKukhLatest(jobs[1].value);
    if(k){data.kukh={buy:k.buy,sell:k.sell,source:k.source,source_url:k.source_url,published_at:k.published_at};data.kukh_rates=k.rates||{};} else errors.push('kukh-parse');
  }else errors.push('kukh');

  if(jobs[2].status==='fulfilled'){
    const g=parseGailanyLatest(jobs[2].value);
    if(g) data.gailany={...g,checked_at:new Date().toISOString()}; else errors.push('gailany-parse');
  }else errors.push('gailany');

  if(jobs[3].status==='fulfilled'){
    const h=parseHatwan(jobs[3].value);
    if(h?.rates?.USD) data.hatwan={...h,checked_at:new Date().toISOString()}; else errors.push('hatwan-parse');
  }else errors.push('hatwan');

  if(jobs[4].status==='fulfilled'){
    const c=parseCbi(jobs[4].value);
    if(c?.rates?.USD!==null && c?.rates?.USD!==undefined) data.cbi=c; else errors.push('cbi-parse');
  }else errors.push('cbi');

  if(jobs[5].status==='fulfilled'){
    const txt=stripHtml(jobs[5].value);
    let k21=getGold(txt,'21');
    let k24=getGold(txt,'24');
    let k18=k24?Math.round(k24*0.75):(k21?Math.round(k21*(18/21)):0);
    if(!k24 && k21) k24=Math.round(k21*(24/21));
    if(k21 && k24) data.gold={k18,k21,k24}; else errors.push('gold-parse');
  }else errors.push('gold');

  data.updated_at=new Date().toISOString();
  data.error=errors.join(', ');
  return new Response(JSON.stringify(data,null,2),{status:200,headers:{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store, no-cache, must-revalidate, max-age=0','Pragma':'no-cache','Access-Control-Allow-Origin':'*'}});
}


/* MX Fuel: independently check published price references, never invent new prices. */
const FUEL_PRICE_REFERENCES={
  federal:[
    {url:'https://www.dostor.org/5660420',prices:[450,850,1250]},
    {url:'https://www.rudawarabia.net/arabic/categories/news/1367254',prices:[450,850]}
  ],
  erbil:[
    {url:'https://www.kurdistan24.net/ar/story/927400',prices:[750,1000,1200]},
    {url:'https://gov.krd/mnr-ar/activities/news-and-press-releases/2026/july/%D8%AA%D8%AD%D8%AF%D9%8A%D8%AF-%D9%82%D9%8A%D9%85%D8%A9-%D8%A7%D9%84%D8%A8%D9%86%D8%B2%D9%8A%D9%86-%D8%A8-750-%D8%AF%D9%8A%D9%86%D8%A7%D8%B1-%D8%A7-%D8%B9%D9%84%D9%89-%D8%A3%D9%84%D8%A7-%D9%8A%D8%AA%D8%AC%D8%A7%D9%88%D8%B2-%D8%B3%D8%B9%D8%B1%D9%87-%D8%A7%D9%84%D8%AA%D8%AC%D8%A7%D8%B1%D9%8A-850-%D8%AF%D9%8A%D9%86%D8%A7%D8%B1-%D8%A7/',prices:[750,850]}
  ]
};
async function checkFuelReference(reference){
  const controller=new AbortController();
  const timer=setTimeout(()=>controller.abort(),9500);
  try{
    const response=await fetch(reference.url,{
      signal:controller.signal,redirect:'follow',
      headers:{'User-Agent':UA,'Accept-Language':'ar-IQ,ar;q=0.9','Accept':'text/html'},
      cf:{cacheEverything:true,cacheTtl:900}
    });
    if(!response.ok) return null;
    const html=await response.text();
    if(html.length<300) return null;
    const numbers=stripHtml(html).replace(/([0-9])[,،](?=[0-9]{3}(?![0-9]))/g,'$1');
    if(!reference.prices.every(p=>new RegExp('(^|[^0-9])'+p+'([^0-9]|$)').test(numbers)))return null;
    return reference.url;
  }catch(_){return null}
  finally{clearTimeout(timer)}
}
async function fuelReferenceResponse(request,ctx){
  const cache=caches.default;
  const key=new Request(new URL('/api/fuel',request.url).toString(),{method:'GET'});
  const saved=await cache.match(key);
  if(saved)return saved;
  const now=new Date().toISOString();
  const entries=await Promise.all(Object.entries(FUEL_PRICE_REFERENCES).map(async ([region,references])=>{
    const attempts=await Promise.allSettled(references.map(checkFuelReference));
    const match=attempts.find(v=>v.status==='fulfilled' && v.value);
    return [region,{ok:!!match,checked_at:match?now:null,reference_url:match?match.value:null}];
  }));
  const body={attempted_at:now,check_interval_minutes:60,sources:Object.fromEntries(entries)};
  const response=new Response(JSON.stringify(body),{
    status:200,
    headers:{
      'Content-Type':'application/json; charset=utf-8',
      'Cache-Control':'public, max-age=0, s-maxage=3600',
      'Access-Control-Allow-Origin':'*'
    }
  });
  ctx.waitUntil(cache.put(key,response.clone()));
  return response;
}

export default {
  async fetch(request,env,ctx){
    const url=new URL(request.url);

    if(url.pathname==='/beta' || url.pathname==='/beta/' || url.pathname==='/beta.html'){
      if(request.method!=='GET' && request.method!=='HEAD') return new Response('Method Not Allowed',{status:405});
      return betaPageResponse(request,env);
    }

    if(url.pathname==='/api/fuel'){
      if(request.method!=='GET')return new Response('Method Not Allowed',{status:405});
      return fuelReferenceResponse(request,ctx);
    }

    if(url.pathname==='/api/market'){
      if(request.method==='OPTIONS') return new Response(null,{status:204,headers:{'Access-Control-Allow-Origin':'*','Access-Control-Allow-Methods':'GET, OPTIONS','Access-Control-Allow-Headers':'Content-Type'}});
      if(request.method!=='GET') return new Response('Method Not Allowed',{status:405});
      return marketResponse();
    }
    return env.ASSETS.fetch(request);
  }
};
