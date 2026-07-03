systemctl stop mining-autoupload
systemctl disable mining-autoupload
rm /etc/systemd/system/mining-autoupload.service
systemctl daemon-reload
cp /srv/datalogger_michelin/autoupload/mining-autoupload.service /etc/systemd/system/mining-autoupload.service
systemctl enable mining-autoupload
systemctl restart mining-autoupload
