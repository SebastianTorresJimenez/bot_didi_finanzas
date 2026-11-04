# database.py - Corrección definitiva para la estabilidad de balances SQLite
import sqlite3
from datetime import datetime, timedelta

def init_db():
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transacciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo TEXT, -- 'ingreso' o 'gasto'
            categoria TEXT, 
            monto REAL,
            fecha TEXT -- Fecha y hora local como texto exacto
        )
    """)
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_transacciones_fecha_tipo "
        "ON transacciones (fecha, tipo)"
    )
    conexion.commit()
    conexion.close()

def registrar_transaccion(tipo, categoria, monto):
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
    hoy = datetime.now().date()
    fecha_hoy = hoy.strftime('%Y-%m-%d')
    fecha_manana = (hoy + timedelta(days=1)).strftime('%Y-%m-%d')
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    # Total Ingresos del día
    cursor.execute("SELECT SUM(monto) FROM transacciones WHERE tipo = 'ingreso' AND fecha >= ? AND fecha < ?", (fecha_hoy, fecha_manana))
    res_ing = cursor.fetchone()
    total_ingresos = res_ing[0] if res_ing and res_ing[0] is not None else 0.0
    
    # Total Gastos del día
    cursor.execute("SELECT SUM(monto) FROM transacciones WHERE tipo = 'gasto' AND fecha >= ? AND fecha < ?", (fecha_hoy, fecha_manana))
    res_gas = cursor.fetchone()
    total_gastos = res_gas[0] if res_gas and res_gas[0] is not None else 0.0
    
    # Detalles agrupados por categoría para hoy
    cursor.execute("SELECT categoria, SUM(monto) FROM transacciones WHERE fecha >= ? AND fecha < ? GROUP BY categoria", (fecha_hoy, fecha_manana))
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

def get_weekly_summary():
    fecha_inicio = (datetime.utcnow().date() - timedelta(days=7)).strftime('%Y-%m-%d')
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    # Usamos string de fecha para los últimos 7 días con formato seguro SUBSTR
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'ingreso' AND fecha >= ?
    """, (fecha_inicio,))
    res_ing = cursor.fetchone()
    total_ingresos = res_ing[0] if res_ing and res_ing[0] is not None else 0.0
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'gasto' AND fecha >= ?
    """, (fecha_inicio,))
    res_gas = cursor.fetchone()
    total_gastos = res_gas[0] if res_gas and res_gas[0] is not None else 0.0
    
    cursor.execute("""
        SELECT categoria, SUM(monto) FROM transacciones 
        WHERE fecha >= ?
        GROUP BY categoria
    """, (fecha_inicio,))
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

def get_monthly_summary():
    inicio_mes = datetime.now().strftime('%Y-%m-01')
    conexion = sqlite3.connect("finanzas_didi.db")
    cursor = conexion.cursor()
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'ingreso' AND fecha >= ?
    """, (inicio_mes,))
    res_ing = cursor.fetchone()
    total_ingresos = res_ing[0] if res_ing and res_ing[0] is not None else 0.0
    
    cursor.execute("""
        SELECT SUM(monto) FROM transacciones 
        WHERE tipo = 'gasto' AND fecha >= ?
    """, (inicio_mes,))
    res_gas = cursor.fetchone()
    total_gastos = res_gas[0] if res_gas and res_gas[0] is not None else 0.0
    
    cursor.execute("""
        SELECT categoria, SUM(monto) FROM transacciones 
        WHERE fecha >= ?
        GROUP BY categoria
    """, (inicio_mes,))
    detalles = cursor.fetchall()
    conexion.close()
    
    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

init_db()