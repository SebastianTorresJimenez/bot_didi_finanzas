# ocr_processor.py - Procesamiento de Imágenes e Inteligencia OCR
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
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img, lang='spa')
    
    # Expresiones regulares para montos
    earnings_match = re.search(r'\$\s*(\d+[\.,]\d+)', text)
    earnings = float(earnings_match.group(1).replace('.', '').replace(',', '.')) if earnings_match else 0.0
    
    # Detección de método
    payment_method = "Tarjeta"
    if "En efectivo" in text or "Efectivo" in text:
        payment_method = "Efectivo"
        
    duration_match = re.search(r'(\d+m\d+s)', text)
    distance_match = re.search(r'(\d+[\.,]\d+\s*km)', text)
    
    return {
        "net_earnings": earnings,
        "payment_method": payment_method,
        "duration": duration_match.group(1) if duration_match else "N/A",
        "distance": distance_match.group(1) if distance_match else "N/A"
    }