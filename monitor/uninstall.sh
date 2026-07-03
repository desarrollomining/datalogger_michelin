systemctl stop mining-monitor
systemctl disable mining-monitor
rm /etc/systemd/system/mining-monitor.service
systemctl daemon-reload

