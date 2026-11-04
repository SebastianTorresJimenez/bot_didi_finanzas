import asyncio
import logging
import os
import tempfile
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from database import registrar_transaccion, get_daily_summary, get_weekly_summary, get_monthly_summary
from ocr_procesor import extract_didi_trip_info_async
from scheduler_reports import setup_report_scheduler

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

TOKEN = "8827946740:AAEZnOlJziFLbDJMeBaCiARLrClWf3Cu9sI"
GLOBAL_CHAT_ID = None

def obtener_menu_principal():
    keyboard = [
        [InlineKeyboardButton("📥 REGISTRAR INGRESO", callback_data="menu_ingreso")],
        [InlineKeyboardButton("📤 REGISTRAR GASTO", callback_data="menu_gasto")],
        [
            InlineKeyboardButton("📊 Balance Diario", callback_data="bal_diario"),
            InlineKeyboardButton("📅 Semanal", callback_data="bal_semanal"),
            InlineKeyboardButton("📆 Mensual", callback_data="bal_mensual"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GLOBAL_CHAT_ID
    if update.message:
        GLOBAL_CHAT_ID = update.message.chat_id
    elif update.callback_query:
        GLOBAL_CHAT_ID = update.callback_query.message.chat_id

    context.user_data.clear()
    mensaje = (
        "👋 ¡Hola! Bienvenid@ a tu Asistente Financiero para Didi.\n\n"
        "Selecciona una opción o envíame directamente la captura de pantalla de tu viaje para registrar el ingreso automáticamente:"
    )
    if update.message:
        await update.message.reply_text(mensaje, reply_markup=obtener_menu_principal())
    elif update.callback_query:
        await update.callback_query.message.reply_text(mensaje, reply_markup=obtener_menu_principal())

async def responder_botones(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GLOBAL_CHAT_ID
    query = update.callback_query
    
    try:
        await query.answer()
    except Exception as e:
        logging.warning(f"No se pudo responder al callback (posible expiración): {e}")
        return

    GLOBAL_CHAT_ID = query.message.chat_id
    data = query.data

    if data == "menu_ingreso":
        context.user_data["esperando"] = "ingreso_didi"
        await query.edit_message_text(
            "📥 *Registrar Ingreso*\n\nEnvíame la **captura de pantalla** de la carrera de Didi por aquí, o escribe el monto manualmente.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_inicio")]])
        )

    elif data == "menu_gasto":
        keyboard_gastos = [
            [InlineKeyboardButton("⛽ Gasolina", callback_data="gasto_gasolina")],
            [InlineKeyboardButton("🛠️ Mantenimiento / Repuestos", callback_data="gasto_mantenimiento")],
            [InlineKeyboardButton("🥪 Comida / Peajes / Otros", callback_data="gasto_otros")],
            [InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_inicio")]
        ]
        await query.edit_message_text(
            "📤 *Registrar Gasto*\n\nSelecciona el tipo de gasto que realizaste:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard_gastos)
        )

    elif data in ["gasto_gasolina", "gasto_mantenimiento", "gasto_otros"]:
        categoria_map = {
            "gasto_gasolina": "Gasolina",
            "gasto_mantenimiento": "Mantenimiento",
            "gasto_otros": "Otros Gastos"
        }
        cat_elegida = categoria_map[data]
        context.user_data["esperando"] = "monto_gasto"
        context.user_data["categoria_actual"] = cat_elegida

        await query.edit_message_text(
            f"💰 *Registrar Gasto: {cat_elegida}*\n\nEscribe por chat el monto que gastaste (ejemplo: `35000`):",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_inicio")]])
        )

    elif data.startswith("pago_"):
        metodo = data.replace("pago_", "").capitalize()
        monto = context.user_data.get("monto_pendiente", 0)
        
        await asyncio.to_thread(registrar_transaccion, "ingreso", f"Didi ({metodo})", monto)
        context.user_data.clear()

        await query.edit_message_text(
            f"✅ *¡Carrera registrada con éxito!*\n\n"
            f"💵 **Monto:** ${monto:,.0f} COP\n"
            f"💳 **Método de pago:** {metodo}",
            parse_mode="Markdown",
            reply_markup=obtener_menu_principal()
        )

    elif data == "bal_diario":
        total_ingresos, total_gastos, balance_neto, detalles = await asyncio.to_thread(get_daily_summary)
        
        texto_resumen = (
            "📊 *Balance Financiero:*\n\n"
            f"📥 **Total Ingresos:** ${total_ingresos:,.0f} COP\n"
            f"📤 **Total Gastos:** ${total_gastos:,.0f} COP\n"
            f"-----------------------------------\n"
            f"💰 **Balance Neto:** ${balance_neto:,.0f} COP\n\n"
            "📋 *Detalle por categoría:*\n"
        )
        
        if not detalles:
            texto_resumen += "Aún no hay transacciones registradas."
        else:
            for cat, total in detalles:
                texto_resumen += f"- {cat}: ${total:,.0f}\n"

        await query.edit_message_text(
            texto_resumen,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_inicio")]])
        )

    elif data == "bal_semanal":
        total_ingresos, total_gastos, balance_neto, detalles = await asyncio.to_thread(get_weekly_summary)
        
        texto_resumen = (
            "📅 *Balance Semanal (Lunes a Hoy):*\n\n"
            f"📥 **Total Ingresos:** ${total_ingresos:,.0f} COP\n"
            f"📤 **Total Gastos:** ${total_gastos:,.0f} COP\n"
            f"-----------------------------------\n"
            f"💰 **Balance Neto:** ${balance_neto:,.0f} COP\n\n"
            "📋 *Detalle por categoría:*\n"
        )
        
        if not detalles:
            texto_resumen += "Aún no hay transacciones esta semana."
        else:
            for cat, total in detalles:
                texto_resumen += f"- {cat}: ${total:,.0f}\n"

        await query.edit_message_text(
            texto_resumen,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_inicio")]])
        )

    elif data == "bal_mensual":
        total_ingresos, total_gastos, balance_neto, detalles = await asyncio.to_thread(get_monthly_summary)
        
        texto_resumen = (
            "📆 *Balance Mensual (Mes Actual):*\n\n"
            f"📥 **Total Ingresos:** ${total_ingresos:,.0f} COP\n"
            f"📤 **Total Gastos:** ${total_gastos:,.0f} COP\n"
            f"-----------------------------------\n"
            f"💰 **Balance Neto:** ${balance_neto:,.0f} COP\n\n"
            "📋 *Detalle por categoría:*\n"
        )
        
        if not detalles:
            texto_resumen += "Aún no hay transacciones este mes."
        else:
            for cat, total in detalles:
                texto_resumen += f"- {cat}: ${total:,.0f}\n"

        await query.edit_message_text(
            texto_resumen,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Volver al Menú", callback_data="menu_inicio")]])
        )

    elif data == "menu_inicio":
        context.user_data.clear()
        await query.edit_message_text(
            "👋 Menú Principal:\nSelecciona una opción:",
            reply_markup=obtener_menu_principal()
        )

async def manejar_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GLOBAL_CHAT_ID
    GLOBAL_CHAT_ID = update.message.chat_id
    estado = context.user_data.get("esperando")

    if estado == "ingreso_didi":
        texto = update.message.text.strip().replace(".", "").replace(",", "")
        try:
            monto = float(texto)
            context.user_data["monto_pendiente"] = monto
            
            keyboard_pago = [
                [InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
                 InlineKeyboardButton("📱 Nequi", callback_data="pago_nequi")],
                [InlineKeyboardButton("💳 Saldo Didi (Tarjeta)", callback_data="pago_tarjeta")]
            ]
            await update.message.reply_text(
                f"✅ Monto ingresado: *${monto:,.0f} COP*\n\n¿Cómo te pagaron este servicio?",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard_pago)
            )
        except ValueError:
            await update.message.reply_text("⚠️ Por favor, ingresa un número válido para el monto (ejemplo: `120000`).")

    elif estado == "monto_gasto":
        texto = update.message.text.strip().replace(".", "").replace(",", "")
        try:
            monto = float(texto)
            categoria = context.user_data.get("categoria_actual", "Gasto General")
            await asyncio.to_thread(registrar_transaccion, "gasto", categoria, monto)
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ ¡Gasto de *{categoria}* por *${monto:,.0f}* registrado exitosamente!",
                parse_mode="Markdown",
                reply_markup=obtener_menu_principal()
            )
        except ValueError:
            await update.message.reply_text("⚠️ Por favor, ingresa un número válido para el monto (ejemplo: `25000`).")
    else:
        await update.message.reply_text("Usa el comando /start para ver el menú principal.")

async def recibir_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GLOBAL_CHAT_ID
    GLOBAL_CHAT_ID = update.message.chat_id

    status_msg = await update.message.reply_text("🔍 Leyendo captura de pantalla con OCR...")

    image_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as image_file:
            image_path = image_file.name
        photo_file = await update.message.photo[-1].get_file()
        await photo_file.download_to_drive(image_path)

        trip_info = await extract_didi_trip_info_async(image_path)
        monto_detectado = trip_info["net_earnings"]
        duracion_distancia = "No detectada"
        if trip_info["duration"] != "N/A" and trip_info["distance"] != "N/A":
            duracion_distancia = f"{trip_info['duration']} / {trip_info['distance']}"

        if monto_detectado:
            context.user_data["monto_pendiente"] = monto_detectado

            keyboard_pago = [
                [InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
                 InlineKeyboardButton("📱 Nequi", callback_data="pago_nequi")],
                [InlineKeyboardButton("💳 Saldo Didi (Tarjeta)", callback_data="pago_tarjeta")]
            ]

            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text=(
                    "✅ **Carrera Analizada por OCR**\n"
                    f"💵 **Monto:** ${monto_detectado:,.0f} COP\n"
                    f"⏱️ **Duración/Dist:** {duracion_distancia}\n\n"
                    "¿Cómo te pagaron este servicio?"
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard_pago)
            )
        else:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id,
                message_id=status_msg.message_id,
                text="⚠️ No pude detectar automáticamente el monto exacto. Por favor, escribe el valor del ingreso por el chat."
            )
            context.user_data["esperando"] = "ingreso_didi"

    except Exception as e:
        logging.error(f"Error en OCR: {e}")
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id,
            message_id=status_msg.message_id,
            text="❌ Ocurrió un error procesando la imagen. Intenta escribir el monto manualmente."
        )
    finally:
        if image_path and os.path.exists(image_path):
            os.remove(image_path)

# Mini servidor web secundario para mantener vivo el servicio en Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot DiDi Finanzas is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Arrancar el servidor web auxiliar en segundo plano
threading.Thread(target=run_web_server, daemon=True).start()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(responder_botones))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, recibir_imagen))

    setup_report_scheduler(app, lambda: GLOBAL_CHAT_ID)

    print("🤖 Bot activo mediante Polling seguro y con servidor web auxiliar...")
    
    # Arranca el polling limpio descartando sesiones viejas o colgadas
    app.run_polling(drop_pending_updates=True)