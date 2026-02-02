systemctl stop mining-serial
systemctl disable mining-serial
rm /etc/systemd/system/mining-serial.service
systemctl daemon-reload