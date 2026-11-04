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

def _get_summary_for_range(fecha_inicio, fecha_fin):
    conexion = sqlite3.connect("finanzas_didi.db")
    try:
        cursor = conexion.cursor()
        cursor.execute("BEGIN")
        cursor.execute(
            """
            SELECT
                COALESCE(SUM(CASE WHEN tipo = 'ingreso' THEN monto ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN tipo = 'gasto' THEN monto ELSE 0 END), 0)
            FROM transacciones
            WHERE fecha >= ? AND fecha < ?
            """,
            (fecha_inicio, fecha_fin)
        )
        total_ingresos, total_gastos = cursor.fetchone()
        cursor.execute(
            """
            SELECT categoria, SUM(monto)
            FROM transacciones
            WHERE fecha >= ? AND fecha < ?
            GROUP BY categoria
            ORDER BY categoria
            """,
            (fecha_inicio, fecha_fin)
        )
        detalles = cursor.fetchall()
    finally:
        conexion.close()

    balance_neto = total_ingresos - total_gastos
    return total_ingresos, total_gastos, balance_neto, detalles

def get_daily_summary():
    hoy = datetime.now().date()
    fecha_inicio = hoy.strftime('%Y-%m-%d')
    fecha_fin = (hoy + timedelta(days=1)).strftime('%Y-%m-%d')
    return _get_summary_for_range(fecha_inicio, fecha_fin)

def get_weekly_summary():
    hoy = datetime.now().date()
    lunes = hoy - timedelta(days=hoy.weekday())
    fecha_inicio = lunes.strftime('%Y-%m-%d')
    fecha_fin = (hoy + timedelta(days=1)).strftime('%Y-%m-%d')
    return _get_summary_for_range(fecha_inicio, fecha_fin)

def get_monthly_summary():
    hoy = datetime.now().date()
    inicio_mes = hoy.replace(day=1)
    fecha_inicio = inicio_mes.strftime('%Y-%m-%d')
    fecha_fin = (hoy + timedelta(days=1)).strftime('%Y-%m-%d')
    return _get_summary_for_range(fecha_inicio, fecha_fin)

init_db()