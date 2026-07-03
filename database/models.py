import os
import sys
import sqlite3
import argparse
import traceback
from tabulate import tabulate
from datetime import datetime
import time

sys.path.append('/srv/datalogger_michelin/')
from lib.utils import Utils
from database import tables

class Database(Utils):
    def __init__(self, log_id= "DATABASE" ):
        self.log_id = log_id
        self.database_path = "/srv/datalogger_michelin/database/database.db"
        self.backup_database_path = "/srv/datalogger_michelin/database/backup"

    # Función para verificar la conexión a la base de datos
    def check_database(self):
        #TODO: Add check if file is empty
        """
        Verifica si se puede abrir la base de datos SQLite.

        Args:
            database_path (str): Ruta de la base de datos.

        Returns:
            None
        """
        try:
            if not os.path.isfile(self.database_path):
                with sqlite3.connect(database=self.database_path) as conn:
                    print(f"Opened SQLite database with version {sqlite3.sqlite_version} successfully.")
        except sqlite3.OperationalError as e:
            print("Failed to open database:", e)

    # Función para crear tablas en la base de datos
    def create_tables(self, dict_tables: dict):
        """
        Crea las tablas especificadas en la base de datos si no existen.

        Args:
            dict_tables (dict): Diccionario con las definiciones de las tablas y sus columnas.

        Returns:
            None
        """
        conn = sqlite3.connect(self.database_path)
        c = conn.cursor()

        for table in dict_tables.keys():
            fieldset = []
            for col, definition in dict_tables[table].items():
                fieldset.append("'{0}' {1}".format(col, definition))
            print(fieldset)
            if len(fieldset) > 0:
                query = "CREATE TABLE IF NOT EXISTS {0} ({1})".format(table, ", ".join(fieldset))
                c.execute(query)

        c.close()
        conn.close()

    # Función para reiniciar la base de datos (placeholder)
    def reset_database(self):
        """
        Placeholder para la lógica de reinicio de la base de datos.
        """
        try:
            self.log("REINICIANDO DATABASE")
            # 1. BACKUP DB
            now = datetime.now()
            backup_db_cmd = f"cp {self.database_path} {self.backup_database_path}/database_{now.strftime('%Y-%m-%d#%H:%M:%S')}.db"
            self.command(backup_db_cmd)

            # 2. DELETE DB FILE
            delete_db_cmd = f"sudo rm {self.database_path}"
            self.command(delete_db_cmd)

            # 3. CREATE TABLES
            create_tables_cmd = "python3 /srv/datalogger_michelin/database/models.py --create_database true"
            self.command(create_tables_cmd)
        except:
            self.traceback()
            
    def get_raw_data(self, columns="", condition_column="", limit=10):
        """
        Obtiene datos de la base de datos, con la opción de especificar columnas y un límite.

        Args:
            database_path (str): Ruta de la base de datos.
            columns (str): Columnas personalizadas a seleccionar (por defecto, selecciona todas las relevantes).
            limit (int): Límite de filas a devolver.

        Returns:
            list: Lista de filas obtenidas de la base de datos.
        """
        rows, col_name = None, ""
        try: 
            conn = sqlite3.connect(self.database_path)
            cur = conn.cursor()

            if condition_column:
                query = f"""SELECT id, packet_data, vehicle, wheel, timestamp, datetime FROM raw_data WHERE {condition_column}=0 ORDER BY id DESC LIMIT {limit}"""
            else:
                if columns:
                    query = f"""SELECT id, {columns} FROM raw_data ORDER BY id DESC LIMIT {limit}"""
                else:
                    query = f"""SELECT id, packet_data, vehicle, wheel, timestamp, datetime, uploaded_mining FROM raw_data ORDER BY id DESC LIMIT {limit}"""
            
            print(query)
            cur.execute(query)
            rows = cur.fetchall()
            col_name = [i[0] for i in cur.description]
            conn.close()
        except:
            self.traceback()
        return rows, col_name
    
    def get_processed_data(self, columns="", condition_column="", limit=10):
        """
        Obtiene datos procesados de la base de datos, con la opción de especificar columnas y un límite.

        Args:
            database_path (str): Ruta de la base de datos.
            columns (str): Columnas personalizadas a seleccionar (por defecto, selecciona todas las relevantes).
            limit (int): Límite de filas a devolver.

        Returns:
            list: Lista de filas obtenidas de la base de datos.
        """
        rows, col_name = None, ""
        try:
            conn = sqlite3.connect(self.database_path)
            cur = conn.cursor()

            if condition_column:
                query = f"""SELECT id, packet_data, vehicle, wheel, timestamp, datetime FROM processed_data WHERE {condition_column}=0 ORDER BY id DESC LIMIT {limit}"""
            else:
                if columns:
                    query = f"""SELECT id, {columns} FROM processed_data ORDER BY id DESC LIMIT {limit}"""
                else:
                    query = f"""SELECT id, packet_data, vehicle, wheel, timestamp, datetime, uploaded_mining FROM processed_data ORDER BY id DESC LIMIT {limit}"""

            print(query)
            cur.execute(query)
            rows = cur.fetchall()
            col_name = [i[0] for i in cur.description]
            conn.close()
        except:
            self.traceback()
        return rows, col_name
    
    def get_latest_wheel_data(self, table_type="", vehicle="", wheel=""):
        """
        Busca el ÚLTIMO registro para un vehículo y rueda específicos 
        que tenga MENOS de 24 horas de antigüedad.
        """
        rows, col_name = None, ""
        table = "processed_data" if table_type == "processed" else "raw_data"

        cutoff_timestamp = int(time.time()) - 86400

        try:
            conn = sqlite3.connect(self.database_path)
            cur = conn.cursor()

            query = f"""
                SELECT id, packet_data, vehicle, wheel, timestamp, datetime 
                FROM {table} 
                WHERE vehicle = ? 
                  AND wheel = ? 
                  AND timestamp >= ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            """
            
            cur.execute(query, (vehicle, wheel, cutoff_timestamp))
            rows = cur.fetchall()
            col_name = [i[0] for i in cur.description]
            conn.close()
        except:
            self.traceback()
            
        return rows, col_name
    
    def insert_raw_data(self, packet_data, vehicle, wheel)-> None:
        """_summary_

        Args:
            packet_data (_type_): _description_
            
        """
        try: 
            sql = "insert into raw_data (packet_data, vehicle, wheel, timestamp, datetime) values (?, ?, ?, ?, ?)"
            self.log(sql)
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            now = datetime.now()
            
            cursor.execute(sql,(
                str(packet_data),
                vehicle,
                wheel,
                int(datetime.timestamp(now)),
                now.strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        
        except:
            self.traceback()
        
    def insert_processed_data(self, packet_data, vehicle, wheel)-> None:
        """_summary_

        Args:
            packet_data (_type_): _description_
        """
        try: 
            sql = "insert into processed_data (packet_data, vehicle, wheel, timestamp, datetime) values (?, ?, ?, ?, ?)"
            self.log(sql)
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            now = datetime.now()
            
            cursor.execute(sql,(
                str(packet_data),
                vehicle,
                wheel,
                int(datetime.timestamp(now)),
                now.strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            conn.commit()
            cursor.close()
            conn.close()
        
        except:
            self.traceback()
            
    def update_value(self, table, column_name, ids):
        try: 
            conn = sqlite3.connect(self.database_path)
            cur = conn.cursor()
            sql="update {table} set {column}=1 where id in ({seq})".format(table=table, column=column_name, seq=','.join(['?']*len(ids)))
            cur.execute(sql, tuple(ids))
            conn.commit()
            conn.close()
            print(f"Ids {ids} actualizadas")
            
        except:
            e = sys.exc_info()
            print("Dumping traceback for [%s: %s]" % (str(e[0].__name__), str(e[1])))
            traceback.print_tb(e[2])
    
    def delete_rows(self, column, operator, condition_value, table):
        try:
            conn =  sqlite3.connect(database= self.database_path)
            cur = conn.cursor()
            query = f"""DELETE from {table} where {column} {operator} {condition_value}"""
            cur.execute(query)
            rows = cur.fetchall()
            conn.close()
            return rows
        except:
            self.traceback()
        return rows

    def manage_old_data(self, table, days: int)-> None:
        try:
            conn =  sqlite3.connect(database= self.database_path)
            cur = conn.cursor()
            now = datetime.now()
            cutoff_timestamp = now.timestamp() - (days * 86400) 
            query = f"""SELECT id, timestamp from {table} where timestamp < {cutoff_timestamp}"""
            cur.execute(query)
            rows = cur.fetchall()
            
            if not rows:
                print(f"No old data to delete in {table}.")
                return
            
            delete_query = f"""DELETE from {table} where timestamp < {cutoff_timestamp}"""
            cur.execute(delete_query)
            conn.commit()
            conn.close()
            
        except:
            self.traceback()
            
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gestión de la base de datos del sistema.")
    parser.add_argument('-ct', '--create_database', default=False, help='Crea las tablas en la base de datos.', type=bool)
    parser.add_argument('-rd', '--reset_db', default=False, help='Reinicia y recrea la base de datos.', type=bool)
    parser.add_argument('-gd', '--get_data', default=False, help='Obtiene datos de la base de datos.', type=bool)
    parser.add_argument('-gcd', '--get_custome_data', default="", help='Obtiene columnas personalizadas de la base de datos.', type=str)
    parser.add_argument('-l', '--limit', default=10, help='Límite opcional para la consulta.', type=int)
    args = parser.parse_args()
    
    database = Database()
    if args.create_database:
        database.check_database()
        database.create_tables(dict_tables=tables.TABLES)
    elif args.reset_db:
        database.check_database()
        database.reset_database()
    elif args.get_data:
        rows, col_name = database.get_raw_data(limit=args.limit)
        rows2, col_name2 = database.get_processed_data(limit=args.limit)
        print(tabulate(rows, headers=col_name, tablefmt='psql'))
        print(tabulate(rows2, headers=col_name2, tablefmt='psql'))
    elif args.get_custome_data:
        rows, col_name = database.get_raw_data(columns=args.get_custome_data, limit=args.limit)
        rows2, col_name2 = database.get_processed_data(columns=args.get_custome_data, limit=args.limit)
        print(tabulate(rows, headers=col_name, tablefmt='psql'))
        print(tabulate(rows2, headers=col_name2, tablefmt='psql'))
    else: 
        print("Argumento no válido. Usa --help para ver las opciones disponibles.")