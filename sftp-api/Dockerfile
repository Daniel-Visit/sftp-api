FROM python:3.11-slim

# Configuración de entorno
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

# Instalar dependencias del sistema en un solo layer
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    openssh-client \
    ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Configurar directorio de trabajo
WORKDIR /app

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar código de la aplicación
COPY app.py .

# Exponer puerto (Railway usa la variable PORT)
EXPOSE 8080

# Comando de inicio usando variable de entorno PORT
CMD uvicorn app:app --host 0.0.0.0 --port ${PORT:-8080}
