# SFTP API (FastAPI + Paramiko)

**Objetivo**: API HTTP para listar, crear directorios, subir archivos (solo archivos, no carpetas), descargar, eliminar archivo y eliminar directorio en un servidor remoto vía SFTP/SSH.

**Stack**: FastAPI, Paramiko, Uvicorn.

**Deploy**: Docker (API) + opcional Nginx (TLS).

**Auth**: X-API-Key (simple para red interna/plataforma).

## 1) Arquitectura

```
[Spring / Backend] --(X-API-Key)--> [FastAPI SFTP API] ---SSH/SFTP---> [Servidor de Archivos]
                                                    ^
                                                    | Docker
                                                    v
                                                [Nginx TLS]
```

La API opera directamente sobre el servidor SFTP.

Todas las rutas quedan confinadas a BASE_DIR.

Subir es SOLO archivos: nada de "carpetas"; si necesitas muchos, sube uno por request o sube un .zip.

## 2) Endpoints

**Header obligatorio**: `X-API-Key: <tu_api_key>`

| Método | Ruta | Descripción | Parámetros |
|--------|------|-------------|------------|
| GET | `/healthz` | Healthcheck sencillo | — |
| GET | `/list` | Lista contenido de un directorio bajo BASE_DIR | `path=/` (query) |
| POST | `/mkdir` | Crea directorio recursivamente (tipo mkdir -p) | `path` (form) |
| POST | `/upload` | Sube UN archivo a una ruta destino. Rechaza rutas que terminan en "/" | `remote_path` (form), `file` (multipart) |
| GET | `/download` | Descarga un archivo (stream) | `remote_path` (query) |
| DELETE | `/delete-file` | Elimina un archivo | `remote_path` (query) |
| DELETE | `/delete-dir` | Elimina un directorio (vacío o recursivo con `?recursive=true`) | `remote_path` (query), `recursive` (bool query) |

## 3) Variables de entorno

Copia `.env.example` → `.env` y edita:

```bash
API_KEY=pon-una-api-key-fuerte
SFTP_HOST=tu-servidor-sftp
SFTP_PORT=2222
SFTP_USER=tu-usuario
SFTP_PASS=tu-contraseña
BASE_DIR=/home/tu-usuario
```

**Consejos**: usuario no-root, BASE_DIR dentro del home; cuando puedas, usa llaves SSH en vez de password.

## 4) Archivos del proyecto

```
sftp-api/
├─ app.py                 # API FastAPI + Paramiko
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml     # API + Nginx (TLS opcional)
├─ verify.sh              # Script para verificar valores hardcodeados
├─ test.sh                # Script de smoke tests
├─ nginx/
│  ├─ nginx.conf
│  └─ certs/              # fullchain.pem, privkey.pem (para TLS)
├─ .env.example
├─ .gitignore
└─ README.md              # este archivo
```

## 5) Cómo levantar

### 5.1 Local (sin Docker)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # y edita las credenciales
uvicorn app:app --host 0.0.0.0 --port 8080 --reload
```

### 5.2 Docker (solo API)

```bash
cp .env.example .env  # y edita las credenciales
docker build -t sftp-api:latest .
docker run --rm -p 8080:8080 --env-file .env sftp-api:latest
```

### 5.3 Docker Compose (API + Nginx TLS)

```bash
cp .env.example .env  # y edita las credenciales
mkdir -p nginx/certs

# self-signed SOLO pruebas:
openssl req -x509 -newkey rsa:2048 -keyout nginx/certs/privkey.pem -out nginx/certs/fullchain.pem -days 365 -nodes -subj "/CN=localhost"

docker compose up --build -d
```

## 6) Verificación y Testing

### Verificar que no hay valores hardcodeados:
```bash
./verify.sh
```

### Smoke tests (requiere .env configurado):
```bash
./test.sh
```

### Smoke tests manuales (curl)

Prepara variables:
```bash
source .env
export API_KEY
BASEURL=http://localhost:8080
```

**Health**
```bash
curl "$BASEURL/healthz"
```

**Listar raíz**
```bash
curl -H "X-API-Key: $API_KEY" "$BASEURL/list?path=/"
```

**Crear directorio**
```bash
curl -X POST -H "X-API-Key: $API_KEY" -F "path=/uploads/pruebas" "$BASEURL/mkdir"
```

**Subir archivo (SOLO archivo)**
```bash
echo "hola mundo" > prueba.txt
curl -X POST -H "X-API-Key: $API_KEY" \
     -F "remote_path=/uploads/pruebas/prueba.txt" \
     -F "file=@./prueba.txt" \
     "$BASEURL/upload"
```

**Descargar archivo**
```bash
curl -L -H "X-API-Key: $API_KEY" "$BASEURL/download?remote_path=/uploads/pruebas/prueba.txt" -o bajada.txt
```

**Eliminar archivo**
```bash
curl -X DELETE -H "X-API-Key: $API_KEY" "$BASEURL/delete-file?remote_path=/uploads/pruebas/prueba.txt"
```

**Eliminar directorio vacío**
```bash
curl -X DELETE -H "X-API-Key: $API_KEY" "$BASEURL/delete-dir?remote_path=/uploads/pruebas"
```

**Eliminar directorio recursivo**
```bash
curl -X DELETE -H "X-API-Key: $API_KEY" "$BASEURL/delete-dir?remote_path=/uploads&recursive=true"
```

**Batch de varios archivos** (si lo necesitas): sube archivos, uno por request, o en un bucle:

```bash
for f in ./docs/*.pdf; do
  name=$(basename "$f")
  curl -s -X POST -H "X-API-Key: $API_KEY" \
    -F "remote_path=/uploads/reportes/$name" \
    -F "file=@$f" \
    "$BASEURL/upload"
done
```

## 7) Seguridad — "Think hard" checklist

- SSH: usuario no-root; abre solo puerto SSH y HTTP/HTTPS; considera llaves SSH y PasswordAuthentication no en prod.
- Paths: `safe_join` bloquea `..` y no permite escapar BASE_DIR.
- Borrado: `delete-dir` no permite borrar BASE_DIR (protegido) y soporta `?recursive=true`.
- Upload: rechaza `remote_path` que termina en `/` y evita sobreescribir directorios.
- Permisos: tras subir, aplica `chmod 0640`.
- TLS: en prod usa certificados válidos (Let's Encrypt/Traefik).
- Logs: registra errores de Paramiko (404/400/401/403).
- Nombres: prueba archivos con espacios y UTF-8; rutas profundas.

## 8) Troubleshooting

- **401 Invalid API key** → revisa header `X-API-Key` y `.env`.
- **400 Ruta fuera de BASE_DIR** → `path` intenta salir del directorio permitido.
- **404 No existe** → archivo o directorio incorrecto/case sensitive.
- **Permission denied** → ajusta permisos en el servidor:

```bash
ssh -p $SFTP_PORT $SFTP_USER@$SFTP_HOST
chmod 750 $BASE_DIR
mkdir -p $BASE_DIR/uploads && chmod 750 $BASE_DIR/uploads
```

- **Conexión SFTP falla** → prueba manual: `sftp -P $SFTP_PORT $SFTP_USER@$SFTP_HOST`.

## 9) Criterios de aceptación

- ✅ `list/mkdir/upload/download/delete-file/delete-dir` funcionan bajo BASE_DIR.
- ✅ Upload solo acepta archivos; rechaza rutas tipo directorio.
- ✅ `delete-dir` bloquea borrar BASE_DIR y maneja `recursive=true`.
- ✅ Docker y docker-compose levantan sin errores; smoke tests pasan.
- ✅ Ningún valor sensible hardcodeado en el código (verificado con `./verify.sh`).
- ✅ Todas las configuraciones vienen de variables de entorno.
