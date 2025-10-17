#!/usr/bin/env python3
"""
Configuración de testing para la API SFTP.
Proporciona settings para usar con el mock server sin depender de .env
"""

import os
import tempfile
from pathlib import Path

class TestSettings:
    """Configuración para tests con mock server."""
    
    # API Configuration
    API_KEY = "test-api-key-12345"
    
    # Mock SFTP Server Configuration
    SFTP_HOST = "127.0.0.1"
    SFTP_PORT = 2222  # Se asignará dinámicamente un puerto libre
    SFTP_USER = "testuser"
    SFTP_PASS = "testpass"
    BASE_DIR = "/test"  # Ruta en el mock server
    
    @classmethod
    def get_free_port(cls):
        """Obtiene un puerto libre para el mock server."""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    @classmethod
    def update_port(cls, port):
        """Actualiza el puerto del mock server."""
        cls.SFTP_PORT = port
    
    @classmethod
    def to_dict(cls):
        """Convierte la configuración a diccionario."""
        return {
            "API_KEY": cls.API_KEY,
            "SFTP_HOST": cls.SFTP_HOST,
            "SFTP_PORT": cls.SFTP_PORT,
            "SFTP_USER": cls.SFTP_USER,
            "SFTP_PASS": cls.SFTP_PASS,
            "BASE_DIR": cls.BASE_DIR,
        }

# Configuración de producción (para cuando se use con servidor real)
class ProductionSettings:
    """Configuración para producción (requiere .env)."""
    
    API_KEY = "change-me"
    SFTP_HOST = "127.0.0.1"
    SFTP_PORT = 22
    SFTP_USER = "user"
    SFTP_PASS = "pass"
    BASE_DIR = "/home/user"

def get_test_settings():
    """Retorna configuración para testing."""
    return TestSettings

def get_production_settings():
    """Retorna configuración para producción."""
    return ProductionSettings
