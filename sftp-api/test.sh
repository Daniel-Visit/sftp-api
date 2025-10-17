#!/bin/bash

# Cargar variables de entorno
if [ ! -f .env ]; then
    echo "❌ ERROR: Archivo .env no encontrado"
    echo "Copia .env.example a .env y configura tus credenciales"
    exit 1
fi

source .env

# Verificar que las variables están configuradas
if [ -z "$API_KEY" ] || [ -z "$SFTP_HOST" ] || [ -z "$SFTP_PORT" ] || [ -z "$SFTP_USER" ] || [ -z "$SFTP_PASS" ] || [ -z "$BASE_DIR" ]; then
    echo "❌ ERROR: Variables de entorno no configuradas completamente"
    echo "Asegúrate de configurar todas las variables en .env"
    exit 1
fi

BASEURL="http://localhost:8080"

echo "🧪 Iniciando smoke tests..."
echo "API Key: ${API_KEY:0:8}..."
echo "SFTP Host: $SFTP_HOST"
echo "Base URL: $BASEURL"

# Test 1: Health check (sin auth)
echo ""
echo "1️⃣ Test: Health check (sin auth)"
response=$(curl -s -w "%{http_code}" -o /tmp/health_response.json "$BASEURL/healthz")
if [ "$response" = "200" ]; then
    echo "✅ Health check OK"
else
    echo "❌ Health check falló: HTTP $response"
    cat /tmp/health_response.json
fi

# Test 2: Endpoint con API key inválida
echo ""
echo "2️⃣ Test: API key inválida"
response=$(curl -s -w "%{http_code}" -o /tmp/invalid_auth_response.json -H "X-API-Key: invalid-key" "$BASEURL/list")
if [ "$response" = "401" ]; then
    echo "✅ Autenticación funciona correctamente"
else
    echo "❌ Autenticación falló: HTTP $response"
    cat /tmp/invalid_auth_response.json
fi

# Test 3: Path traversal
echo ""
echo "3️⃣ Test: Path traversal (debe fallar)"
response=$(curl -s -w "%{http_code}" -o /tmp/traversal_response.json -H "X-API-Key: $API_KEY" "$BASEURL/list?path=../../../etc/passwd")
if [ "$response" = "400" ]; then
    echo "✅ Path traversal bloqueado correctamente"
else
    echo "❌ Path traversal no fue bloqueado: HTTP $response"
    cat /tmp/traversal_response.json
fi

# Test 4: Listar directorio (con auth válida)
echo ""
echo "4️⃣ Test: Listar directorio (con auth válida)"
response=$(curl -s -w "%{http_code}" -o /tmp/list_response.json -H "X-API-Key: $API_KEY" "$BASEURL/list?path=/")
if [ "$response" = "200" ]; then
    echo "✅ Listar directorio OK"
    echo "Contenido:"
    cat /tmp/list_response.json | head -5
else
    echo "❌ Listar directorio falló: HTTP $response"
    cat /tmp/list_response.json
fi

echo ""
echo "🧪 Smoke tests completados"
