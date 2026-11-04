# ocr_processor.py - Procesamiento de Imágenes e Inteligencia OCR
import asyncio
import pytesseract
from PIL import Image
import re

pytesseract.pytesseract.tesseract_cmd = r'/usr/bin/tesseract'


def extract_didi_trip_info(image_path: str) -> dict:
    """
    Lee capturas de pantalla de Didi y extrae:
    - Ganancias Totales
    - Método de Pago (Efectivo / Tarjeta)
    - Duración y Distancia
    """
    with Image.open(image_path) as img:
        text = pytesseract.image_to_string(img, lang='spa')

    earnings = None
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if any(keyword in line.lower() for keyword in ("ganancias", "total", "tarifa")):
            block = line + " " + (lines[index + 1] if index + 1 < len(lines) else "")
            numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*|\d+', block)
            if numbers:
                value = float(numbers[-1].replace('.', '').replace(',', ''))
                if 3000 <= value <= 500000:
                    earnings = value
                    break

    if earnings is None:
        numbers = re.findall(r'\d{1,3}(?:[.,]\d{3})*|\d+', text)
        for number in numbers:
            normalized = number.replace('.', '').replace(',', '')
            if normalized.isdigit():
                value = float(normalized)
                if 5000 <= value <= 150000:
                    earnings = value
                    break
    
    # Detección de método
    payment_method = "Tarjeta"
    if "efectivo" in text.lower():
        payment_method = "Efectivo"
    elif "nequi" in text.lower():
        payment_method = "Nequi"

    duration_match = re.search(r'(\d+m\s*\d*s?)', text)
    distance_match = re.search(r'(\d+[\.,]?\d*\s*km)', text, re.IGNORECASE)
    
    return {
        "net_earnings": earnings or 0.0,
        "payment_method": payment_method,
        "duration": duration_match.group(1) if duration_match else "N/A",
        "distance": distance_match.group(1) if distance_match else "N/A"
    }


async def extract_didi_trip_info_async(image_path: str) -> dict:
    return await asyncio.to_thread(extract_didi_trip_info, image_path)