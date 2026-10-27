import sqlite3

def init_db():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, -- 'ingreso' o 'gasto'
            categoria TEXT, 
            monto REAL,
            fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conexion.commit()
    conexion.close()

def registrar_transaccion(tipo, categoria, monto):
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO transacciones (tipo, categoria, monto) VALUES (?, ?, ?)",
        (tipo, categoria, monto)
    )
    conexion.commit()
    conexion.close()

# Balance Diario (Ya lo tienes)
def get_daily_summary():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    cursor.execute("SELECT SUM(monto) FROM transacciones WHERE tipo = 'ingreso' AND DATE(fecha) = DATE('now', 'localtime')")
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(monto) FROM transacciones WHERE tipo = 'gasto' AND DATE(fecha) = DATE('now', 'localtime')")
    total_gastos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT categoria, SUM(monto) FROM transacciones WHERE DATE(fecha) = DATE('now', 'localtime') GROUP BY categoria")
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

# --- NUEVO: Balance Semanal (filtra desde el lunes de la semana actual) ---
def get_weekly_summary():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    # 'weekday 1' en SQLite calcula el lunes de la semana actual
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'ingreso' AND DATE(fecha) >= DATE('now', 'localtime', 'weekday 1', '-7 days')
    """)
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'gasto' AND DATE(fecha) >= DATE('now', 'localtime', 'weekday 1', '-7 days')
    """)
    total_gastos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT categoria, SUM(monto) FROM transacciones 
        WHERE DATE(fecha) >= DATE('now', 'localtime', 'weekday 1', '-7 days') 
        GROUP BY categoria
    """)
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

# --- NUEVO: Balance Mensual (filtra desde el día 1 del mes actual) ---
def get_monthly_summary():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    # 'start of month' calcula el primer día del mes corriente
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'ingreso' AND DATE(fecha) >= DATE('now', 'localtime', 'start of month')
    """)
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'gasto' AND DATE(fecha) >= DATE('now', 'localtime', 'start of month')
    """)
    total_gastos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT categoria, SUM(monto) FROM transacciones 
        WHERE DATE(fecha) >= DATE('now', 'localtime', 'start of month') 
        GROUP BY categoria
    """)
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

init_db()