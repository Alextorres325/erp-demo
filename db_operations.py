import sqlite3
import hashlib
from datetime import date

# Función para hashear contraseñas
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Conexión a la base de datos SQLite
def get_db_connection():
    conn = sqlite3.connect('erp.db')
    return conn

# Crear la tabla de usuarios si no existe
def create_users_table():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Verificar si el usuario existe
def verify_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT password FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()

    if row:
        stored_password = row[0]
        return stored_password == hash_password(password)
    return False

# Crear un nuevo usuario
def add_user(email, password):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Verificar si el usuario ya existe
    cursor.execute('SELECT email FROM users WHERE email = ?', (email,))
    if cursor.fetchone():
        conn.close()
        return False  # El correo ya existe

    hashed_password = hash_password(password)
    cursor.execute('INSERT INTO users (email, password) VALUES (?, ?)', (email, hashed_password))
    conn.commit()
    conn.close()
    return True

# Crear tablas de órdenes de compra y productos
def create_purchase_tables():
    conn = get_db_connection()
    c = conn.cursor()

    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT,
            request_by TEXT,
            request_date TEXT,
            request_approval TEXT,
            supplier TEXT,
            area TEXT,
            category TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS purchase_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            product TEXT,
            quantity INTEGER,
            unit_cost REAL,
            taxes TEXT,
            total REAL,
            FOREIGN KEY(order_id) REFERENCES purchase_orders(id)
        )
    ''')

    conn.commit()
    conn.close()

# Guardar orden de compra con validación y conversión de datos
def save_purchase_order(request_by, request_date, approval_to, supplier, area, category, product_entries):
    conn = get_db_connection()
    cursor = conn.cursor()

    # Asegurar formato de fecha como texto ISO
    if isinstance(request_date, date):
        request_date = request_date.isoformat()
    elif isinstance(request_date, str):
        try:
            request_date_clean = request_date.replace(" ", "")
            equest_date = date.fromisoformat(request_date_clean).isoformat()
        except Exception:
            raise ValueError(f"Fecha inválida: {request_date}")

    # Insertar encabezado de orden
    cursor.execute('''
        INSERT INTO purchase_orders (request_by, request_date, request_approval, supplier, area, category)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (request_by, request_date, approval_to, supplier, area, category))

    order_id = cursor.lastrowid  # ID de la orden insertada

    # Insertar productos
    for item in product_entries:
        try:
            product = item['product']
            quantity = int(item['quantity'])
            unit_cost = float(str(item['unit_cost']).replace("$", "").replace(",", "").strip())
            tax = item.get('tax', '0%')
            total = item.get('total')

            if isinstance(total, str):
                total = float(total.replace("$", "").replace(",", "").strip())
            elif total is None:
                total = quantity * unit_cost * (1.16 if "16" in tax else 1.0)

            cursor.execute('''
                INSERT INTO purchase_items (order_id, product, quantity, unit_cost, taxes, total)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                order_id,
                product,
                quantity,
                unit_cost,
                tax,
                total
            ))
        except Exception as e:
            print("Error al insertar producto:", item)
            raise e

    conn.commit()
    conn.close()