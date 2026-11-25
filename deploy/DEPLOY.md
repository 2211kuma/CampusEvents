# 腾讯云部署说明（CVM / 轻量应用服务器通用）

适用：Ubuntu 22.04 / 24.04（对应 Python 3.10 / 3.12，均可用），公网 IP 直接访问（绑定域名需先完成 ICP 备案）。

## 1. 准备

- 控制台安全组放行 **22（SSH）** 与 **80（HTTP）**。
- 本地登录：`ssh root@<公网IP>`（CVM 的 ubuntu 镜像用户可能是 `ubuntu`，需要 `sudo`）。

## 2. 装环境并拉代码

```bash
apt update && apt install -y python3 python3-venv python3-pip git nginx
git clone https://github.com/2211kuma/CampusEvents.git /opt/CampusEvents
cd /opt/CampusEvents && python3 -m venv venv && source venv/bin/activate
pip install flask gunicorn
```

## 3. 先手动试跑

```bash
gunicorn -w 2 -b 127.0.0.1:8000 "app.web:create_app()"
```

另开一个 SSH 窗口：

```bash
curl -I http://127.0.0.1:8000     # 期望 200
```

确认正常后按 Ctrl+C 停掉。

## 4. 配为系统服务

```bash
cp /opt/CampusEvents/deploy/campusevent.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now campusevent
systemctl status campusevent --no-pager
```

日志：`journalctl -u campusevent -f`

## 5. 配 nginx

```bash
cp /opt/CampusEvents/deploy/nginx-campusevent.conf /etc/nginx/sites-available/campusevent
ln -sf /etc/nginx/sites-available/campusevent /etc/nginx/sites-enabled/campusevent
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx
```

浏览器打开 `http://<公网IP>` 即可。

## 6. 更新代码

```bash
cd /opt/CampusEvents && git pull && systemctl restart campusevent
```

## 7. 数据与注意事项

- 数据库自动生成在 `/opt/CampusEvents/data/campusevent.db`，该目录被 `.gitignore` 排除，`git pull` 不会覆盖数据。
- 重置演示数据：`cd /opt/CampusEvents && venv/bin/python seed.py --reset`（会清空已有报名）。
- 免费试用 1 个月，到期前续费，否则实例可能被回收。
- 备案：使用域名访问境内服务器必须 ICP 备案；直接用 IP:80 访问一般可用。
- 演示用途，不建议把 SQLite 放多进程高并发场景；若访问量上来，把 gunicorn 的 `-w 2` 调到 1 或改用 MySQL。
