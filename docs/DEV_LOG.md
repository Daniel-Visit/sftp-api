# Dev Log

## 2025-10-16
- Creado `FakeSFTPClient` para pruebas locales, reemplazando la dependencia del mock SFTP basado en Paramiko.
- Ajustada la suite (`python test_suite.py`) para usar el stub y validar todos los endpoints (resultados: 15/15 tests OK).
- Limpieza automática: el directorio temporal y el monkeypatch se restauran en `teardown`.
