systemctl stop mining-autoupload
systemctl disable mining-autoupload
rm /etc/systemd/system/mining-autoupload.service
systemctl daemon-reload