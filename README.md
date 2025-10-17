SFTP API (FastAPI + Paramiko) — README

Objetivo: API HTTP para listar, crear directorios, subir archivos (solo archivos, no carpetas), descargar, eliminar archivo y eliminar directorio en un servidor remoto vía SFTP/SSH (p. ej. Droplet DigitalOcean 167.99.12.87 puerto 2222).
Stack: FastAPI, Paramiko, Uvicorn.
Deploy: Docker (API) + opcional Nginx (TLS).
Auth: X-API-Key (simple para red interna/plataforma).

1) Arquitectura
[Spring / Backend] --(X-API-Key)--> [FastAPI SFTP API] ---SSH/SFTP---> [Servidor de Archivos]
                                                    ^
                                                    | Docker
                                                    v
                                                [Nginx TLS]


La API opera directamente sobre el servidor SFTP.

Todas las rutas quedan confinadas a BASE_DIR.

Subir es SOLO archivos: nada de “carpetas”; si necesitas muchos, sube uno por request o sube un .zip.

2) Endpoints

Header obligatorio: X-API-Key: <tu_api_key>

Método	Ruta	Descripción	Parámetros
GET	/healthz	Healthcheck sencillo.	—
GET	/list	Lista contenido de un directorio bajo BASE_DIR.	path=/ (query)
POST	/mkdir	Crea directorio recursivamente (tipo mkdir -p).	path (form)
POST	/upload	Sube UN archivo a una ruta destino. Rechaza rutas que terminan en “/”.	remote_path (form), file (multipart)
GET	/download	Descarga un archivo (stream).	remote_path (query)
DELETE	/delete-file	Elimina un archivo.	remote_path (query)
DELETE	/delete-dir	Elimina un directorio (vacío o recursivo con ?recursive=true).	remote_path (query), recursive (bool query)
3) Variables de entorno

Copia .env.example → .env y edita:

API_KEY=pon-una-api-key-fuerte
SFTP_HOST=167.99.12.87
SFTP_PORT=2222
SFTP_USER=TU_USUARIO
SFTP_PASS=TU_PASSWORD
BASE_DIR=/home/TU_USUARIO


Consejos: usuario no-root, BASE_DIR dentro del home; cuando puedas, usa llaves SSH en vez de password.

4) Archivos del proyecto
sftp-api/
├─ app.py                 # API FastAPI + Paramiko
├─ requirements.txt
├─ Dockerfile
├─ docker-compose.yml     # API + Nginx (TLS opcional)
├─ nginx/
│  ├─ nginx.conf
│  └─ certs/              # fullchain.pem, privkey.pem (para TLS)
├─ .env.example
└─ README.md              # este archivo

4.1 requirements.txt
fastapi
uvicorn[standard]
paramiko
python-multipart
pydantic-settings

4.2 app.py
import os
import stat as pystat
import posixpath
import paramiko
from typing import Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header, Query
from fastapi.responses import StreamingResponse
from pydantic_settings import BaseSettings

# ------------- Settings -------------
class Settings(BaseSettings):
    API_KEY: str = "change-me"
    SFTP_HOST: str = "127.0.0.1"
    SFTP_PORT: int = 22
    SFTP_USER: str = "user"
    SFTP_PASS: str = "pass"
    BASE_DIR: str = "/home/user"

settings = Settings()
app = FastAPI(title="SFTP API", version="1.2.0")

# ------------- Auth -------------
def require_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# ------------- SFTP helpers -------------
def sftp_connect() -> paramiko.SFTPClient:
    transport = paramiko.Transport((settings.SFTP_HOST, settings.SFTP_PORT))
    transport.connect(username=settings.SFTP_USER, password=settings.SFTP_PASS)
    return paramiko.SFTPClient.from_transport(transport)

def safe_join(base: str, path: str) -> str:
    base_norm = posixpath.normpath(base)
    target = posixpath.normpath(posixpath.join(base_norm, path.lstrip("/")))
    if not target.startswith(base_norm):
        raise HTTPException(400, "Ruta fuera de BASE_DIR")
    return target

def mkdirs_sftp(sftp: paramiko.SFTPClient, remote_dir: str):
    parts = remote_dir.strip("/").split("/")
    cur = "/"
    for part in parts:
        if not part:
            continue
        cur = posixpath.join(cur, part)
        try:
            sftp.stat(cur)
        except FileNotFoundError:
            sftp.mkdir(cur)

def is_dir(sftp: paramiko.SFTPClient, remote_path: str) -> bool:
    st = sftp.stat(remote_path)
    return pystat.S_ISDIR(st.st_mode)

def listdir_info(sftp: paramiko.SFTPClient, remote_dir: str):
    items = []
    for f in sftp.listdir_attr(remote_dir):
        items.append({
            "name": f.filename,
            "size": f.st_size,
            "mode": oct(f.st_mode),
            "is_dir": pystat.S_ISDIR(f.st_mode),
            "mtime": f.st_mtime,
        })
    return items

def rmtree_sftp(sftp: paramiko.SFTPClient, target: str):
    base = posixpath.normpath(settings.BASE_DIR)
    target_norm = posixpath.normpath(target)
    if target_norm == base:
        raise HTTPException(400, "No se puede eliminar BASE_DIR")
    if not is_dir(sftp, target_norm):
        sftp.remove(target_norm)
        return
    for entry in sftp.listdir_attr(target_norm):
        child = posixpath.join(target_norm, entry.filename)
        if pystat.S_ISDIR(entry.st_mode):
            rmtree_sftp(sftp, child)
        else:
            sftp.remove(child)
    sftp.rmdir(target_norm)

# ------------- Endpoints -------------
@app.get("/healthz")
def healthz():
    return {"ok": True, "service": "sftp-api"}

@app.get("/list", dependencies=[Depends(require_api_key)])
def list_dir(path: str = Query("/", description="Ruta relativa a BASE_DIR")):
    sftp = sftp_connect()
    try:
        target = safe_join(settings.BASE_DIR, path)
        return {"path": target, "items": listdir_info(sftp, target)}
    finally:
        sftp.close()

@app.post("/mkdir", dependencies=[Depends(require_api_key)])
def mkdir(path: str = Form(..., description="Directorio a crear (relativo a BASE_DIR)")):
    sftp = sftp_connect()
    try:
        target = safe_join(settings.BASE_DIR, path)
        mkdirs_sftp(sftp, target)
        return {"ok": True, "created": target}
    finally:
        sftp.close()

@app.post("/upload", dependencies=[Depends(require_api_key)])
def upload(remote_path: str = Form(..., description="Ruta destino del archivo (relativa a BASE_DIR)"),
          file: UploadFile = File(...)):
    sftp = sftp_connect()
    try:
        if remote_path.endswith("/"):
            raise HTTPException(400, "remote_path debe ser un ARCHIVO (no terminar en /)")
        target = safe_join(settings.BASE_DIR, remote_path)
        remote_dir = posixpath.dirname(target)
        mkdirs_sftp(sftp, remote_dir)

        # Evita sobreescribir un directorio por error
        try:
            if is_dir(sftp, target):
                raise HTTPException(400, "remote_path apunta a un directorio; usa un nombre de archivo")
        except FileNotFoundError:
            pass

        with sftp.open(target, "wb") as dst:
            while True:
                chunk = file.file.read(1024 * 1024)  # 1MB
                if not chunk:
                    break
                dst.write(chunk)
        sftp.chmod(target, 0o640)
        return {"ok": True, "path": target}
    finally:
        sftp.close()

@app.get("/download", dependencies=[Depends(require_api_key)])
def download(remote_path: str):
    sftp = sftp_connect()
    try:
        target = safe_join(settings.BASE_DIR, remote_path)
        f = sftp.open(target, "rb")
        filename = posixpath.basename(target)
        return StreamingResponse(
            f,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except FileNotFoundError:
        raise HTTPException(404, "No existe")
    finally:
        sftp.close()

@app.delete("/delete-file", dependencies=[Depends(require_api_key)])
def delete_file(remote_path: str):
    sftp = sftp_connect()
    try:
        target = safe_join(settings.BASE_DIR, remote_path)
        if is_dir(sftp, target):
            raise HTTPException(400, "Es un directorio. Usa /delete-dir.")
        sftp.remove(target)
        return {"ok": True, "deleted": target}
    except FileNotFoundError:
        raise HTTPException(404, "No existe")
    finally:
        sftp.close()

@app.delete("/delete-dir", dependencies=[Depends(require_api_key)])
def delete_dir(remote_path: str, recursive: bool = Query(False, description="Eliminar recursivamente")):
    sftp = sftp_connect()
    try:
        target = safe_join(settings.BASE_DIR, remote_path)
        if not is_dir(sftp, target):
            raise HTTPException(400, "No es un directorio")
        if recursive:
            rmtree_sftp(sftp, target)
        else:
            if sftp.listdir(target):
                raise HTTPException(400, "Directorio no vacío (usa ?recursive=true)")
            sftp.rmdir(target)
        return {"ok": True, "deleted": target, "recursive": recursive}
    finally:
        sftp.close()

4.3 Dockerfile
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    openssh-client ca-certificates && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py /app/

EXPOSE 8080
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]

4.4 nginx/nginx.conf
events {}
http {
  include       mime.types;
  default_type  application/octet-stream;
  sendfile      on;

  server {
    listen 80;
    server_name _;

    if ($ssl_protocol = "") {
      return 301 https://$host$request_uri;
    }
  }

  server {
    listen 443 ssl;
    server_name _;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    location / {
      proxy_set_header Host $host;
      proxy_set_header X-Real-IP $remote_addr;
      proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
      proxy_set_header X-Forwarded-Proto $scheme;
      proxy_pass http://api:8080;
    }
  }
}

4.5 docker-compose.yml
version: "3.9"
services:
  api:
    build: .
    env_file:
      - .env
    restart: unless-stopped
    networks: [net]

  nginx:
    image: nginx:1.27-alpine
    depends_on: [api]
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/certs:/etc/nginx/certs:ro
    ports:
      - "80:80"
      - "443:443"
    restart: unless-stopped
    networks: [net]

networks:
  net:
    driver: bridge

4.6 .env.example
API_KEY=pon-una-api-key-fuerte
SFTP_HOST=167.99.12.87
SFTP_PORT=2222
SFTP_USER=TU_USUARIO
SFTP_PASS=TU_PASSWORD
BASE_DIR=/home/TU_USUARIO

5) Cómo levantar
5.1 Local (sin Docker)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export $(cat .env | xargs)  # o define a mano
uvicorn app:app --host 0.0.0.0 --port 8080 --reload

5.2 Docker (solo API)
docker build -t sftp-api:latest .
docker run --rm -p 8080:8080 --env-file .env sftp-api:latest

5.3 Docker Compose (API + Nginx TLS)
mkdir -p nginx/certs
# self-signed SOLO pruebas:
openssl req -x509 -newkey rsa:2048 -keyout nginx/certs/privkey.pem -out nginx/certs/fullchain.pem -days 365 -nodes -subj "/CN=localhost"

docker compose up --build -d

6) Pruebas

6.1 Suite automatizada (Fake SFTP)

La suite integra un `FakeSFTPClient` que simula el servidor SFTP sobre un directorio temporal, por lo que no necesitas conexión remota para validar la API.

```
cd sftp-api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python test_suite.py
```

El reporte de ejecuciones se registra en `docs/TEST_RUNS.md`. La suite cubre listar/mkdir/upload/download/delete y protecciones sobre `BASE_DIR`.

Atajo: `./scripts/run_tests.sh` crea/activa la venv, instala dependencias y ejecuta la suite en un solo paso.

6.2 Smoke tests (curl)

Prepara variables:

export API_KEY=$(grep API_KEY .env | cut -d= -f2)
BASEURL=http://localhost:8080


Health
curl "$BASEURL/healthz"

Listar raíz
curl -H "X-API-Key: $API_KEY" "$BASEURL/list?path=/"

Crear directorio
curl -X POST -H "X-API-Key: $API_KEY" -F "path=/uploads/pruebas" "$BASEURL/mkdir"

Subir archivo (SOLO archivo)

echo "hola mundo" > prueba.txt
curl -X POST -H "X-API-Key: $API_KEY" \
     -F "remote_path=/uploads/pruebas/prueba.txt" \
     -F "file=@./prueba.txt" \
     "$BASEURL/upload"


Descargar archivo
curl -L -H "X-API-Key: $API_KEY" "$BASEURL/download?remote_path=/uploads/pruebas/prueba.txt" -o bajada.txt

Eliminar archivo
curl -X DELETE -H "X-API-Key: $API_KEY" "$BASEURL/delete-file?remote_path=/uploads/pruebas/prueba.txt"

Eliminar directorio vacío
curl -X DELETE -H "X-API-Key: $API_KEY" "$BASEURL/delete-dir?remote_path=/uploads/pruebas"

Eliminar directorio recursivo
curl -X DELETE -H "X-API-Key: $API_KEY" "$BASEURL/delete-dir?remote_path=/uploads&recursive=true"

Batch de varios archivos (si lo necesitas): sube archivos, uno por request, o en un bucle:

for f in ./docs/*.pdf; do
  name=$(basename "$f")
  curl -s -X POST -H "X-API-Key: $API_KEY" \
    -F "remote_path=/uploads/reportes/$name" \
    -F "file=@$f" \
    "$BASEURL/upload"
done

7) Seguridad — “Think hard” checklist

SSH: usuario no-root; abre solo puerto 2222 y HTTP/HTTPS; considera llaves SSH y PasswordAuthentication no en prod.

Paths: safe_join bloquea .. y no permite escapar BASE_DIR.

Borrado: delete-dir no permite borrar BASE_DIR (protegido) y soporta ?recursive=true.

Upload: rechaza remote_path que termina en / y evita sobreescribir directorios.

Permisos: tras subir, aplica chmod 0640.

TLS: en prod usa certificados válidos (Let’s Encrypt/Traefik).

Logs: registra errores de Paramiko (404/400/401/403).

Nombres: prueba archivos con espacios y UTF-8; rutas profundas.

8) Deploy

- Dockerfile y docker-compose listos: ver sección 5.
- Guía extendida (`docs/DEPLOYMENT.md`) con pasos para GitHub y Railway (Docker o Buildpack via Procfile).

8) Troubleshooting

401 Invalid API key → revisa header X-API-Key y .env.

400 Ruta fuera de BASE_DIR → path intenta salir del directorio permitido.

404 No existe → archivo o directorio incorrecto/case sensitive.

Permission denied → ajusta permisos en el servidor:

ssh -p 2222 <USUARIO>@167.99.12.87
chmod 750 /home/<USUARIO>
mkdir -p /home/<USUARIO>/uploads && chmod 750 /home/<USUARIO>/uploads


Conexión SFTP falla → prueba manual: sftp -P 2222 <USUARIO>@167.99.12.87.

9) Criterios de aceptación

list/mkdir/upload/download/delete-file/delete-dir funcionan bajo BASE_DIR.

Upload solo acepta archivos; rechaza rutas tipo directorio.

delete-dir bloquea borrar BASE_DIR y maneja recursive=true.

Docker y docker-compose levantan sin errores; smoke tests pasan.
