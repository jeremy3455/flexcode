# Registro de Cambios y Correcciones

## [1.0.1] - 2026-07-05

### Añadido

#### Function Calling Automático
- Implementado envío de `tools` en requests a la API compatible con OpenAI
- El LLM decide autónomamente qué herramienta usar según la conversación
- Manejo de `tool_calls` con ejecución de herramienta y realimentación al LLM
- Comandos explícitos `/buscar`, `/codigo`, `/imagen` mantenidos como fallback
- System prompt actualizado con la lista de herramientas disponibles

#### Nuevas Herramientas
- **`tools/calculator.py`**: Calculadora segura basada en AST de Python
  - Soporta: +, -, *, /, //, %, **, abs, round, int, float, min, max, pi, e
  - Bloquea ejecución de código arbitrario, imports, variables no definidas
- **`tools/datetime_tool.py`**: Obtiene fecha/hora actual con formato strftime
- **`tools/file_reader.py`**: Lee archivos del sistema (límite 1MB, UTF-8)

#### Autenticación de Usuarios
- **`database.py`**: Nueva tabla `users` + migración automática de columna `user_id` en `sessions`
- **`web_app.py`**: Endpoints `POST /register`, `POST /login`, `GET /me` con JWT
  - Hash de contraseñas con PBKDF2 + salt (sin dependencias externas)
  - JWT con algoritmo HS256, expiración 24h, secreto configurable
  - Dependencia `get_current_user` para proteger endpoints
- **`templates/index.html`**: Pantalla de login/register, token en localStorage, badge de usuario, botón de salir

#### Tests Automatizados
Estructura completa de tests con pytest (45 tests):

| Archivo | Tests | Objetivo |
|---------|-------|----------|
| `tests/test_calculator.py` | 7 | Aritmética, funciones, constantes, seguridad, errores |
| `tests/test_datetime_tool.py` | 4 | Formatos de fecha/hora |
| `tests/test_file_reader.py` | 4 | Lectura de archivos, errores, límites |
| `tests/test_memory.py` | 5 | Operaciones de memoria conversacional |
| `tests/test_agent.py` | 7 | Agent con mocks, commands, tool calling |
| `tests/test_database.py` | 7 | CRUD usuarios y sesiones |
| `tests/test_api.py` | 11 | Endpoints REST autenticados y públicos |

### Corregido

#### Calculator: `ast.Num` deprecated en Python 3.14
- **Síntoma**: `module 'ast' has no attribute 'Num'`
- **Causa**: `ast.Num`, `ast.Str`, etc. fueron eliminados en Python 3.14 (reemplazados por `ast.Constant`)
- **Solución**: Eliminada la comprobación de `ast.Num`, usando solo `ast.Constant`

#### Calculator: `sum()` con argumentos variables
- **Síntoma**: `sum() takes at most 2 arguments (3 given)`
- **Causa**: La función `sum()` de Python espera un iterable como primer argumento, no argumentos variables
- **Solución**: Eliminada `sum` de `_ALLOWED_FUNCS` (no compatible con la interfaz de args)

#### Base de datos: columna `user_id` faltante
- **Síntoma**: `OperationalError: no such column: user_id`
- **Causa**: `CREATE TABLE IF NOT EXISTS` no altera tablas existentes; la base de datos tenía el esquema anterior
- **Solución**: Añadida migración en `init_db()` que verifica si `user_id` existe y la añade con `ALTER TABLE`

#### Base de datos: Foreign Key constraint con sesiones sin usuario
- **Síntoma**: `FOREIGN KEY constraint failed` al crear sesión sin `user_id`
- **Causa**: `FOREIGN KEY (user_id) REFERENCES users(id)` exigía que `''` existiera en `users`
- **Solución**: Eliminada la constraint FK en `user_id` (soportamos sesiones sin usuario)

#### Tests: Base de datos en memoria por conexión
- **Síntoma**: `no such table` en tests database y API
- **Causa**: SQLite `:memory:` crea una base separada por cada conexión
- **Solución**: Cambiado a archivo temporal (`tempfile`) para compartir la base entre conexiones

#### Tests: PermissionError al limpiar archivo temporal
- **Síntoma**: `PermissionError: El proceso no tiene acceso al archivo`
- **Causa**: SQLite mantenía el archivo bloqueado al intentar eliminarlo
- **Solución**: Forzar cierre de conexiones (`conn.close()`) antes de `os.unlink()`

#### Tests: Dependencia `pyjwt` faltante
- **Síntoma**: `ModuleNotFoundError: No module named 'jwt'`
- **Causa**: `pyjwt` no estaba en `requirements.txt`
- **Solución**: Añadido `pyjwt>=2.0.0` a requirements.txt

---

### Técnico

- **Dependencias nuevas**: `pyjwt>=2.0.0`, `pytest>=9.0.0`
- **Versión de Python**: Compatible con Python 3.14 (AST API actualizada)
- **Base de datos**: Migración automática de esquema para usuarios existentes
