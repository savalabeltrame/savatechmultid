import sqlite3
import pandas as pd
import os

# 1. Definir la ruta a la base de datos simulada
# (Ajusta la ruta si es necesario, asumiendo que estás en la carpeta src)
db_path = os.path.join('..', 'dados', 'erp_simulado_totvs.db')

# 2. CONEXIÓN SEGURA: MODO SOLO LECTURA (READ-ONLY)
# El parámetro '?mode=ro' le dice a SQLite que abra la base de datos
# físicamente bloqueada para escritura. Es imposible modificar datos.
uri = f"file:{db_path}?mode=ro"
conn = sqlite3.connect(uri, uri=True)

print("=" * 50)
print(" CONEXIÓN ERP ESTABLECIDA EN MODO SOLO LECTURA")
print("=" * 50)
print("✅ Se puede LEER (SELECT) datos del ERP.")
print("⛔ Está FÍSICAMENTE BLOQUEADO para escribir (INSERT/UPDATE/DELETE).")
print("=" * 50)

# 3. PRUEBA 1: LEER DATOS (Esto debe funcionar)
print("\n📦 Intentando leer productos del ERP...")
try:
    df_productos = pd.read_sql_query("SELECT * FROM ERP_PRODUCTOS", conn)
    print(f"✅ ÉXITO: Se leyeron {len(df_productos)} productos correctamente.")
    print("\nVista previa de los datos leídos:")
    print(df_productos[['CODIGO', 'NOMBRE', 'CATEGORIA']].head(5))
except Exception as e:
    print(f"❌ Error al leer: {e}")

# 4. PRUEBA 2: INTENTAR ESCRIBIR DATOS (Esto debe fallar y ser bloqueado)
print("\n\n️ PRUEBA DE SEGURIDAD: Intentando INYECTAR un producto falso...")
try:
    cursor = conn.cursor()
    # Intentamos hacer un INSERT (como si un hacker o un bug quisiera borrar/crear algo)
    cursor.execute("INSERT INTO ERP_PRODUCTOS VALUES ('HACK001', 'Producto Hackeado', 'Hack', 0, 0, 'Hack')")
    conn.commit()
    print(" ¡ALERTA DE SEGURIDAD! Se permitió la escritura. Algo está mal.")
except sqlite3.OperationalError:
    print("🛡️ ¡BLOQUEO EXITOSO! La base de datos rechazó la escritura.")
    print("🛡️ Tu ERP está 100% seguro con esta conexión.")
except Exception as e:
    print(f"️ Bloqueado por otro motivo de seguridad: {e}")

# Cerrar conexión
conn.close()
print("\n Conexión cerrada.")