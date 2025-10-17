#!/usr/bin/env python3
"""
Mock SFTP Server para testing.
Simula un servidor SFTP local usando paramiko y un directorio temporal.
"""

import os
import tempfile
import threading
import time
import socket
import shutil
from pathlib import Path
import paramiko
import logging
import paramiko.util

paramiko.util.log_to_file("mock_paramiko.log", level="DEBUG")

# Configurar logging para debug
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockSFTPHandle(paramiko.SFTPHandle):
    """Handle para archivos SFTP en el mock server."""
    
    def __init__(self, filename, mode, server):
        self.server = server
        self.filename = filename
        self.mode = mode
        super().__init__()
        
        # Mapear a archivo local
        local_path = self.server.map_path(filename)
        self.file = open(local_path, mode)
        self.readfile = self.file
        self.writefile = self.file
        self.flags = mode

class MockSFTPServerInterface(paramiko.SFTPServerInterface):
    """Implementación del servidor SFTP para testing."""
    
    active_instances = []
    
    def __init__(self, server, base_dir, *args, **kwargs):
        self.server = server
        self.base_dir = Path(base_dir)
        logger.info(f"Mock SFTP base directory: {self.base_dir}")
        
        # Crear directorio base de prueba
        self.test_dir = self.base_dir / "test"
        self.test_dir.mkdir(parents=True, exist_ok=True)
        
        # Crear algunos archivos de prueba si no existen
        (self.test_dir / "file1.txt").write_text("Hello World")
        (self.test_dir / "file2.txt").write_text("Test content")
        
        super().__init__(server, *args, **kwargs)
        MockSFTPServerInterface.active_instances.append(self)
    
    def map_path(self, path):
        """Mapea ruta SFTP a ruta local."""
        # Remover /test del path y mapear a test_dir
        if path == "/" or path == "/test":
            return str(self.test_dir)
        
        if path.startswith("/test/"):
            local_path = path[5:]  # Remover "/test"
        else:
            local_path = path.lstrip("/")
        
        full_path = self.test_dir / local_path
        return str(full_path)
    
    def list_folder(self, path):
        """Lista contenido de directorio."""
        local_path = self.map_path(path)
        logger.info(f"SFTP list_folder path={path} local={local_path}")
        try:
            items = []
            for item in Path(local_path).iterdir():
                stat = item.stat()
                attrs = paramiko.SFTPAttributes.from_stat(stat)
                attrs.filename = item.name
                items.append(attrs)
            return items
        except FileNotFoundError:
            return paramiko.SFTP_NO_SUCH_FILE
        except Exception as e:
            logger.error(f"Error listing {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def stat(self, path):
        """Obtiene stats de archivo/directorio."""
        local_path = self.map_path(path)
        logger.info(f"SFTP stat path={path} local={local_path}")
        
        try:
            stat = Path(local_path).stat()
            attrs = paramiko.SFTPAttributes.from_stat(stat)
            attrs.filename = Path(local_path).name
            return attrs
        except FileNotFoundError:
            return paramiko.SFTP_NO_SUCH_FILE
        except Exception as e:
            logger.error(f"Error stating {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def open(self, path, flags, attr):
        """Abre archivo para lectura/escritura."""
        local_path = self.map_path(path)
        logger.info(f"SFTP open path={path} local={local_path} flags={flags}")
        
        # Determinar modo (binario)
        if flags & os.O_RDWR:
            mode = "r+b"
        elif flags & os.O_WRONLY:
            mode = "wb"
        else:
            mode = "rb"

        if flags & os.O_APPEND:
            mode = "ab" if "w" in mode else "a+b"
        
        try:
            # Crear directorio padre si no existe
            Path(local_path).parent.mkdir(parents=True, exist_ok=True)
            
            return MockSFTPHandle(path, mode, self)
        except Exception as e:
            logger.error(f"Error opening {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def mkdir(self, path, attr):
        """Crea directorio."""
        local_path = self.map_path(path)
        logger.info(f"SFTP mkdir path={path} local={local_path}")
        
        try:
            Path(local_path).mkdir(parents=True, exist_ok=True)
            logger.info(f"SFTP mkdir created {local_path}")
            return paramiko.SFTP_OK
        except Exception as e:
            logger.error(f"Error creating directory {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def rmdir(self, path):
        """Elimina directorio."""
        local_path = self.map_path(path)
        logger.info(f"SFTP rmdir path={path} local={local_path}")
        
        try:
            Path(local_path).rmdir()
            return paramiko.SFTP_OK
        except OSError as e:
            logger.error(f"Error removing directory {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def remove(self, path):
        """Elimina archivo."""
        local_path = self.map_path(path)
        logger.info(f"SFTP remove path={path} local={local_path}")
        
        try:
            Path(local_path).unlink()
            return paramiko.SFTP_OK
        except FileNotFoundError:
            return paramiko.SFTP_NO_SUCH_FILE
        except Exception as e:
            logger.error(f"Error removing {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def chmod(self, path, mode):
        """Cambia permisos de archivo."""
        local_path = self.map_path(path)
        logger.info(f"SFTP chmod path={path} mode={mode}")
        
        try:
            Path(local_path).chmod(mode)
            return paramiko.SFTP_OK
        except Exception as e:
            logger.error(f"Error chmod {path}: {e}")
            return paramiko.SFTP_FAILURE
    
    def session_ended(self):
        """Limpia recursos al finalizar la sesión."""
        try:
            self.finish()
        finally:
            super().session_ended()

    def session_started(self):
        logger.info("SFTP session started")
        super().session_started()
    
    def finish(self):
        """Hook para limpiar instancias cuando el server cierra."""
        if self in MockSFTPServerInterface.active_instances:
            MockSFTPServerInterface.active_instances.remove(self)

    @classmethod
    def cleanup_instances(cls):
        """Limpia cualquier instancia activa."""
        for instance in list(cls.active_instances):
            try:
                instance.finish()
            except Exception:
                pass
        cls.active_instances.clear()

class MockSSHServer(paramiko.ServerInterface):
    """Servidor SSH para el mock SFTP."""
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
    
    def check_auth_password(self, username, password):
        if username == self.username and password == self.password:
            return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED
    
    def check_channel_request(self, kind, chanid):
        if kind == 'session':
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


class MockSFTPServer:
    """Servidor SFTP mock que corre en thread separado."""
    
    def __init__(self, host="127.0.0.1", port=2222, username="testuser", password="testpass"):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.thread = None
        self.running = False
        self._stop_event = threading.Event()
        self._sock = None
        self._interface_instances = []
        self.base_dir = None
        
        # Generar claves RSA para el servidor
        self.host_key = paramiko.RSAKey.generate(2048)

    def start(self):
        """Inicia el servidor SFTP en un thread separado."""
        if self.running:
            return

        # Preparar directorio base limpio para esta sesión
        if self.base_dir and Path(self.base_dir).exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)
        self.base_dir = Path(tempfile.mkdtemp(prefix="sftp_test_root_"))

        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        
        # Esperar a que el servidor esté listo
        max_attempts = 50
        for i in range(max_attempts):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((self.host, self.port))
                sock.close()
                if result == 0:
                    self.running = True
                    logger.info(f"Mock SFTP server started on {self.host}:{self.port}")
                    return
            except:
                pass
            time.sleep(0.1)
        
        raise Exception("Failed to start mock SFTP server")
    
    def _run_server(self):
        """Función que corre el servidor en el thread."""
        try:
            # Crear socket del servidor
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.bind((self.host, self.port))
                sock.listen(5)
                sock.settimeout(1.0)
                self._sock = sock
                
                while not self._stop_event.is_set():
                    try:
                        client, addr = sock.accept()
                    except socket.timeout:
                        continue
                    except OSError:
                        if self._stop_event.is_set():
                            break
                        raise

                    logger.info(f"Mock SFTP client connected from {addr}")

                    transport = None
                    channel = None
                    try:
                        transport = paramiko.Transport(client)
                        transport.add_server_key(self.host_key)

                        # Configurar servidor SSH
                        ssh_server = MockSSHServer(
                            self.username,
                            self.password,
                        )
                        transport.set_subsystem_handler(
                            "sftp",
                            paramiko.SFTPServer,
                            MockSFTPServerInterface,
                            base_dir=str(self.base_dir),
                        )
                        transport.start_server(server=ssh_server)

                        # Esperar autenticación / canal
                        channel = transport.accept(20)
                        if channel is None:
                            transport.close()
                            continue

                        # Mantener la conexión mientras el canal siga activo
                        while (
                            not self._stop_event.is_set()
                            and transport.is_active()
                            and not channel.closed
                        ):
                            time.sleep(0.1)

                    except Exception as e:
                        if not self._stop_event.is_set():
                            logger.exception("Error in mock SFTP server loop")
                        continue
                    finally:
                        MockSFTPServerInterface.cleanup_instances()
                        if transport:
                            transport.close()
                        try:
                            client.close()
                        except OSError:
                            pass
        except Exception as e:
            logger.error(f"Failed to start mock SFTP server: {e}")
        finally:
            self.running = False
            self._sock = None
            for interface in self._interface_instances:
                try:
                    if hasattr(interface, "base_dir") and Path(interface.base_dir).exists():
                        # Intentar limpiar el directorio temporal
                        shutil.rmtree(interface.base_dir, ignore_errors=True)
                except Exception as cleanup_err:
                    logger.warning(f"Error cleaning mock SFTP directory: {cleanup_err}")
            self._interface_instances.clear()
    
    def stop(self):
        """Detiene el servidor SFTP."""
        self.running = False
        self._stop_event.set()
        if self._sock:
            try:
                self._sock.close()
            except OSError:
                pass
        if self.thread:
            self.thread.join(timeout=5)
            self.thread = None
        if self.base_dir and Path(self.base_dir).exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)

def get_free_port():
    """Obtiene un puerto libre."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

if __name__ == "__main__":
    # Test básico del servidor mock
    server = MockSFTPServer(port=get_free_port())
    try:
        server.start()
        print(f"Mock SFTP server running on port {server.port}")
        print("Press Ctrl+C to stop")
        
        # Mantener corriendo
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping mock SFTP server...")
        server.stop()
