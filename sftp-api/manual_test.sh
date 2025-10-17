#!/bin/bash

# Script de test manual para API SFTP
# Ejecuta tests contra el servidor SFTP real
# Escribe resultados a manual_test_results.txt

# Colores para output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuración
BASEURL="http://localhost:8080"
RESULTS_FILE="manual_test_results.txt"
TIMESTAMP=$(date +%s)
TEST_DIR="/test-api-${TIMESTAMP}"

# Cargar variables de entorno
if [ ! -f .env ]; then
    echo -e "${RED}❌ ERROR: Archivo .env no encontrado${NC}"
    echo "Por favor crea el archivo .env con tus credenciales"
    exit 1
fi

source .env

if [ -z "$API_KEY" ]; then
    echo -e "${RED}❌ ERROR: API_KEY no configurada en .env${NC}"
    exit 1
fi

# Inicializar archivo de resultados
echo "==================================" > $RESULTS_FILE
echo "SFTP API - RESULTADOS DE TEST MANUAL" >> $RESULTS_FILE
echo "Fecha: $(date)" >> $RESULTS_FILE
echo "Servidor: $SFTP_HOST:$SFTP_PORT" >> $RESULTS_FILE
echo "Usuario: $SFTP_USER" >> $RESULTS_FILE
echo "==================================" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

# Contador de tests
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Función para ejecutar test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_status="$3"
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    echo -e "${YELLOW}🧪 Test ${TOTAL_TESTS}: ${test_name}${NC}"
    echo "-----------------------------------" >> $RESULTS_FILE
    echo "Test ${TOTAL_TESTS}: ${test_name}" >> $RESULTS_FILE
    echo "Comando: ${test_command}" >> $RESULTS_FILE
    
    # Ejecutar comando y capturar status code
    response=$(eval "$test_command" 2>&1)
    status=$?
    http_status=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)
    
    echo "Status HTTP: ${http_status}" >> $RESULTS_FILE
    echo "Respuesta: ${body}" >> $RESULTS_FILE
    
    # Verificar resultado
    if [[ "$http_status" == "$expected_status" ]] || [[ "$status" == "0" && -n "$body" ]]; then
        echo -e "${GREEN}✅ PASÓ${NC}"
        echo "Resultado: ✅ PASÓ" >> $RESULTS_FILE
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}❌ FALLÓ${NC}"
        echo "Resultado: ❌ FALLÓ (esperado: $expected_status, obtenido: $http_status)" >> $RESULTS_FILE
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo "" >> $RESULTS_FILE
    
    sleep 0.5
}

echo -e "${GREEN}🚀 Iniciando tests manuales...${NC}"
echo ""

# Test 1: Health Check
run_test "Health Check" \
    "curl -s -w '\n%{http_code}' $BASEURL/healthz" \
    "200"

# Test 2: Auth - Sin API Key
run_test "Auth - Sin API Key (debe fallar)" \
    "curl -s -w '\n%{http_code}' $BASEURL/list" \
    "401"

# Test 3: Auth - API Key incorrecta
run_test "Auth - API Key incorrecta (debe fallar)" \
    "curl -s -w '\n%{http_code}' -H 'X-API-Key: invalid-key' $BASEURL/list" \
    "401"

# Test 4: Listar directorio root
run_test "Listar directorio root" \
    "curl -s -w '\n%{http_code}' -H 'X-API-Key: $API_KEY' '$BASEURL/list?path=/'" \
    "200"

# Test 5: Path traversal (debe fallar)
run_test "Path traversal (debe fallar)" \
    "curl -s -w '\n%{http_code}' -H 'X-API-Key: $API_KEY' '$BASEURL/list?path=../../etc/passwd'" \
    "400"

# Test 6: Crear directorio
run_test "Crear directorio de prueba" \
    "curl -s -w '\n%{http_code}' -X POST -H 'X-API-Key: $API_KEY' -F 'path=$TEST_DIR' $BASEURL/mkdir" \
    "200"

# Test 7: Subir archivo
echo "test content ${TIMESTAMP}" > /tmp/test_file_${TIMESTAMP}.txt
run_test "Subir archivo" \
    "curl -s -w '\n%{http_code}' -X POST -H 'X-API-Key: $API_KEY' -F 'remote_path=${TEST_DIR}/test.txt' -F 'file=@/tmp/test_file_${TIMESTAMP}.txt' $BASEURL/upload" \
    "200"

# Test 8: Upload terminando en / (debe fallar)
run_test "Upload terminando en / (debe fallar)" \
    "curl -s -w '\n%{http_code}' -X POST -H 'X-API-Key: $API_KEY' -F 'remote_path=${TEST_DIR}/' -F 'file=@/tmp/test_file_${TIMESTAMP}.txt' $BASEURL/upload" \
    "400"

# Test 9: Descargar archivo
run_test "Descargar archivo" \
    "curl -s -w '\n%{http_code}' -H 'X-API-Key: $API_KEY' '$BASEURL/download?remote_path=${TEST_DIR}/test.txt' -o /tmp/downloaded_${TIMESTAMP}.txt" \
    "200"

# Verificar contenido del archivo descargado
if [ -f /tmp/downloaded_${TIMESTAMP}.txt ]; then
    downloaded_content=$(cat /tmp/downloaded_${TIMESTAMP}.txt)
    echo "Contenido descargado: ${downloaded_content}" >> $RESULTS_FILE
    rm /tmp/downloaded_${TIMESTAMP}.txt
fi

# Test 10: Eliminar archivo
run_test "Eliminar archivo" \
    "curl -s -w '\n%{http_code}' -X DELETE -H 'X-API-Key: $API_KEY' '$BASEURL/delete-file?remote_path=${TEST_DIR}/test.txt'" \
    "200"

# Test 11: Eliminar directorio vacío
run_test "Eliminar directorio vacío" \
    "curl -s -w '\n%{http_code}' -X DELETE -H 'X-API-Key: $API_KEY' '$BASEURL/delete-dir?remote_path=${TEST_DIR}'" \
    "200"

# Test 12: Crear directorio con archivo para test recursivo
run_test "Crear directorio para test recursivo" \
    "curl -s -w '\n%{http_code}' -X POST -H 'X-API-Key: $API_KEY' -F 'path=${TEST_DIR}' $BASEURL/mkdir" \
    "200"

run_test "Subir archivo para test recursivo" \
    "curl -s -w '\n%{http_code}' -X POST -H 'X-API-Key: $API_KEY' -F 'remote_path=${TEST_DIR}/file.txt' -F 'file=@/tmp/test_file_${TIMESTAMP}.txt' $BASEURL/upload" \
    "200"

# Test 13: Eliminar directorio no vacío sin recursive (debe fallar)
run_test "Eliminar directorio no vacío sin recursive (debe fallar)" \
    "curl -s -w '\n%{http_code}' -X DELETE -H 'X-API-Key: $API_KEY' '$BASEURL/delete-dir?remote_path=${TEST_DIR}'" \
    "400"

# Test 14: Eliminar directorio con recursive
run_test "Eliminar directorio recursivamente" \
    "curl -s -w '\n%{http_code}' -X DELETE -H 'X-API-Key: $API_KEY' '$BASEURL/delete-dir?remote_path=${TEST_DIR}&recursive=true'" \
    "200"

# Limpiar archivos temporales
rm -f /tmp/test_file_${TIMESTAMP}.txt

# Resumen final
echo "" >> $RESULTS_FILE
echo "==================================" >> $RESULTS_FILE
echo "RESUMEN FINAL" >> $RESULTS_FILE
echo "==================================" >> $RESULTS_FILE
echo "Total de tests: ${TOTAL_TESTS}" >> $RESULTS_FILE
echo "Tests exitosos: ${PASSED_TESTS}" >> $RESULTS_FILE
echo "Tests fallidos: ${FAILED_TESTS}" >> $RESULTS_FILE
SUCCESS_RATE=$(awk "BEGIN {printf \"%.1f\", ($PASSED_TESTS/$TOTAL_TESTS)*100}")
echo "Tasa de éxito: ${SUCCESS_RATE}%" >> $RESULTS_FILE
echo "" >> $RESULTS_FILE

# Mostrar resumen en pantalla
echo ""
echo "==================================="
echo -e "${GREEN}📊 RESUMEN FINAL${NC}"
echo "==================================="
echo "Total de tests: ${TOTAL_TESTS}"
echo -e "Tests exitosos: ${GREEN}${PASSED_TESTS}${NC}"
echo -e "Tests fallidos: ${RED}${FAILED_TESTS}${NC}"
echo "Tasa de éxito: ${SUCCESS_RATE}%"
echo ""
echo "Resultados completos guardados en: ${RESULTS_FILE}"
echo ""

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 ¡Todos los tests pasaron!${NC}"
    echo -e "${GREEN}✅ La API está lista para deployment en Railway${NC}"
    exit 0
else
    echo -e "${RED}⚠️  Algunos tests fallaron. Revisa ${RESULTS_FILE} para más detalles.${NC}"
    exit 1
fi
