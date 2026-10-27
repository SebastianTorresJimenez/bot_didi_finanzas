# scheduler_reports.py - Programación Automática de Reportes Diarios 9:00 PM
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database import get_daily_summary

def setup_report_scheduler(app):
    scheduler = AsyncIOScheduler()
    
    async def send_9pm_report():
        summary = get_daily_summary()
        gross = summary['cash_in'] + summary['nequi_in'] + summary['didi_in']
        total_exp = summary['cash_exp'] + summary['nequi_exp']
        net = gross - total_exp
        pocket_cash = summary['cash_in'] - summary['cash_exp']
        
        report_msg = (
            "🌙 **Resumen del Día - 9:00 PM**\n\n"
            "📥 **Ingresos Brutos:**\n"
            f"💵 Efectivo recaudado: ${summary['cash_in']:,.0f}\n"
            f"📲 Nequi: ${summary['nequi_in']:,.0f}\n"
            f"💳 Saldo Didi: ${summary['didi_in']:,.0f}\n"
            f"💰 **Total Ingresos:** ${gross:,.0f}\n\n"
            "📤 **Gastos del Día:**\n"
            f"⛽ Pagado en Cash: -${summary['cash_exp']:,.0f}\n"
            f"📲 Pagado en Nequi: -${summary['nequi_exp']:,.0f}\n\n"
            "-----------------------------------\n"
            f"📈 **GANANCIA NETA REAL:** **${net:,.0f}**\n"
            f"👛 **Efectivo Físico en Bolsillo:** ${pocket_cash:,.0f}"
        )
        # Reemplazar con tu CHAT_ID personal de Telegram
        USER_CHAT_ID = 123456789 
        await app.bot.send_message(chat_id=USER_CHAT_ID, text=report_msg, parse_mode="Markdown")

    # Ejecutar todos los días a las 21:00 (9:00 PM)
    scheduler.add_job(send_9pm_report, 'cron', hour=21, minute=0)
    scheduler.start()