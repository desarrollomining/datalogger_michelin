systemctl stop mining-config
systemctl disable mining-config
rm /etc/systemd/system/mining-config.service
systemctl daemon-reload
cp /srv/datalogger_michelin/config/mining-config.service /etc/systemd/system/mining-config.service
systemctl enable mining-config
systemctl restart mining-config
