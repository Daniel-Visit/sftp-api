#!/bin/bash

echo "🔍 Verificando que no hay valores hardcodeados..."

# Verificar que no hay IPs, puertos o credenciales hardcodeadas
echo "Verificando app.py..."
if grep -E "(167\.99\.12\.87|2222|homemed|qweqwe)" app.py; then
    echo "❌ ERROR: Se encontraron valores hardcodeados en app.py"
    exit 1
fi

echo "Verificando .env.example..."
if grep -E "(167\.99\.12\.87|homemed|qweqwe)" .env.example; then
    echo "❌ ERROR: Se encontraron valores hardcodeados en .env.example"
    exit 1
fi

echo "Verificando docker-compose.yml..."
if grep -E "(167\.99\.12\.87|2222|homemed|qweqwe)" docker-compose.yml; then
    echo "❌ ERROR: Se encontraron valores hardcodeados en docker-compose.yml"
    exit 1
fi

echo "Verificando nginx/nginx.conf..."
if grep -E "(167\.99\.12\.87|2222|homemed|qweqwe)" nginx/nginx.conf; then
    echo "❌ ERROR: Se encontraron valores hardcodeados en nginx/nginx.conf"
    exit 1
fi

echo "✅ Verificación completada: No se encontraron valores hardcodeados"
