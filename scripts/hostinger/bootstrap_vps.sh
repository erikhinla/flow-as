#!/usr/bin/env bash
set -euo pipefail

# Bootstrap Ubuntu VPS for FLOW Agent AS.
# Run as root: bash scripts/hostinger/bootstrap_vps.sh

apt-get update
apt-get install -y ca-certificates curl gnupg lsb-release ufw git

install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list >/dev/null

apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable docker
systemctl start docker

# Minimum firewall baseline; tighten source IPs in production.
ufw allow OpenSSH
ufw allow 9000/tcp
ufw allow 9443/tcp
ufw allow 18000/tcp
ufw allow 8080/tcp
ufw allow 50090/tcp
ufw --force enable

echo "VPS bootstrap complete."
