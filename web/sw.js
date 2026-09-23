const CACHE='mx-dollar-v19';
const ASSETS=['./manifest.webmanifest','./icon.svg'];

self.addEventListener('install',e=>{
  self.skipWaiting();
});

self.addEventListener('activate',e=>{
  e.waitUntil(
    caches.keys()
      .then(keys=>Promise.all(keys.map(k=>caches.delete(k))))
      .then(()=>self.clients.claim())
  );
});

self.addEventListener('fetch',e=>{
  if(e.request.method!=='GET') return;

  const url=new URL(e.request.url);

  // For the stable V8 page and index, always force a cache-busted network request.
  if(e.request.mode==='navigate' || url.pathname.endsWith('/mx-dollar-live-v8.html') || url.pathname.endsWith('/index.html')){
    e.respondWith((async()=>{
      try{
        const fresh=new URL(e.request.url);
        fresh.searchParams.set('__mxcb',Date.now().toString());
        const r=await fetch(fresh.toString(),{
          cache:'no-store',
          headers:{'Cache-Control':'no-cache'}
        });
        if(r.ok) return r;
      }catch(_){}
      try{
        return await fetch(e.request,{cache:'reload'});
      }catch(_){
        return new Response('<!doctype html><meta charset="utf-8"><body style="background:#070a0f;color:#fff;font-family:sans-serif">MX Dollar: reload required</body>',{headers:{'Content-Type':'text/html; charset=utf-8'}});
      }
    })());
    return;
  }

  // data.json must always be live too.
  if(url.pathname.endsWith('/data.json')){
    e.respondWith(fetch(e.request,{cache:'no-store'}));
    return;
  }

  e.respondWith(fetch(e.request,{cache:'no-store'}).catch(()=>caches.match(e.request)));
});
