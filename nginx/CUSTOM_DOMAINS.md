# Portal custom domains (white-label client portal)

TimeTracker can serve the client portal on a per-client hostname
(e.g. `portal.acme.com`) when:

1. **Admin → Settings → Allow portal custom domains** is enabled.
2. The client has **Custom portal domain** set (Clients → Edit).
3. DNS for that hostname points at this TimeTracker host.
4. TLS is terminated (recommended) via a certificate covering the hostname.

## DNS

Create a CNAME (or A record) from the client hostname to your TimeTracker
public hostname, for example:

```text
portal.acme.com.  CNAME  timetracker.example.com.
```

## TLS with certbot (webroot)

Example using the existing nginx HTTP server and webroot challenge:

```bash
certbot certonly --webroot -w /var/www/certbot \
  -d portal.acme.com
```

Then add a server block (or reuse a wildcard cert) that proxies to the
TimeTracker upstream, similar to `https.conf`.

## Example nginx server block

```nginx
server {
    listen 443 ssl http2;
    server_name portal.acme.com;

    ssl_certificate     /etc/letsencrypt/live/portal.acme.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/portal.acme.com/privkey.pem;

    location / {
        proxy_pass http://timetracker_upstream;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

`Host` must be forwarded so TimeTracker can resolve the client by
`custom_domain`.

## Wildcard option

If you control a parent domain (e.g. `*.portal.yourcompany.com`), issue a
wildcard certificate once and map each client's `custom_domain` under that
zone. That avoids per-client certbot runs.
