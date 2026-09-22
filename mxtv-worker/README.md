# MX TV Web — Cloudflare Worker

This is the working web edition of MX TV for Xtream servers that use plain HTTP.

## Deploy

Use Cloudflare's **Deploy to Cloudflare** flow, then enter a long random value for `COOKIE_SIGNING_KEY`.

After deployment, open the generated `workers.dev` URL and log in with:

- Server URL
- Username
- Password

The Worker proxies Xtream API calls and HLS/media so an HTTP IPTV provider can work from an HTTPS website.

The browser only keeps the recent server + username list. The active password is carried in a signed HttpOnly session cookie.
