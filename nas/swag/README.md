# Home network names

Short names for the services and devices at home. Type `photos.lan` and the browser lands on
`https://photos.bernat-nas.duckdns.org`, which the SWAG container on the NAS serves with its Let's Encrypt wildcard
certificate. No device needs a custom certificate installed. `home.lan` lists every service.

The files mirror SWAG's `/config` directory:

- `nginx/proxy-confs/local-lan.subdomain.conf` redirects `name.lan` to the duckdns name and proxies each site to its
  device.
- `nginx/lan.conf` restricts those sites to the Trusted network (10.2.0.0/24), because port 443 is forwarded from the
  internet.
- `www/home/index.html` is the start page.

Devices without a login of their own (Wall Connector, printer, Presence, AT&T gateway) never sit behind the
internet-facing listener. Their `.lan` name redirects to the device's own address over port 80, which is not forwarded.

## Adding a name

1. Only for a service with its own login: add a `server` block for `name.bernat-nas.duckdns.org` to
   `local-lan.subdomain.conf`. For anything else, add a port 80 redirect to its own address instead.
2. In UniFi, add a DNS Host (A) record for `name.lan` pointing at the NAS (10.2.0.213), plus one for
   `name.bernat-nas.duckdns.org` when the service sits behind SWAG.
3. Add a card to `index.html`.
4. Copy the changed files into the container and run `nginx -t && nginx -s reload` there.

## Pitfalls

- Do not refuse the gateway's address (10.2.0.1). Browsers using DNS-over-HTTPS, Firefox by default, get the public
  address and loop back through the gateway, so they arrive from there.
- A `.lan` redirect must stay a 302. Browsers cache a 301 indefinitely, so changing its target later breaks the name on
  every device that saw the old one.
- Home Assistant answers 400 when a proxy it does not trust sends `X-Forwarded-For`, so its block skips SWAG's
  `proxy.conf`.
- Glances rejects any `Host` header but its own address, and the duplicate `Host` that `proxy.conf` would add.
