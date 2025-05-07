import sqlite3

# Crear/Conectar a la base de datos SQLite
conn = sqlite3.connect('users_db.sqlite')  # Esto creará el archivo 'users_db.sqlite' si no existe

# Crear un cursor para interactuar con la base de datos
cursor = conn.cursor()

# Crear la tabla 'users' si no existe
cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                     email TEXT PRIMARY KEY,
                     password TEXT)''')

# Confirmar los cambios y cerrar la conexión
conn.commit()
conn.close()

print("Base de datos y tabla 'users' creadas exitosamente.")