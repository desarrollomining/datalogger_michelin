# Definición de las tablas de la base de datos
# TODO: AGREGAR NUEVA COLUMNA
TABLES = {
    'raw_data': {
        'id'             : 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'packet_data'    : 'TEXT',
        'vehicle'        : 'TEXT',
        'wheel'          : 'TEXT',
        'timestamp'      : 'INTEGER',
        'datetime'       : 'DATETIME',
        'uploaded_mining': 'INTEGER NOT NULL DEFAULT 0',
    },
    'processed_data':{
        'id'            : 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'packet_data'   : 'TEXT',
        'vehicle'       : 'TEXT',
        'wheel'         : 'TEXT',
        'timestamp'     : 'INTEGER',
        'datetime'      : 'DATETIME',
        'uploaded'      : 'INTEGER NOT NULL DEFAULT 0'
    }
}