# scheduler_reports.py - Programación Automática de Reportes Diarios 9:00 PM
import asyncio
from datetime import time
from database import get_daily_summary

def setup_report_scheduler(app, get_chat_id):
    
    async def send_9pm_report(context):
        chat_id = get_chat_id()
        if chat_id is None:
            return

        total_income, total_expenses, net, details = await asyncio.to_thread(
            get_daily_summary
        )
        category_details = "\n".join(
            f"- {category}: ${total:,.0f}" for category, total in details
        ) or "Sin movimientos registrados."
        
        report_msg = (
            "🌙 *Resumen del Día - 9:00 PM*\n\n"
            f"📥 *Total ingresos:* ${total_income:,.0f}\n"
            f"📤 *Total gastos:* ${total_expenses:,.0f}\n\n"
            "📋 *Detalle por categoría:*\n"
            f"{category_details}\n\n"
            f"📈 *Balance neto:* ${net:,.0f}"
        )
        await context.bot.send_message(
            chat_id=chat_id,
            text=report_msg,
            parse_mode="Markdown"
        )

    app.job_queue.run_daily(send_9pm_report, time=time(hour=21))