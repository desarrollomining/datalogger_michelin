#UMBRAL
echo 'Actualizando comando UMBRAL'
cp /srv/datalogger_michelin/commands/umbral /bin/umbral
sudo chmod 777 /bin/umbral
echo 'Comando UMBRAL actualizado'

#SENSORES
echo 'Actualizando comando NUMERO_SENSORES'
cp /srv/datalogger_michelin/commands/numero_sensores /bin/numero_sensores
sudo chmod 777 /bin/numero_sensores
echo 'Comando NUMERO_SENSORES actualizado'