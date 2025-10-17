# Test Runs - SFTP API

Este documento registra los resultados de los tests ejecutados en la API SFTP.

## Configuración del Servidor SFTP

- **Host**: 167.99.12.87
- **Puerto**: 2222
- **Usuario**: homemed
- **Contraseña**: qweqwe
- **BASE_DIR**: /home/homemed

## Test Run #1 - Fecha: [PENDIENTE]

### Setup
- API levantada con: `uvicorn app:app --host 0.0.0.0 --port 8080`
- Archivo `.env` configurado con credenciales reales

### Tests Ejecutados

#### 1. Health Check
```bash
curl http://localhost:8080/healthz
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 2. Listar Directorio Root
```bash
curl -H "X-API-Key: $API_KEY" "http://localhost:8080/list?path=/"
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 3. Crear Directorio
```bash
curl -X POST -H "X-API-Key: $API_KEY" -F "path=/test-api-$(date +%s)" http://localhost:8080/mkdir
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 4. Subir Archivo
```bash
echo "test content $(date +%s)" > test.txt
curl -X POST -H "X-API-Key: $API_KEY" \
     -F "remote_path=/test-api-xxx/test.txt" \
     -F "file=@./test.txt" \
     http://localhost:8080/upload
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 5. Descargar Archivo
```bash
curl -L -H "X-API-Key: $API_KEY" "http://localhost:8080/download?remote_path=/test-api-xxx/test.txt" -o downloaded.txt
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 6. Eliminar Archivo
```bash
curl -X DELETE -H "X-API-Key: $API_KEY" "http://localhost:8080/delete-file?remote_path=/test-api-xxx/test.txt"
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 7. Eliminar Directorio
```bash
curl -X DELETE -H "X-API-Key: $API_KEY" "http://localhost:8080/delete-dir?remote_path=/test-api-xxx"
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

### Tests de Seguridad

#### 8. Path Traversal
```bash
curl -H "X-API-Key: $API_KEY" "http://localhost:8080/list?path=../../etc/passwd"
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 9. API Key Inválida
```bash
curl -H "X-API-Key: invalid-key" "http://localhost:8080/list"
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

#### 10. Upload a Directorio (debe fallar)
```bash
curl -X POST -H "X-API-Key: $API_KEY" \
     -F "remote_path=/test/" \
     -F "file=@./test.txt" \
     http://localhost:8080/upload
```
**Resultado**: [PENDIENTE]
**Status**: [PENDIENTE]

## Resumen

- **Tests Ejecutados**: 0/10
- **Tests Exitosos**: 0
- **Tests Fallidos**: 0
- **Estado**: PENDIENTE DE EJECUCIÓN

## Notas

- Los tests se ejecutarán usando las credenciales reales del servidor SFTP
- Cada test incluye verificación de status code y contenido de respuesta
- Se documentarán errores específicos si los hay
- Los archivos de prueba se crearán con timestamps únicos para evitar conflictos
