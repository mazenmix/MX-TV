const CACHE='mx-dollar-v21';

self.addEventListener('install',event=>{
  self.skipWaiting();
});

self.addEventListener('activate',event=>{
  event.waitUntil((async()=>{
    const keys=await caches.keys();
    await Promise.all(keys.map(key=>caches.delete(key)));
    await self.clients.claim();
  })());
});

// Intentionally no fetch handler.
// Safari rejects navigations when a service worker responds with a redirected Response.
// Let the browser/Cloudflare handle all page and API requests directly.
