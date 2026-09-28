#!/bin/bash
set -euo pipefail
cd /root/yuanze-deploy-20260923
# Verify the vendor binary before installation.
grep ' caddy_2.11.4_linux_amd64.tar.gz$' caddy_2.11.4_checksums.txt | sha512sum --check --strict
if ! id yuanze >/dev/null 2>&1; then useradd --system --home-dir /var/lib/yuanze-reference --shell /sbin/nologin yuanze; fi
if ! id yuanze-web >/dev/null 2>&1; then useradd --system --home-dir /var/lib/yuanze-web --shell /sbin/nologin yuanze-web; fi
install -d -m 750 -o root -g yuanze /opt/yuanze-reference /opt/yuanze-reference/releases
release=/opt/yuanze-reference/releases/20260923-reference-v1
if [ -e "$release" ]; then echo 'Release path already exists; stopping safely.'; exit 1; fi
install -d -m 750 -o root -g yuanze "$release"
tar -xzf yuanze-reference-20260923.tar.gz -C "$release"
# The final reviewed server replaces the archived draft.
install -m 640 -o root -g yuanze server.py "$release/server.py"
chown -R root:yuanze "$release"
find "$release" -type d -exec chmod 750 {} +
find "$release" -type f -exec chmod 640 {} +
install -d -m 700 -o yuanze -g yuanze /var/lib/yuanze-reference
if [ ! -e /var/lib/yuanze-reference/auth.json ]; then install -m 600 -o yuanze -g yuanze reference-auth.json /var/lib/yuanze-reference/auth.json; fi
install -d -m 700 -o yuanze-web -g yuanze-web /var/lib/yuanze-web
install -d -m 755 /etc/yuanze-reference
install -m 644 "$release/deploy/Caddyfile" /etc/yuanze-reference/Caddyfile
install -m 644 "$release/deploy/yuanze-reference.service" /etc/systemd/system/yuanze-reference.service
install -m 644 "$release/deploy/yuanze-web.service" /etc/systemd/system/yuanze-web.service
tar -xzf caddy_2.11.4_linux_amd64.tar.gz caddy
install -m 755 caddy /usr/local/bin/yuanze-caddy
/usr/local/bin/yuanze-caddy validate --config /etc/yuanze-reference/Caddyfile --adapter caddyfile
if [ -L /opt/yuanze-reference/current ]; then readlink /opt/yuanze-reference/current > previous-release.txt; fi
ln -sfn "$release" /opt/yuanze-reference/current
systemctl daemon-reload
systemctl enable --now yuanze-reference.service yuanze-web.service
systemctl is-active yuanze-reference.service yuanze-web.service
