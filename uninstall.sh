cd /srv/datalogger_michelin
for service in autoupload commands config monitor server web-server
do 
    cd $service
    sh uninstall.sh
    cd ..
done

# Eliminar alguna base de datos antigua
sudo rm /srv/datalogger_michelin/database/database.db