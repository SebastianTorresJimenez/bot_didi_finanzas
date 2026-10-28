import logging
from datetime import time
import re
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image
import pytesseract
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from apscheduler.schedulers.background import BackgroundScheduler
from database import registrar_transaccion, get_daily_summary, get_weekly_summary, get_monthly_summary

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'

TOKEN = "8984256294:AAF8RNWQtMI-PSCx8KMYyR5l-AwerRv8UOc"
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

    # --- NUEVO: Manejo de los botones de métodos de pago tras el OCR ---
    elif data.startswith("pago_"):
        metodo = data.replace("pago_", "").capitalize()
        monto = context.user_data.get("monto_pendiente", 0)
        
        # Guardar en base de datos con el método de pago elegido
        registrar_transaccion("ingreso", f"Didi ({metodo})", monto)
        context.user_data.clear()

        await query.edit_message_text(
            f"✅ *¡Carrera registrada con éxito!*\n\n"
            f"💵 **Monto:** ${monto:,.0f} COP\n"
            f"💳 **Método de pago:** {metodo}",
            parse_mode="Markdown",
            reply_markup=obtener_menu_principal()
        )

    elif data == "bal_diario":
        total_ingresos, total_gastos, balance_neto, detalles = get_daily_summary()
        
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
        total_ingresos, total_gastos, balance_neto, detalles = get_weekly_summary()
        
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
        total_ingresos, total_gastos, balance_neto, detalles = get_monthly_summary()
        
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
            
            # Mostrar botones de pago también para ingreso manual
            keyboard_pago = [
                [InlineKeyboardButton("💵 Efectivo", callback_data="pago_efectivo"),
                 InlineKeyboardButton("📱 Nequi", callback_data="pago_nequi")],
                [InlineKeyboardButton("💳 Saldo Didi (Tarjeta)", callback_data="pago_tarjeta")]
            ]
            context.user_data.clear()
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
            registrar_transaccion("gasto", categoria, monto)
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

# Procesamiento de imágenes con OCR y despliegue de botones de pago
async def recibir_imagen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global GLOBAL_CHAT_ID
    GLOBAL_CHAT_ID = update.message.chat_id

    status_msg = await update.message.reply_text("🔍 Leyendo captura de pantalla con OCR...")

    photo_file = await update.message.photo[-1].get_file()
    image_path = "temp_capture.jpg"
    await photo_file.download_to_drive(image_path)

    try:
        imagen = Image.open(image_path)
        texto_ocr = pytesseract.image_to_string(imagen, lang='spa')
        
        monto_detectado = None
        duracion_distancia = "No detectada"

        # Extraer duración y distancia si aparecen en la imagen
        match_duracion = re.search(r'(\d+m\s*\d*s?)', texto_ocr)
        match_distancia = re.search(r'(\d+[\.,]?\d*\s*km)', texto_ocr, re.IGNORECASE)
        if match_duracion and match_distancia:
            duracion_distancia = f"{match_duracion.group(1)} / {match_distancia.group(1)}"

        # Buscar el monto principal
        lineas = texto_ocr.split('\n')
        for i, linea in enumerate(lineas):
            if "ganancias" in linea.lower() or "total" in linea.lower() or "tarifa" in linea.lower():
                bloque_a_revisar = linea + " " + (lineas[i+1] if i+1 < len(lineas) else "")
                numeros = re.findall(r'\d{1,3}(?:[.,]\d{3})*|\d+', bloque_a_revisar)
                if numeros:
                    limpio = numeros[-1].replace('.', '').replace(',', '')
                    val = float(limpio)
                    if 3000 <= val <= 500000:
                        monto_detectado = val
                        break

        if not monto_detectado:
            todos_los_numeros = re.findall(r'\d{1,3}(?:[.,]\d{3})*|\d+', texto_ocr)
            for num in todos_los_numeros:
                limpio = num.replace('.', '').replace(',', '')
                if limpio.isdigit():
                    val = float(limpio)
                    if 5000 <= val <= 150000:
                        monto_detectado = val
                        break

        if monto_detectado:
            # Guardamos temporalmente el monto para asignarlo cuando presione el botón de pago
            context.user_data["monto_pendiente"] = monto_detectado

            # Creamos los botones idénticos a tu referencia visual
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

def tarea_reporte_nocturno(application):
    if GLOBAL_CHAT_ID:
        resumen = get_daily_summary()
        texto = "🌙 *Reporte Nocturno Automático (9:00 p.m.)*\n\n"
        if not resumen:
            texto += "No hubo movimientos registrados hoy."
        else:
            for tipo, total in resumen:
                texto += f"- {tipo.capitalize()}: ${total:,.0f}\n"
        
        application.job_queue.run_once(
            lambda ctx: ctx.bot.send_message(chat_id=GLOBAL_CHAT_ID, text=texto, parse_mode="Markdown"),
            when=0
        )

# Mini servidor web para evitar el Timeout en Render
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot DiDi Finanzas is running!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Iniciar el servidor web en un hilo secundario antes de arrancar el bot
threading.Thread(target=run_web_server, daemon=True).start()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(responder_botones))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_texto))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, recibir_imagen))

    scheduler = BackgroundScheduler()
    scheduler.add_job(lambda: tarea_reporte_nocturno(app), 'cron', hour=21, minute=0)
    scheduler.start()

    print("🤖 Bot activo con OCR y botones de métodos de pago configurados...")
    app.run_polling()