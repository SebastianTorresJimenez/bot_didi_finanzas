import sqlite3
from datetime import datetime

def init_db():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, -- 'ingreso' o 'gasto'
            categoria TEXT, 
            monto REAL,
            fecha TEXT -- Guardaremos la fecha y hora local como texto exacto
        )
    """)
    conexion.commit()
    conexion.close()

def registrar_transaccion(tipo, categoria, monto):
    # Obtenemos la fecha y hora actual exacta del momento
    fecha_actual = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    cursor.execute(
        "INSERT INTO transacciones (tipo, categoria, monto, fecha) VALUES (?, ?, ?, ?)",
        (tipo, categoria, monto, fecha_actual)
    )
    conexion.commit()
    conexion.close()

def get_daily_summary():
    # Usamos la fecha actual de Python (YYYY-MM-DD) sin depender del servidor UTC
    fecha_hoy = datetime.now().strftime('%Y-%m-%d')
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    cursor.execute("SELECT SUM(monto) FROM transacciones WHERE tipo = 'ingreso' AND DATE(fecha) = ?", (fecha_hoy,))
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT SUM(monto) FROM transacciones WHERE tipo = 'gasto' AND DATE(fecha) = ?", (fecha_hoy,))
    total_gastos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("SELECT categoria, SUM(monto) FROM transacciones WHERE DATE(fecha) = ? GROUP BY categoria", (fecha_hoy,))
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

def get_weekly_summary():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    # Filtramos desde los últimos 7 días con fecha exacta de Python
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'ingreso' AND DATE(fecha) >= DATE('now', '-7 days')
    """)
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'gasto' AND DATE(fecha) >= DATE('now', '-7 days')
    """)
    total_gastos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT categoria, SUM(monto) FROM transacciones 
        WHERE DATE(fecha) >= DATE('now', '-7 days') 
        GROUP BY categoria
    """)
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

def get_monthly_summary():
    # Primer día del mes actual en formato YYYY-MM-01
    inicio_mes = datetime.now().strftime('%Y-%m-01')
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'ingreso' AND DATE(fecha) >= ?
    """, (inicio_mes,))
    total_ingresos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'gasto' AND DATE(fecha) >= ?
    """, (inicio_mes,))
    total_gastos = cursor.fetchone()[0] or 0.0
    
    cursor.execute("""
        SELECT categoria, SUM(monto) FROM transacciones 
        WHERE DATE(fecha) >= ? 
        GROUP BY categoria
    """, (inicio_mes,))
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

init_db()