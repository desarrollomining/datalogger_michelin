systemctl stop mining-server
systemctl disable mining-server
rm /etc/systemd/system/mining-server.service
systemctl daemon-reload