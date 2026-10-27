FROM python:3.10-slim

# Instalar Tesseract OCR y el idioma español en el contenedor de Linux
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-spa \
    && rm -rf /var/lib/apt/lists/*

# Directorio de trabajo dentro del servidor
WORKDIR /app

# Copiar e instalar las librerías de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código del bot
COPY . .

# Comando para encender el bot
CMD ["python", "main.py"]