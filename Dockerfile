FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Instalar dependencias del sistema adicionales si son necesarias (Playwright ya trae las dependencias de los navegadores)
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Establecer el directorio de trabajo
WORKDIR /app
ENV PYTHONPATH=/app

# Copiar los requerimientos e instalarlos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el código de la aplicación
COPY . .

# Exponer el puerto por defecto de Flask
EXPOSE 5000

# Comando para iniciar el bot principal
CMD ["python", "src/main.py"]
