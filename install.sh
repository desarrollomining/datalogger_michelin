# Eliminar alguna base de datos antigua
sudo rm /srv/datalogger_michelin/database/database.db
# Crearla nuevamente
python3 /srv/datalogger_michelin/database/models.py --create_database true

cd /srv/datalogger_michelin
for service in autoupload commands config monitor server web-server
do 
    cd $service
    sh install.sh
    cd ..
done 
