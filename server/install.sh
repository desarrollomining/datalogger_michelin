systemctl stop mining-server
systemctl disable mining-server
rm /etc/systemd/system/mining-server.service
systemctl daemon-reload
cp /srv/datalogger_michelin/server/mining-server.service /etc/systemd/system/mining-server.service
systemctl enable mining-server
systemctl restart mining-server