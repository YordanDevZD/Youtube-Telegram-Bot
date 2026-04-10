# Usar imagen oficial de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar FFmpeg y otras dependencias del sistema
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar archivo de requerimientos primero (mejor para caché)
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código
COPY . .

# Crear directorio para descargas
RUN mkdir -p downloads

# Comando para ejecutar el bot
CMD ["python", "main.py"]
