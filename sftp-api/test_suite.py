#!/usr/bin/env python3
"""
Suite completa de tests automatizados para la API SFTP.
Usa un cliente SFTP fake (filesystem local) y TestClient de FastAPI.
"""

import os
import sys
import time
import tempfile
import shutil
from pathlib import Path
from io import BytesIO

# Agregar el directorio actual al path para imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
import paramiko

# Importar nuestros módulos
from app import app, set_settings_for_testing
from test_config import TestSettings


class FakeSFTPFile:
    """Wrapper simple para manejar archivos en el fake client."""

    def __init__(self, path, mode):
        self._file = open(path, mode)

    def read(self, *args, **kwargs):
        return self._file.read(*args, **kwargs)

    def write(self, data):
        return self._file.write(data)

    def close(self):
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def __iter__(self):
        self._file.seek(0)
        return self

    def __next__(self):
        chunk = self._file.read(32768)
        if not chunk:
            raise StopIteration
        return chunk


class FakeSFTPClient:
    """Implementación mínima de SFTP sobre el filesystem local."""

    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)

    def _resolve(self, path):
        local = Path(path)
        if not local.is_absolute():
            local = self.base_dir / path.lstrip("/")
        return local

    def listdir(self, path):
        return os.listdir(self._resolve(path))

    def listdir_attr(self, path):
        local = self._resolve(path)
        items = []
        for entry in os.scandir(local):
            attrs = paramiko.SFTPAttributes.from_stat(entry.stat(follow_symlinks=False))
            attrs.filename = entry.name
            items.append(attrs)
        return items

    def stat(self, path):
        local = self._resolve(path)
        stat_result = local.stat()
        attrs = paramiko.SFTPAttributes.from_stat(stat_result)
        attrs.filename = local.name
        return attrs

    def mkdir(self, path):
        self._resolve(path).mkdir()

    def rmdir(self, path):
        self._resolve(path).rmdir()

    def remove(self, path):
        self._resolve(path).unlink()

    def chmod(self, path, mode):
        os.chmod(self._resolve(path), mode)

    def open(self, path, mode):
        local = self._resolve(path)
        local.parent.mkdir(parents=True, exist_ok=True)
        return FakeSFTPFile(local, mode)

    def close(self):
        pass

class TestRunner:
    """Ejecutor de tests con reporte detallado."""
    
    def __init__(self):
        self.tests_passed = 0
        self.tests_failed = 0
        self.failed_tests = []
        self.base_dir = None
        self.original_sftp_connect = None
        self.client = None
        
    def setup(self):
        """Configura el entorno de testing."""
        print("🔧 Configurando entorno de testing...")
        
        # Crear base temporal y poblarla con archivos de ejemplo
        self.base_dir = Path(tempfile.mkdtemp(prefix="sftp_fake_"))
        test_root = self.base_dir / "test"
        test_root.mkdir(parents=True, exist_ok=True)
        (test_root / "file1.txt").write_text("Hello World")
        (test_root / "file2.txt").write_text("Test content")

        # Ajustar configuración de la app
        TestSettings.BASE_DIR = str(self.base_dir)
        test_settings = TestSettings()
        set_settings_for_testing(test_settings)

        # Parchear sftp_connect para usar el fake client
        import app as app_module
        self.original_sftp_connect = app_module.sftp_connect

        def fake_connect():
            return FakeSFTPClient(self.base_dir)

        app_module.sftp_connect = fake_connect

        # Crear cliente HTTP de testing
        self.client = TestClient(app)
        
        print("✅ Entorno configurado")
        
    def teardown(self):
        """Limpia el entorno de testing."""
        import app as app_module
        if self.original_sftp_connect:
            app_module.sftp_connect = self.original_sftp_connect
        if self.base_dir and self.base_dir.exists():
            shutil.rmtree(self.base_dir, ignore_errors=True)
        print("🧹 Entorno limpiado")
    
    def run_test(self, test_name, test_func):
        """Ejecuta un test individual y registra el resultado."""
        try:
            print(f"🧪 Ejecutando: {test_name}")
            test_func()
            print(f"✅ PASÓ: {test_name}")
            self.tests_passed += 1
            return True
        except Exception as e:
            print(f"❌ FALLÓ: {test_name}")
            print(f"   Error: {str(e)}")
            self.tests_failed += 1
            self.failed_tests.append((test_name, str(e)))
            return False
    
    def test_healthcheck(self):
        """Test: Healthcheck sin autenticación."""
        response = self.client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert data["service"] == "sftp-api"
    
    def test_auth_invalid_missing_key(self):
        """Test: Endpoint protegido sin API key."""
        response = self.client.get("/list")
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key" in data["detail"]
    
    def test_auth_invalid_wrong_key(self):
        """Test: Endpoint protegido con API key incorrecta."""
        response = self.client.get("/list", headers={"X-API-Key": "wrong-key"})
        assert response.status_code == 401
        data = response.json()
        assert "Invalid API key" in data["detail"]
    
    def test_list_valid(self):
        """Test: Listar directorio con API key válida."""
        response = self.client.get("/list?path=/", headers={"X-API-Key": TestSettings.API_KEY})
        assert response.status_code == 200
        data = response.json()
        assert "path" in data
        assert "items" in data
        assert isinstance(data["items"], list)
    
    def test_list_path_traversal(self):
        """Test: Path traversal debe ser bloqueado."""
        response = self.client.get("/list?path=../../etc/passwd", headers={"X-API-Key": TestSettings.API_KEY})
        assert response.status_code == 400
        data = response.json()
        assert "Ruta fuera de BASE_DIR" in data["detail"]
    
    def test_mkdir_valid(self):
        """Test: Crear directorio válido."""
        test_dir = f"/test-api-{int(time.time())}"
        response = self.client.post(
            "/mkdir",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"path": test_dir}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "created" in data
        
        # Verificar que el directorio existe listándolo
        list_response = self.client.get("/list?path=/", headers={"X-API-Key": TestSettings.API_KEY})
        assert list_response.status_code == 200
    
    def test_upload_valid(self):
        """Test: Subir archivo válido."""
        test_content = f"Test content {time.time()}"
        test_file = BytesIO(test_content.encode())
        
        response = self.client.post(
            "/upload",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"remote_path": "/test-file.txt"},
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] == True
        assert "path" in data
    
    def test_upload_invalid_ends_with_slash(self):
        """Test: Upload con remote_path terminando en / debe fallar."""
        test_content = "Test content"
        test_file = BytesIO(test_content.encode())
        
        response = self.client.post(
            "/upload",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"remote_path": "/test-dir/"},
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        assert response.status_code == 400
        data = response.json()
        assert "remote_path debe ser un ARCHIVO" in data["detail"]
    
    def test_download_valid(self):
        """Test: Descargar archivo existente."""
        # Primero subir un archivo
        test_content = "Download test content"
        test_file = BytesIO(test_content.encode())
        
        upload_response = self.client.post(
            "/upload",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"remote_path": "/download-test.txt"},
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        assert upload_response.status_code == 200
        
        # Ahora descargarlo
        download_response = self.client.get(
            "/download?remote_path=/download-test.txt",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert download_response.status_code == 200
        assert download_response.content.decode() == test_content
    
    def test_download_not_found(self):
        """Test: Descargar archivo inexistente."""
        response = self.client.get(
            "/download?remote_path=/nonexistent.txt",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert response.status_code == 404
        data = response.json()
        assert "No existe" in data["detail"]
    
    def test_delete_file_valid(self):
        """Test: Eliminar archivo existente."""
        # Primero subir un archivo
        test_content = "File to delete"
        test_file = BytesIO(test_content.encode())
        
        upload_response = self.client.post(
            "/upload",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"remote_path": "/file-to-delete.txt"},
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        assert upload_response.status_code == 200
        
        # Ahora eliminarlo
        delete_response = self.client.delete(
            "/delete-file?remote_path=/file-to-delete.txt",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["ok"] == True
        assert "deleted" in data
    
    def test_delete_file_not_found(self):
        """Test: Eliminar archivo inexistente."""
        response = self.client.delete(
            "/delete-file?remote_path=/nonexistent.txt",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert response.status_code == 404
        data = response.json()
        assert "No existe" in data["detail"]
    
    def test_delete_dir_empty(self):
        """Test: Eliminar directorio vacío."""
        # Primero crear un directorio
        test_dir = f"/empty-dir-{int(time.time())}"
        mkdir_response = self.client.post(
            "/mkdir",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"path": test_dir}
        )
        assert mkdir_response.status_code == 200
        
        # Ahora eliminarlo
        delete_response = self.client.delete(
            f"/delete-dir?remote_path={test_dir}",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["ok"] == True
        assert data["recursive"] == False
    
    def test_delete_dir_with_files(self):
        """Test: Eliminar directorio con archivos (recursivo)."""
        # Crear directorio con archivo
        test_dir = f"/dir-with-files-{int(time.time())}"
        mkdir_response = self.client.post(
            "/mkdir",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"path": test_dir}
        )
        assert mkdir_response.status_code == 200
        
        # Subir archivo al directorio
        test_content = "File in directory"
        test_file = BytesIO(test_content.encode())
        
        upload_response = self.client.post(
            "/upload",
            headers={"X-API-Key": TestSettings.API_KEY},
            data={"remote_path": f"{test_dir}/file.txt"},
            files={"file": ("test.txt", test_file, "text/plain")}
        )
        assert upload_response.status_code == 200
        
        # Intentar eliminar sin recursive (debe fallar)
        delete_response = self.client.delete(
            f"/delete-dir?remote_path={test_dir}",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert delete_response.status_code == 400
        data = delete_response.json()
        assert "Directorio no vacío" in data["detail"]
        
        # Eliminar con recursive (debe funcionar)
        delete_recursive_response = self.client.delete(
            f"/delete-dir?remote_path={test_dir}&recursive=true",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert delete_recursive_response.status_code == 200
        data = delete_recursive_response.json()
        assert data["ok"] == True
        assert data["recursive"] == True
    
    def test_delete_base_dir_protection(self):
        """Test: Intentar eliminar BASE_DIR debe fallar."""
        response = self.client.delete(
            "/delete-dir?remote_path=/&recursive=true",
            headers={"X-API-Key": TestSettings.API_KEY}
        )
        assert response.status_code == 400
        data = response.json()
        assert "No se puede eliminar BASE_DIR" in data["detail"]
    
    def run_all_tests(self):
        """Ejecuta todos los tests y reporta resultados."""
        print("🧪 Iniciando suite completa de tests...")
        
        # Lista de todos los tests
        tests = [
            ("Healthcheck", self.test_healthcheck),
            ("Auth - Sin API key", self.test_auth_invalid_missing_key),
            ("Auth - API key incorrecta", self.test_auth_invalid_wrong_key),
            ("List - Válido", self.test_list_valid),
            ("List - Path traversal", self.test_list_path_traversal),
            ("Mkdir - Válido", self.test_mkdir_valid),
            ("Upload - Válido", self.test_upload_valid),
            ("Upload - Termina en /", self.test_upload_invalid_ends_with_slash),
            ("Download - Válido", self.test_download_valid),
            ("Download - No existe", self.test_download_not_found),
            ("Delete File - Válido", self.test_delete_file_valid),
            ("Delete File - No existe", self.test_delete_file_not_found),
            ("Delete Dir - Vacío", self.test_delete_dir_empty),
            ("Delete Dir - Con archivos", self.test_delete_dir_with_files),
            ("Protección BASE_DIR", self.test_delete_base_dir_protection),
        ]
        
        # Ejecutar cada test
        for test_name, test_func in tests:
            self.run_test(test_name, test_func)
        
        # Reportar resultados
        total_tests = self.tests_passed + self.tests_failed
        print(f"\n📊 RESUMEN DE TESTS:")
        print(f"✅ Pasaron: {self.tests_passed}/{total_tests}")
        print(f"❌ Fallaron: {self.tests_failed}/{total_tests}")
        
        if self.failed_tests:
            print(f"\n🔍 TESTS QUE FALLARON:")
            for test_name, error in self.failed_tests:
                print(f"  - {test_name}: {error}")
        
        success_rate = (self.tests_passed / total_tests) * 100 if total_tests > 0 else 0
        print(f"\n🎯 TASA DE ÉXITO: {success_rate:.1f}%")
        
        return self.tests_failed == 0

def main():
    """Función principal."""
    runner = TestRunner()
    
    try:
        runner.setup()
        success = runner.run_all_tests()
        return 0 if success else 1
    except Exception as e:
        print(f"❌ ERROR FATAL: {e}")
        return 1
    finally:
        runner.teardown()

if __name__ == "__main__":
    exit(main())
