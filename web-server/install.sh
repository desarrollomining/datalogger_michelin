systemctl stop mining-web-server
systemctl disable mining-web-server
rm /etc/systemd/system/mining-web-server.service
systemctl daemon-reload
cp /srv/datalogger_michelin/web-server/mining-web-server.service /etc/systemd/system/mining-web-server.service
systemctl enable mining-web-server
systemctl restart mining-web-server