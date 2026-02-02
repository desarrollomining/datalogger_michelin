systemctl stop mining-web-server
systemctl disable mining-web-server
rm /etc/systemd/system/mining-web-server.service
systemctl daemon-reload