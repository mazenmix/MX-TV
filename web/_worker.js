// MX Dollar market engine: IQWealth public JSON is the only source for FX, currencies and gold.
// Published quote time is retained; request time never replaces original publication.
const SOURCE='https://iraqsm.com';
const UA='Mozilla/5.0 (compatible; MazenmiX/1.0)';
const FX_URL=SOURCE+'/data/fx.json';
const GOLD_URL=SOURCE+'/data/gold.json';
const CURRENCIES_URL=SOURCE+'/data/currencies.json';
function decodeEntities(s){
  return String(s||'').replace(/&nbsp;|&#160;/gi,' ').replace(/&quot;/gi,'"')
    .replace(/&#39;|&apos;/gi,"'").replace(/&lt;/gi,'<').replace(/&gt;/gi,'>')
    .replace(/&amp;/gi,'').replace(/&#x([0-9a-f]+);/gi,(_,h)=>String.fromCodePoint(parseInt(h,16)))
    .replace(/&#([0-9]+);/g,(_,n)=>String.fromCodePoint(parseInt(n,10)));
}
function stripHtml(s){
  return decodeEntities(String(s||'').replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi,' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi,' ')
    .replace(/<br\s*\/?>/gi,' ').replace(/<[^>]*>/g,' '))
    .replace(/[\u200e\u200f]/g,' ').replace(/\s+/g,' ').trim();
}
async function readFeed(url){
  const c=new AbortController();
  const timer=setTimeout(()=>c.abort(),10000);
  try{
    const r=await fetch(url,{signal:c.signal,headers:{Accept:'application/json'},cf:{cacheTtl:60,cacheEverything:true}});
    if(!r.ok)throw Error('IQWealth HTTP '+r.status+' at '+url);
    const d=await r.json();
    if(!d||typeof d!=='object'||d.publisher!=='IQWealth (iraqsm.com)')throw Error('Invalid IQWealth response');
    return d;
  }finally{clearTimeout(timer)}
}
function validUnit(v){return typeof v==='number'&&Number.isFinite(v)&&v>=800&&v<=3500}
function fromGold(feed){
  const result={};
  for(const k of [18,21,24]){
    const entry=(feed?.gramByCarat||[]).find(x=>Number(x.karat)===k);
    const value=Number(entry?.mithqalIqd);
    if(Number.isFinite(value)&&value>100000&&value<3000000)result['k'+k]=Math.round(value);
  }
  return result;
}
async function marketResponse(){
  const results=await Promise.allSettled([readFeed(FX_URL),readFeed(GOLD_URL),readFeed(CURRENCIES_URL)]);
  const fx=results[0].status==='fulfilled'?results[0].value:null;
  const buy=Number(fx?.parallel?.buy),sell=Number(fx?.parallel?.sell);
  const published=fx?.parallel?.publishedAt;
  const ms=Date.parse(published||'');
  if(!validUnit(buy)||!validUnit(sell)||!Number.isFinite(ms)||ms>Date.now()+600000){
    return Response.json({error:'Verified IQWealth quote unavailable; no alternative sources used',source:SOURCE},{
      status:503,headers:{'Cache-Control':'no-store','Access-Control-Allow-Origin':'*'}
    });
  }
  const stale=fx.parallel.stale===true||Date.now()-ms>36*3600000;
  const gold=results[1].status==='fulfilled'?results[1].value:null;
  const cur=results[2].status==='fulfilled'?results[2].value:null;
  const perUsd={USD:1};
  for(const [code,raw] of Object.entries(cur?.perUsd||{})){
    if(/^[A-Z]{3}$/.test(code)&&Number(raw)>0&&Number.isFinite(Number(raw)))perUsd[code]=Number(raw);
  }
  const cbi=Number(fx?.official?.cbi);
  const payload={
    kifah:{buy:Math.round(buy*100),sell:Math.round(sell*100)},
    harithiya:{},kukh:{},kukh_rates:{},gailany:{},hatwan:{},
    gold:fromGold(gold),
    gold_meta:{source:'IQWealth',source_url:SOURCE+'/gold',as_of:gold?.asOf||'',generated_at:gold?.generatedAt||''},
    currencies:{perUsd,asOf:cur?.asOf||'',generatedAt:cur?.generatedAt||'',source:'IQWealth'},
    usd_meta:{source:'IQWealth',source_url:SOURCE+'/fx',published_at:published,
      stale,state:stale?'stale':'current',note:'بورصة الكفاح · IQWealth · سعر البيع',unit:'IQD per 100 USD'},
    cbi:{source:'IQWealth',source_url:SOURCE+'/fx',rates:{USD:validUnit(cbi)?cbi:null},confirmed:fx?.official?.confirmed||null},
    updated_at:new Date().toISOString(),as_of:fx.asOf||null,
    source:'IQWealth',source_url:SOURCE+'/en',attribution:'Data: IQWealth — https://iraqsm.com',
    error:results.slice(1).some(x=>x.status==='rejected')?'Some non-FX IQWealth feeds unavailable':''
  };
  return Response.json(payload,{headers:{'Cache-Control':'no-store','Access-Control-Allow-Origin':'*'}});
}
async function betaPageResponse(request,env){
  // GitHub hosts only the expanded HTML page, not prices. All price calls
  // inside this page go to /api/market, backed solely by IQWealth.
  try{
    const r=await fetch('https://raw.githubusercontent.com/mazenmix/MX-TV/main/web/beta.html?t='+Date.now(),
      {cache:'no-store',headers:{Accept:'text/html','Cache-Control':'no-cache'}});
    if(r.ok){
      const html=await r.text();
      return new Response(html,{status:200,headers:{'Content-Type':'text/html; charset=utf-8',
        'Cache-Control':'no-store, no-cache, must-revalidate, max-age=0'}});
    }
  }catch(_){}
  try{
    const u=new URL(request.url);
    u.pathname='/beta.html';u.search='';
    const r=await env.ASSETS.fetch(new Request(u.toString(),request));
    if(r.ok)return r;
  }catch(_){}
  return new Response('Expanded edition temporarily unavailable',{status:503,headers:{'Cache-Control':'no-store'}});
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
