import sqlite3
import random
from datetime import datetime, timedelta

def crear_erp_simulado():
    # Conectar a la base de datos (se creará si no existe)
    conn = sqlite3.connect('../dados/erp_simulado_totvs.db')
    cursor = conn.cursor()

    # 1. Tabla de Productos (Simula la tabla SB1 de TOTVS)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ERP_PRODUCTOS (
            CODIGO VARCHAR(20) PRIMARY KEY,
            NOMBRE VARCHAR(100),
            CATEGORIA VARCHAR(50),
            PRECIO_COSTO REAL,
            PRECIO_VENTA REAL,
            PROVEEDOR VARCHAR(50)
        )
    ''')

    # 2. Tabla de Saldos de Stock (Simula la tabla SB2)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ERP_STOCK (
            CODIGO VARCHAR(20),
            ALMACEN VARCHAR(10),
            CANTIDAD_SISTEMA REAL,
            ULTIMA_ACTUALIZACION DATETIME,
            PRIMARY KEY (CODIGO, ALMACEN)
        )
    ''')

    # 3. Tabla de Movimientos/Entradas (Simula la tabla SD1 - Notas Fiscales de Entrada)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ERP_MOVIMIENTOS (
            ID_MOVIMIENTO INTEGER PRIMARY KEY AUTOINCREMENT,
            CODIGO VARCHAR(20),
            TIPO VARCHAR(10), -- 'ENTRADA' o 'SALIDA'
            CANTIDAD REAL,
            FECHA DATETIME,
            NOTA_FISCAL VARCHAR(20)
        )
    ''')

    # Datos ficticios realistas
    productos = [
        ('7891000100101', 'Leche Entera 1L', 'Lacteos', 3.50, 5.99, 'Parmalat'),
        ('7891000100102', 'Cafe Molido 500g', 'Abarrotes', 8.00, 14.90, 'Pilao'),
        ('7891000100103', 'Arroz Tipo 1 5kg', 'Abarrotes', 15.00, 24.90, 'Tio Joao'),
        ('7891000100104', 'Frijol Negro 1kg', 'Abarrotes', 6.00, 9.90, 'Camil'),
        ('7891000100105', 'Aceite de Soya 900ml', 'Abarrotes', 4.50, 7.99, 'Liza'),
        ('7891000100106', 'Azucar Refinado 1kg', 'Abarrotes', 3.00, 4.99, 'Uniao'),
        ('7891000100107', 'Harina de Trigo 1kg', 'Abarrotes', 3.50, 5.50, 'Dona Benta'),
        ('7891000100108', 'Galleta Maria 400g', 'Galletas', 2.50, 4.50, 'Bauducco'),
        ('7891000100109', 'Jabon en Polvo 1kg', 'Limpieza', 12.00, 19.90, 'Omo'),
        ('7891000100110', 'Detergente Liquido 500ml', 'Limpieza', 2.00, 3.50, 'Ype'),
        ('7891000100111', 'Papel Higienico 12 rollos', 'Higiene', 10.00, 18.90, 'Neve'),
        ('7891000100112', 'Shampoo 400ml', 'Higiene', 9.00, 16.90, 'Pantene'),
        ('7891000100113', 'Cerveza Lata 350ml', 'Bebidas', 2.50, 4.50, 'Brahma'),
        ('7891000100114', 'Refresco 2L', 'Bebidas', 5.00, 8.90, 'Coca Cola'),
        ('7891000100115', 'Jugo de Naranja 1L', 'Bebidas', 4.00, 7.50, 'Del Valle')
    ]

    # Insertar productos
    cursor.executemany('INSERT OR IGNORE INTO ERP_PRODUCTOS VALUES (?,?,?,?,?,?)', productos)

    # Insertar saldos de stock (simulando un inventario real)
    stock_data = []
    for cod, nom, cat, pc, pv, prov in productos:
        # Cantidad aleatoria entre 10 y 500
        cantidad = random.uniform(10, 500)
        fecha = datetime.now() - timedelta(days=random.randint(0, 5))
        stock_data.append((cod, 'ALM01', round(cantidad, 2), fecha))
    
    cursor.executemany('INSERT OR IGNORE INTO ERP_STOCK VALUES (?,?,?,?)', stock_data)

    # Insertar movimientos recientes (simulando ventas y compras de la semana)
    movimientos = []
    for i in range(50):
        cod = random.choice(productos)[0]
        tipo = random.choice(['ENTRADA', 'SALIDA'])
        cant = random.uniform(1, 50)
        fecha = datetime.now() - timedelta(hours=random.randint(1, 168))
        nf = f'NF-{random.randint(10000, 99999)}'
        movimientos.append((cod, tipo, round(cant, 2), fecha, nf))

    cursor.executemany('INSERT INTO ERP_MOVIMIENTOS (CODIGO, TIPO, CANTIDAD, FECHA, NOTA_FISCAL) VALUES (?,?,?,?,?)', movimientos)

    conn.commit()
    conn.close()
    print("✅ Base de datos 'erp_simulado_totvs.db' creada exitosamente en la carpeta 'dados'.")

if __name__ == '__main__':
    crear_erp_simulado()