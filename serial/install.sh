systemctl stop mining-serial
systemctl disable mining-serial
rm /etc/systemd/system/mining-serial.service
systemctl daemon-reload
cp /srv/datalogger_michelin/serial/mining-serial.service /etc/systemd/system/mining-serial.service
systemctl enable mining-serial
systemctl restart mining-serial