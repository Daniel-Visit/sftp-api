# Deploy Guide

## 1. Tests & Quality Gate
- Ejecutar `./scripts/run_tests.sh` para levantar la venv, instalar dependencias y validar la suite (`python test_suite.py`).
- Registrar el resultado en `docs/TEST_RUNS.md` si corresponde.

## 2. Docker
```bash
cd sftp-api
docker build -t sftp-api:latest .
docker run --rm -p 8080:8080 --env-file .env sftp-api:latest
```
- Variables esperadas: `API_KEY`, `SFTP_HOST`, `SFTP_PORT`, `SFTP_USER`, `SFTP_PASS`, `BASE_DIR`, `PORT` (opcional, default `8080`).

## 3. GitHub
1. Crear repositorio vacío en GitHub (ej. `sftp-api`).
2. Inicializar localmente:
    ```bash
    git init
    git add .
    git commit -m "Initial commit"
    git branch -M main
    git remote add origin git@github.com:<usuario>/<repo>.git
    git push -u origin main
    ```
3. Añadir instrucciones en el README para colaboradores (ej. script de tests).

## 4. Railway
### Opción Dockerfile (recomendada)
1. En Railway > New Project > Deploy from GitHub, seleccionar el repositorio.
2. Railway detectará el `Dockerfile` (asegúrate de que esté en la raíz del repo).
3. Configurar variables:
    - `PORT=8080` (Railway lo inyecta automáticamente, pero se puede sobrescribir).
    - `API_KEY`, `SFTP_HOST`, `SFTP_PORT`, `SFTP_USER`, `SFTP_PASS`, `BASE_DIR`.
4. Deploy y validar logs.

### Opción Buildpack + Procfile
1. Crear `Procfile` con:  
   `web: uvicorn app:app --host 0.0.0.0 --port $PORT`
2. Railway detectará Python, instalará `requirements.txt` y ejecutará el `Procfile`.
3. Configurar las mismas variables de entorno.

## 5. Smoke Tests en Railway
1. Esperar a que la app esté “Running”.
2. Obtener la URL desplegada e invocar:
    ```bash
    API_KEY=<tu_key>
    BASEURL=https://<tu-servicio>.up.railway.app
    curl -H "X-API-Key: $API_KEY" "$BASEURL/list?path=/"
    ```
3. Registrar los resultados (ej. en `docs/TEST_RUNS.md`).
