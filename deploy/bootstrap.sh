#!/usr/bin/env bash
set -euo pipefail

echo "== 1/6 安装依赖 =="
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip git nginx

echo "== 2/6 拉取代码 =="
rm -rf /opt/CampusEvents
git clone --depth 1 https://github.com/2211kuma/CampusEvents.git /opt/CampusEvents

echo "== 3/6 建虚拟环境 =="
cd /opt/CampusEvents
python3 -m venv venv
venv/bin/pip install -q --upgrade pip
venv/bin/pip install -q flask gunicorn

echo "== 4/6 systemd 服务 =="
cp /opt/CampusEvents/deploy/campusevent.service /etc/systemd/system/campusevent.service
systemctl daemon-reload
systemctl enable --now campusevent

echo "== 5/6 nginx =="
cp /opt/CampusEvents/deploy/nginx-campusevent.conf /etc/nginx/sites-available/campusevent
ln -sf /etc/nginx/sites-available/campusevent /etc/nginx/sites-enabled/campusevent
rm -f /etc/nginx/sites-enabled/default
nginx -t
systemctl reload nginx

echo "== 6/6 自检 =="
sleep 3
systemctl is-active campusevent
curl -s -o /dev/null -w "local_http=%{http_code}\n" http://127.0.0.1:8000/ || true
curl -s -o /dev/null -w "via_nginx=%{http_code}\n" http://127.0.0.1/ || true
echo "DONE"
