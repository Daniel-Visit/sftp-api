#!/usr/bin/env python3
"""
Test simple para validar que la API funciona sin mock server complejo.
"""

import sys
import os

# Agregar el directorio actual al path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test: Verificar que todos los imports funcionan."""
    try:
        from app import app, get_settings
        from test_config import TestSettings
        print("✅ Imports básicos funcionan")
        return True
    except Exception as e:
        print(f"❌ Error en imports: {e}")
        return False

def test_settings():
    """Test: Verificar configuración."""
    try:
        from test_config import TestSettings
        settings = TestSettings()
        assert settings.API_KEY == "test-api-key-12345"
        assert settings.SFTP_HOST == "127.0.0.1"
        assert settings.SFTP_PORT == 2222
        print("✅ Configuración de testing funciona")
        return True
    except Exception as e:
        print(f"❌ Error en configuración: {e}")
        return False

def test_fastapi_app():
    """Test: Verificar que FastAPI app se crea correctamente."""
    try:
        from app import app
        assert app.title == "SFTP API"
        assert app.version == "1.2.0"
        print("✅ FastAPI app creada correctamente")
        return True
    except Exception as e:
        print(f"❌ Error en FastAPI app: {e}")
        return False

def main():
    """Ejecuta tests simples."""
    print("🧪 Ejecutando tests simples...")
    
    tests = [
        test_imports,
        test_settings,
        test_fastapi_app,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 Resultados:")
    print(f"✅ Pasaron: {passed}")
    print(f"❌ Fallaron: {failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
