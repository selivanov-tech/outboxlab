# Dev image for apps/web — Caddy serving placeholder until Next.js scaffold lands.
FROM caddy:2.9-alpine

WORKDIR /srv

COPY apps/web/index.html /srv/index.html

# Step 4: replace with Next.js dev server.
CMD ["caddy", "file-server", "--root", "/srv", "--listen", ":3000"]
