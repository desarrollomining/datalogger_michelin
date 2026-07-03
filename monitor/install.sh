systemctl stop mining-monitor
systemctl disable mining-monitor
rm /etc/systemd/system/mining-monitor.service
systemctl daemon-reload
cp /srv/datalogger_michelin/monitor/mining-monitor.service /etc/systemd/system/mining-monitor.service
systemctl enable mining-monitor
systemctl restart mining-monitor
