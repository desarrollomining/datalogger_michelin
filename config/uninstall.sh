systemctl stop mining-config
systemctl disable mining-config
rm /etc/systemd/system/mining-config.service
systemctl daemon-reload