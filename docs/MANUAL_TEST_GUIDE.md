# Guía de Test Manual - SFTP API

Esta guía te ayudará a ejecutar tests manuales contra el servidor SFTP real antes de hacer deployment en Railway.

## Pre-requisitos

- Python 3.11+ instalado
- Acceso al servidor SFTP (credenciales disponibles)
- Terminal/consola

## Paso 1: Configurar Variables de Entorno

El archivo `.env` ya debe estar configurado en `sftp-api/` con:

```bash
API_KEY=tu-api-key-segura
SFTP_HOST=167.99.12.87
SFTP_PORT=2222
SFTP_USER=homemed
SFTP_PASS=qweqwe
BASE_DIR=/home/homemed
```

Si no existe, créalo:
```bash
cd sftp-api
cp .env.example .env
# Edita .env con tus credenciales reales
```

## Paso 2: Instalar Dependencias

```bash
cd sftp-api

# Opción 1: Con entorno virtual (recomendado)
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Opción 2: Sin entorno virtual
pip install -r requirements.txt
```

## Paso 3: Levantar la API

En una terminal, ejecuta:

```bash
cd sftp-api
source .venv/bin/activate  # Si usas venv
uvicorn app:app --host 0.0.0.0 --port 8080
```

Deberías ver algo como:
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080 (Press CTRL+C to quit)
```

**IMPORTANTE**: Deja esta terminal abierta con la API corriendo.

## Paso 4: Ejecutar Tests Manuales

En **otra terminal nueva**, ejecuta:

```bash
cd sftp-api
bash manual_test.sh
```

El script ejecutará 14 tests automáticamente y mostrará el progreso en tiempo real.

## Paso 5: Revisar Resultados

Los resultados se guardan en `sftp-api/manual_test_results.txt`.

```bash
cat manual_test_results.txt
```

### Resultados Esperados

Si todo funciona correctamente, deberías ver:

```
📊 RESUMEN FINAL
===================================
Total de tests: 14
Tests exitosos: 14
Tests fallidos: 0
Tasa de éxito: 100.0%

🎉 ¡Todos los tests pasaron!
✅ La API está lista para deployment en Railway
```

### Tests Incluidos

1. ✅ Health Check
2. ✅ Auth - Sin API Key (debe fallar con 401)
3. ✅ Auth - API Key incorrecta (debe fallar con 401)
4. ✅ Listar directorio root
5. ✅ Path traversal (debe fallar con 400)
6. ✅ Crear directorio de prueba
7. ✅ Subir archivo
8. ✅ Upload terminando en / (debe fallar con 400)
9. ✅ Descargar archivo
10. ✅ Eliminar archivo
11. ✅ Eliminar directorio vacío
12. ✅ Crear directorio para test recursivo
13. ✅ Eliminar directorio no vacío sin recursive (debe fallar con 400)
14. ✅ Eliminar directorio recursivamente

## Paso 6: Documentar Resultados

Actualiza `docs/TEST_RUNS.md` con los resultados:

```bash
echo "
## Test Manual - $(date)
- Servidor: 167.99.12.87:2222
- Resultados: Ver sftp-api/manual_test_results.txt
- Tests: 14/14 ✅
" >> docs/TEST_RUNS.md
```

## Solución de Problemas

### Error: "Archivo .env no encontrado"
- Asegúrate de estar en el directorio `sftp-api/`
- Verifica que el archivo `.env` existe: `ls -la .env`

### Error: "API_KEY no configurada en .env"
- Abre `.env` y asegúrate que tiene la línea `API_KEY=tu-api-key`
- No debe haber espacios alrededor del `=`

### Error: Connection refused
- Verifica que la API está corriendo en otra terminal
- Asegúrate que está en el puerto 8080: `curl http://localhost:8080/healthz`

### Error: 401 Unauthorized en todos los tests
- Verifica que el `API_KEY` en `.env` es correcto
- Asegúrate que no hay espacios o caracteres especiales

### Error: Timeout o no responde
- Verifica la conexión al servidor SFTP: `sftp -P 2222 homemed@167.99.12.87`
- Verifica que las credenciales en `.env` son correctas
- Verifica que el servidor está accesible desde tu red

### Tests fallidos en operaciones SFTP
- Verifica permisos en el servidor: `chmod 750 /home/homemed`
- Verifica que `BASE_DIR` existe en el servidor
- Revisa logs de uvicorn en la terminal donde está corriendo

## Siguiente Paso: Railway Deployment

Una vez que **todos los tests pasan** (14/14 ✅), estás listo para hacer deployment en Railway:

1. **Commit y push a GitHub**:
```bash
cd "/Users/daniel/Documents/API Digital Ocean"
git add .
git commit -m "Tests manuales completados - API validada"
git push
```

2. **Configurar Railway**:
- Ve a [railway.app](https://railway.app)
- Conecta tu repositorio de GitHub
- Configura las variables de entorno:
  - `API_KEY`
  - `SFTP_HOST`
  - `SFTP_PORT`
  - `SFTP_USER`
  - `SFTP_PASS`
  - `BASE_DIR`
  - `PORT=8080`

3. **Verificar deployment**:
```bash
# Reemplaza <tu-url> con la URL de Railway
curl https://<tu-url>.railway.app/healthz
```

## Notas Adicionales

- Los tests crean y eliminan archivos/directorios temporales con timestamp
- No dejan "basura" en el servidor
- Son seguros de ejecutar múltiples veces
- Verifican tanto casos exitosos como casos de error
