#!/usr/bin/env python3
"""
Script para probar la conexión SFTP básica con el servidor real.
Valida credenciales, permisos y operaciones básicas.
"""

import os
import paramiko
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_KEY: str = "change-me"
    SFTP_HOST: str = "127.0.0.1"
    SFTP_PORT: int = 22
    SFTP_USER: str = "user"
    SFTP_PASS: str = "pass"
    BASE_DIR: str = "/home/user"

    class Config:
        env_file = ".env"

def test_sftp_connection():
    """Prueba la conexión SFTP básica."""
    print("🔍 Cargando configuración desde .env...")
    
    if not os.path.exists('.env'):
        print("❌ ERROR: Archivo .env no encontrado")
        print("Copia .env.example a .env y configura tus credenciales")
        return False
    
    settings = Settings()
    
    print(f"📡 Conectando a {settings.SFTP_HOST}:{settings.SFTP_PORT}")
    print(f"👤 Usuario: {settings.SFTP_USER}")
    print(f"📁 Base dir: {settings.BASE_DIR}")
    
    try:
        # Crear transporte SSH
        transport = paramiko.Transport((settings.SFTP_HOST, settings.SFTP_PORT))
        print("🔐 Autenticando...")
        transport.connect(username=settings.SFTP_USER, password=settings.SFTP_PASS)
        
        # Crear cliente SFTP
        sftp = paramiko.SFTPClient.from_transport(transport)
        print("✅ Conexión SFTP exitosa")
        
        # Probar acceso al directorio base
        print(f"📂 Verificando acceso a {settings.BASE_DIR}...")
        try:
            sftp.stat(settings.BASE_DIR)
            print("✅ BASE_DIR accesible")
        except FileNotFoundError:
            print(f"❌ ERROR: BASE_DIR {settings.BASE_DIR} no existe")
            return False
        except PermissionError:
            print(f"❌ ERROR: Sin permisos para acceder a {settings.BASE_DIR}")
            return False
        
        # Listar contenido del directorio base
        print("📋 Listando contenido del directorio base...")
        try:
            items = sftp.listdir_attr(settings.BASE_DIR)
            print(f"✅ Encontrados {len(items)} elementos:")
            for item in items[:5]:  # Mostrar solo los primeros 5
                item_type = "📁" if item.st_mode & 0o040000 else "📄"
                print(f"  {item_type} {item.filename}")
            if len(items) > 5:
                print(f"  ... y {len(items) - 5} más")
        except Exception as e:
            print(f"❌ ERROR listando directorio: {e}")
            return False
        
        # Probar crear un directorio de prueba
        test_dir = f"{settings.BASE_DIR}/test-sftp-api"
        print(f"🧪 Probando creación de directorio: {test_dir}")
        try:
            sftp.mkdir(test_dir)
            print("✅ Creación de directorio exitosa")
            
            # Limpiar: eliminar directorio de prueba
            sftp.rmdir(test_dir)
            print("🧹 Directorio de prueba eliminado")
        except Exception as e:
            print(f"❌ ERROR creando directorio: {e}")
            # Intentar limpiar si existe
            try:
                sftp.rmdir(test_dir)
            except:
                pass
            return False
        
        sftp.close()
        transport.close()
        print("🎉 Todas las pruebas de conexión pasaron exitosamente")
        return True
        
    except paramiko.AuthenticationException:
        print("❌ ERROR: Autenticación fallida")
        print("Verifica usuario y contraseña en .env")
        return False
    except paramiko.SSHException as e:
        print(f"❌ ERROR SSH: {e}")
        return False
    except ConnectionRefusedError:
        print("❌ ERROR: Conexión rechazada")
        print(f"Verifica que {settings.SFTP_HOST}:{settings.SFTP_PORT} esté accesible")
        return False
    except Exception as e:
        print(f"❌ ERROR inesperado: {e}")
        return False

if __name__ == "__main__":
    success = test_sftp_connection()
    exit(0 if success else 1)
