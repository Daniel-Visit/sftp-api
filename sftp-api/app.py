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

    class Config:
        env_file = ".env"

# Permitir override de settings para testing
_settings_instance = None

def get_settings():
    """Obtiene la instancia de settings (permite override para testing)."""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance

def set_settings_for_testing(test_settings):
    """Permite inyectar settings para testing."""
    global _settings_instance
    _settings_instance = test_settings

settings = get_settings()
app = FastAPI(title="SFTP API", version="1.2.0")

# ------------- Auth -------------
def require_api_key(x_api_key: Optional[str] = Header(None)):
    settings = get_settings()
    if x_api_key != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return True

# ------------- SFTP helpers -------------
def sftp_connect() -> paramiko.SFTPClient:
    settings = get_settings()
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
    settings = get_settings()
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
    settings = get_settings()
    sftp = sftp_connect()
    try:
        target = safe_join(settings.BASE_DIR, path)
        return {"path": target, "items": listdir_info(sftp, target)}
    finally:
        sftp.close()

@app.post("/mkdir", dependencies=[Depends(require_api_key)])
def mkdir(path: str = Form(..., description="Directorio a crear (relativo a BASE_DIR)")):
    settings = get_settings()
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
    settings = get_settings()
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
    settings = get_settings()
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
    settings = get_settings()
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
    settings = get_settings()
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
