# Nginx configuration for a public domain (e.g. timetracker.techteam.ddns.net)

To expose TimeTracker at a public URL so that **both the web UI and the mobile app** work, nginx must proxy **all** paths (including `/api/v1/`) to the app. A single `location /` block is enough; do not proxy only `/` and leave `/api/` elsewhere or unproxied.

---

## Option A: Nginx inside Docker (project’s `docker-compose`)

The repo’s `nginx/conf.d/https.conf` already proxies everything to the app. Use it as-is, or copy and adapt for your domain.

1. **Use the existing config**  
   With the default `server_name _;`, the container accepts any host. Ensure ports 80/443 are published and that no other nginx (or proxy) in front is only forwarding some paths.

2. **Optional: restrict to your domain**  
   In `nginx/conf.d/https.conf`, set:
   ```nginx
   server_name timetracker.techteam.ddns.net;
   ```
   Ensure the TLS certificate (in `nginx/ssl/`) is valid for that hostname (e.g. Let’s Encrypt or your CA).

3. **Ensure this nginx is the one receiving traffic**  
   If another reverse proxy (host nginx, Traefik, etc.) sits in front, it must forward **all** paths for this host to the TimeTracker nginx (or directly to the app), not only `/`.

---

## Option B: Nginx on the host (or main reverse proxy)

If nginx runs **on the host** (or as the main reverse proxy) and the TimeTracker app is in Docker on the same machine (e.g. listening on `127.0.0.1:8080` or a published port), use a server block like this. Replace the upstream address if your app is elsewhere.

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name timetracker.techteam.ddns.net;
    return 308 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name timetracker.techteam.ddns.net;

    # TLS (use your certs; e.g. Let's Encrypt with certbot)
    ssl_certificate     /etc/letsencrypt/live/timetracker.techteam.ddns.net/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/timetracker.techteam.ddns.net/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    client_max_body_size 10M;

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Proxy ALL paths to the app (web UI + /api/v1/ for mobile)
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass_request_headers on;
        proxy_cookie_path / /;
    }

    # WebSockets (Socket.IO)
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8080/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $http_host;
        proxy_set_header X-Forwarded-Host $http_host;
        proxy_set_header X-Forwarded-Port $server_port;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
        proxy_send_timeout 600s;
        proxy_buffering off;
    }
}
```

- If the app runs in Docker and **only** the app container exposes port 8080 on the host, use `proxy_pass http://127.0.0.1:8080;` (or the port you publish in `docker-compose`).
- If nginx is in the **same Docker network** as the app container (e.g. both in one compose), use `proxy_pass http://app:8080;` instead of `127.0.0.1:8080`.

---

## Why the mobile app was getting 404

The Android app calls `https://timetracker.techteam.ddns.net/api/v1/auth/login`. If that returns 404, the request is either:

1. **Not reaching the TimeTracker app**  
   Another nginx (or proxy) in front is only forwarding certain paths (e.g. `/` or `/timetracker/`) and not `/api/v1/`. Fix: ensure the proxy that handles `timetracker.techteam.ddns.net` forwards **all** paths to the app (one `location /` as above).

2. **App behind a subpath**  
   If the web UI is at `https://timetracker.techteam.ddns.net/timetracker/`, the proxy might be stripping the prefix for the backend; the app still sees `/api/v1/...` and the config above is correct. The mobile app must then use the same base URL including the path: `https://timetracker.techteam.ddns.net/timetracker`.

Using the config above (one `location /` proxying to the app) and ensuring no other proxy limits paths should resolve the 404 for `/api/v1/auth/login`.
