#!/bin/bash
# Запускати ПІСЛЯ того, як Cloudflare став активним і api.prodachen.pp.ua
# відкривається через проксі (оранжева хмарка). Запуск: bash deploy/cloudflare.sh
#  1) порти 80/443 відкриті лише для адрес Cloudflare;
#  2) nginx бачить справжній IP відвідувача (знадобиться fail2ban у лабі 10).
set -e

V4=$(curl -fsS https://www.cloudflare.com/ips-v4)
V6=$(curl -fsS https://www.cloudflare.com/ips-v6)
if [ -z "$V4" ]; then echo "не вдалося отримати список IP Cloudflare"; exit 1; fi

echo "== фаєрвол: 80/443 лише від Cloudflare"
sudo ufw delete allow 'Nginx Full' || true
for ip in $V4 $V6; do
    sudo ufw allow proto tcp from "$ip" to any port 80,443 comment cloudflare > /dev/null
done
sudo ufw status | head -n 12
echo "..."

echo "== nginx: справжній IP відвідувача"
{
    echo "# згенеровано deploy/cloudflare.sh"
    for ip in $V4 $V6; do echo "set_real_ip_from $ip;"; done
    echo "real_ip_header CF-Connecting-IP;"
} | sudo tee /etc/nginx/conf.d/cloudflare-realip.conf > /dev/null
sudo nginx -t
sudo systemctl reload nginx
echo "ГОТОВО"
