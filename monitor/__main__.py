import requests
import sys
import os
import subprocess
from datetime import datetime

sys.path.append('/srv/datalogger_michelin/')
from database import models
MAX_DB_SIZE = 400
DATABASE_PATH = "/srv/datalogger_michelin/database/database.db"
DATABASE_BACKUP_PATH = "/srv/datalogger_michelin/database/backup"
DATABASE = models.Database()

def command(orden):
    orden_s=orden.split(' ')
    res=subprocess.check_output(orden_s)
    if res.decode()!='\n' or res.decode()!='':
        print(res.decode())


def check_size_database(path, max_db_size): 
    size_db = file_size(path)
    print(f"Size DB: {size_db} MB")
    if size_db> max_db_size:
        # Restart DB mantaining last 7 days of data 
        DATABASE.manage_old_data(days=7)
        
def file_size(path):
    """
    this function will return the file size in
    """
    if os.path.isfile(path):
        return os.path.getsize(path)/ (1024 * 1024) # Convertir a MB
    
def check_old_database(path):
    try:
        old_databases = os.listdir(path)
        for db in old_databases:
            if "database" in db:
                # 1. GET DB DATETIME
                datetime_str = db[:-3].split("_")[1]
                datetime_db_object = datetime.strptime(datetime_str, '%Y-%m-%d#%H:%M:%S')

                # 2. GET CURRENT DATETIME
                now = datetime.now()
                delta_days = abs((now - datetime_db_object).days)
                print(f"Delta: {delta_days} days")

                # 3. CHECK IF DATABASE IF OLD THAT 10 DAYS
                if delta_days>10:
                    print("DATABASE IS TOO OLD, WILL BE REMOVED")
                    cmd = f"rm {path}/{db}"
                    command(cmd)

    except Exception as ex:
        print(ex)
        

if __name__ == "__main__":
    # 1. CHECK SIZE DB: DELETE AND RESTART DATABASE IF IS TOO LARGE
    check_size_database(path= DATABASE_PATH, max_db_size= MAX_DB_SIZE)

    # 2. CHECK OLD DB's
    check_old_database(path= DATABASE_BACKUP_PATH)