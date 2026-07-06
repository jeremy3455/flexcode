# Agente de IA - Implementación

## Descripción General

Agente conversacional con interfaz CLI y web, soporte para múltiples proveedores de LLM (Ollama, OpenAI, Groq), herramientas integradas vía function calling automático, autenticación de usuarios y gestión de sesiones persistentes.

---

## Arquitectura del Proyecto

```
agente de IA/
├── conversational_agent/           # Núcleo del agente
│   ├── agent.py                   # Clase Agent + AgentConfig + Function Calling
│   └── memory.py                  # Message + ConversationMemory
├── tools/                          # Herramientas del agente
│   ├── calculator.py              # Calculadora matemática segura (AST)
│   ├── code_executor.py           # Ejecución de Python en subproceso
│   ├── datetime_tool.py           # Fecha y hora actual
│   ├── file_reader.py             # Lector de archivos del sistema
│   ├── image_gen.py               # Generación de imágenes (Pollinations.ai)
│   ├── web_search.py              # Búsqueda web (DuckDuckGo)
│   └── __init__.py                # Exportación de todas las herramientas
├── tests/                          # Tests automatizados
│   ├── test_agent.py              # Tests del agente (mocks)
│   ├── test_api.py                # Tests de la API REST
│   ├── test_calculator.py         # Tests de la calculadora
│   ├── test_database.py           # Tests de la base de datos
│   ├── test_datetime_tool.py      # Tests de fecha/hora
│   ├── test_file_reader.py        # Tests de lectura de archivos
│   ├── test_memory.py             # Tests de memoria conversacional
│   └── __init__.py
├── templates/
│   └── index.html                 # Interfaz web SPA con auth
├── database.py                    # Capa de persistencia SQLite
├── main.py                        # Entrada CLI
├── web_app.py                     # Servidor FastAPI con auth JWT
├── IMPLEMENTACION.md              # Este documento
├── FIXES.md                       # Registro de cambios y correcciones
├── requirements.txt               # Dependencias
├── setup_ollama.ps1               # Script de instalación automatizada
├── .env.example                   # Template de configuración
└── conversations.db               # Base de datos SQLite
```

---

## Componentes Implementados

### 1. Núcleo del Agente (`conversational_agent/`)

| Archivo | Funcionalidad |
|---------|---------------|
| `agent.py` | Clase principal `Agent` con `AgentConfig`, cliente OpenAI-compatible, memoria conversacional, **function calling automático** (el LLM decide qué herramienta usar según el contexto), y comandos explícitos `/buscar`, `/search`, `/codigo`, `/code`, `/imagen`, `/image` como fallback |
| `memory.py` | `ConversationMemory` basada en `deque` con límite configurable (default 50 mensajes), dataclass `Message` |

### 2. Herramientas (`tools/`)

| Función | Archivo | Descripción | Activación |
|---------|---------|-------------|------------|
| `web_search` | `web_search.py` | Búsqueda en DuckDuckGo, hasta 5 resultados con título, snippet y URL | Automática (LLM) + `/buscar` / `/search` |
| `execute_python` | `code_executor.py` | Ejecuta código Python en subproceso con timeout 10s, bloquea `input()` | Automática (LLM) + `/codigo` / `/code` |
| `generate_image` | `image_gen.py` | Genera imágenes vía Pollinations.ai, devuelve URL pública | Automática (LLM) + `/imagen` / `/image` |
| `calculate` | `calculator.py` | Evaluación segura de expresiones matemáticas vía AST (+, -, *, /, //, %, **, abs, round, int, float, min, max, pi, e) | Automática (LLM) |
| `get_current_datetime` | `datetime_tool.py` | Fecha y hora actual con formato configurable (strftime) | Automática (LLM) |
| `read_file` | `file_reader.py` | Lectura segura de archivos (límite 1MB, UTF-8) | Automática (LLM) |

### 3. Function Calling Automático

- El agente envía los schemas de las 6 herramientas en cada request a la API
- El LLM decide autónomamente qué herramienta invocar según la conversación
- Las herramientas: `web_search`, `execute_python`, `generate_image`, `calculate`, `get_current_datetime`, `read_file`
- Cuando el LLM solicita una herramienta, el agente la ejecuta y realimenta el resultado al LLM para una respuesta final en lenguaje natural
- Los comandos explícitos (`/buscar`, `/codigo`, `/imagen`) se mantienen como fallback compatible

### 4. Autenticación de Usuarios

- **Backend**: JWT con algoritmo HS256, expiración 24h, secreto configurable vía `JWT_SECRET`
- **Registro**: `POST /register` con username + password (hash PBKDF2 + salt, sin dependencias externas)
- **Login**: `POST /login` devuelve token JWT
- **Verificación**: `GET /me` protegido con Bearer token
- **Protección**: Endpoints de chat y sesiones filtran por `user_id`
- **Frontend**: Pantalla de login/registro con tabs, token en localStorage, renovación automática, badge de usuario y botón "Salir"
- **Sesiones**: Ligadas al usuario autenticado; cada usuario solo ve sus propias conversaciones

### 5. Interfaz de Usuario

#### CLI (`main.py`)
- REPL interactivo
- Comandos: `salir`/`exit`/`quit`, `reset`
- Auto-detección y arranque de Ollama
- Carga de configuración desde `.env`

#### Web UI (`web_app.py` + `templates/index.html`)
- **Backend**: FastAPI en puerto 8001 con hot-reload
- **Endpoints**: `POST /chat`, `POST /register`, `POST /login`, `GET /me`, `POST /sessions`, `POST /sessions/guest`, `GET /sessions`, `GET /sessions/{id}/messages`, `DELETE /sessions/{id}`, `POST /sessions/{id}/save`, `POST /reset`, `GET /`
- **Frontend**: SPA con login/register, diseño dark-mode, sidebar de sesiones, renderizado Markdown, indicador de escritura, chips de acción, selector de idioma, personalidad configurable, notificaciones toast, diseño responsive
- **Idiomas**: ES, EN, PT, FR, DE, IT, JA, ZH + auto-detección
- **Red**: Integración ngrok para URL pública, IP local para acceso LAN, CORS habilitado

### 6. Persistencia (`database.py`)

- SQLite con tablas `users`, `sessions` y `messages`
- CRUD completo de usuarios y sesiones por usuario
- Migración automática de esquema (columna `user_id` añadida si versiones anteriores)
- Sesiones invitadas (en memoria) con opción de guardar a persistente
- Auto-generación de título de sesión a partir del primer mensaje

### 7. Tests Automatizados (`tests/`)

45 tests con pytest, divididos en:

| Archivo | Tests | Cobertura |
|---------|-------|-----------|
| `test_calculator.py` | 7 | Aritmética básica, funciones, constantes, expresiones complejas, seguridad, errores |
| `test_datetime_tool.py` | 4 | Formatos por defecto y personalizados |
| `test_file_reader.py` | 4 | Archivo existente, no encontrado, directorio, límite de tamaño |
| `test_memory.py` | 5 | Add, límite de mensajes, clear, last, len |
| `test_agent.py` | 7 | Respuesta normal, comandos explícitos, load_messages, reset, tool calling (mocks) |
| `test_database.py` | 7 | CRUD usuarios y sesiones |
| `test_api.py` | 11 | Register, login, me, sesiones autenticadas, guest, index |

Ejecución: `python -m pytest tests/ -v`

### 8. Configuración e Instalación

- `.env.example` con 3 proveedores: Ollama, OpenAI, Groq
- `setup_ollama.ps1`: instalación automatizada de Ollama + modelo `llama3.2`
- Auto-arranque de Ollama desde CLI si está instalado pero no corriendo

---

## Proveedores de LLM Soportados

| Proveedor | Configuración |
|-----------|---------------|
| Ollama (local) | `base_url=http://localhost:11434/v1`, `model=llama3.2` |
| OpenAI | `api_key=<key>`, `base_url=https://api.openai.com/v1` |
| Groq (gratuito) | `api_key=<key>`, `base_url=https://api.groq.com/openai/v1`, `model=llama3-70b-8192` |
| Cualquier API compatible con OpenAI | `api_key` + `base_url` personalizados |

---

## Dependencias

```
openai>=1.0.0
python-dotenv>=1.0.0
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
duckduckgo_search>=6.0.0
httpx>=0.27.0
pyjwt>=2.0.0
pytest>=9.0.0
```

---

## Próximos Pasos / No Implementado

- Streaming de respuestas en web UI (respuestas token por token)
- Despliegue con Docker (Dockerfile + docker-compose)
- Más herramientas (lectura de URLs, traducción, etc.)
- Integración continua (GitHub Actions)
