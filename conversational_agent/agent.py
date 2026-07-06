import json
import re
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from .memory import ConversationMemory
from tools import web_search, execute_python, generate_image, calculate, get_current_datetime, read_file, generate_pdf, generate_docx, generate_xlsx


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Busca informacion actualizada en internet. Usa esta herramienta cuando el usuario pregunte por noticias, datos recientes, o cualquier tema que requiera informacion actualizada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "La consulta de busqueda, clara y concisa."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Ejecuta codigo Python de forma segura. Usa esta herramienta cuando el usuario pida hacer calculos, procesar datos, o ejecutar cualquier codigo Python.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "El codigo Python a ejecutar."
                    }
                },
                "required": ["code"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Genera una imagen a partir de una descripcion textual. Usa esta herramienta cuando el usuario pida crear, dibujar, o generar una imagen.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "La descripcion de la imagen a generar."
                    }
                },
                "required": ["prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Realiza calculos matematicos de forma segura. Soporta operaciones basicas (+, -, *, /, //, %, **), funciones (abs, round, int, float, min, max, sum) y constantes (pi, e). Usa esta herramienta cuando el usuario pida hacer cuentas o resolver expresiones matematicas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "La expresion matematica a evaluar, ej: '2 + 2', 'pi * 5**2', 'abs(-10)'."
                    }
                },
                "required": ["expression"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Obtiene la fecha y hora actual del sistema. Usa esta herramienta cuando el usuario pregunte que dia es, que hora es, o cualquier consulta sobre el momento actual.",
            "parameters": {
                "type": "object",
                "properties": {
                    "format": {
                        "type": "string",
                        "description": "Formato de fecha opcional (formato strftime de Python). Por defecto: '%Y-%m-%d %H:%M:%S'.",
                        "default": "%Y-%m-%d %H:%M:%S"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Lee el contenido de un archivo del sistema. Usa esta herramienta cuando el usuario pida leer, mostrar, o inspeccionar el contenido de un archivo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "La ruta del archivo a leer."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_pdf",
            "description": "Genera un archivo PDF con titulo y contenido de texto. Usa esta herramienta cuando el usuario pida crear un PDF, un documento formal, un reporte, o un archivo PDF.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "El titulo del documento PDF."
                    },
                    "content": {
                        "type": "string",
                        "description": "El contenido del documento en texto plano, separado por saltos de linea."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Nombre sugerido para el archivo (opcional, sin extension)."
                    }
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_docx",
            "description": "Genera un archivo Word (.docx) con titulo y contenido. Usa esta herramienta cuando el usuario pida crear un documento de Word, un archivo .docx, una carta formal, o un informe editable.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "El titulo del documento Word."
                    },
                    "content": {
                        "type": "string",
                        "description": "El contenido del documento en texto plano, separado por saltos de linea."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Nombre sugerido para el archivo (opcional, sin extension)."
                    }
                },
                "required": ["title", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "generate_xlsx",
            "description": "Genera un archivo Excel (.xlsx) con encabezados y filas de datos. Usa esta herramienta cuando el usuario pida crear una tabla, una hoja de calculo, un Excel, o datos organizados en columnas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "headers": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Lista de nombres de columnas (ej: ['Nombre', 'Edad', 'Ciudad'])."
                    },
                    "rows": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "description": "Lista de filas, donde cada fila es una lista de valores (ej: [['Ana', '30', 'Lima'], ['Luis', '25', 'Bogota']])."
                    },
                    "filename": {
                        "type": "string",
                        "description": "Nombre sugerido para el archivo (opcional, sin extension)."
                    }
                },
                "required": ["headers", "rows"]
            }
        }
    },
]

TOOL_MAP = {
    "web_search": web_search,
    "execute_python": execute_python,
    "generate_image": generate_image,
    "calculate": calculate,
    "get_current_datetime": get_current_datetime,
    "read_file": read_file,
    "generate_pdf": generate_pdf,
    "generate_docx": generate_docx,
    "generate_xlsx": generate_xlsx,
}


@dataclass
class AgentConfig:
    system_prompt: str = (
        "Eres un asistente conversacional amable y servicial. "
        "Respondes en el mismo idioma en que te hablan. "
        "Tienes acceso a las siguientes herramientas que puedes usar cuando sea necesario:\n"
        "- web_search: Buscar informacion actualizada en internet.\n"
        "- execute_python: Ejecutar codigo Python.\n"
        "- generate_image: Generar imagenes a partir de una descripcion.\n"
        "- calculate: Realizar calculos matematicos.\n"
        "- get_current_datetime: Obtener la fecha y hora actual.\n"
        "- read_file: Leer el contenido de archivos.\n"
        "- generate_pdf: Generar documentos PDF.\n"
        "- generate_docx: Generar documentos Word (.docx).\n"
        "- generate_xlsx: Generar archivos Excel (.xlsx).\n\n"
        "Cuando el usuario te pida algo que requiera una herramienta, usala. "
        "Si no necesitas herramienta, responde normalmente."
    )
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    max_history: int = 50


class Agent:
    def __init__(self, config: Optional[AgentConfig] = None):
        self.config = config or AgentConfig()
        self.memory = ConversationMemory(max_messages=self.config.max_history)

        client_kwargs = {}
        if self.config.api_key:
            client_kwargs["api_key"] = self.config.api_key
        if self.config.base_url:
            client_kwargs["base_url"] = self.config.base_url

        self._client = OpenAI(**client_kwargs)

    def ask(self, message: str) -> str:
        explicit_reply = self._execute_explicit_command(message)
        if explicit_reply is not None:
            self.memory.add("user", message)
            self.memory.add("assistant", explicit_reply)
            return explicit_reply

        self.memory.add("user", message)

        messages = [{"role": "system", "content": self.config.system_prompt}]
        messages.extend(self.memory.get_history())

        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=TOOLS,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        reply = response.choices[0].message

        if reply.tool_calls:
            return self._handle_tool_calls(reply, messages)

        content = reply.content or ""
        self.memory.add("assistant", content)
        return content

    def _handle_tool_calls(self, reply, messages: list) -> str:
        messages.append(reply)

        for tool_call in reply.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            fn = TOOL_MAP.get(fn_name)

            if fn is None:
                result = f"Error: herramienta '{fn_name}' no encontrada."
            else:
                try:
                    result = fn(**fn_args)
                except Exception as e:
                    result = f"Error al ejecutar {fn_name}: {e}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": str(result),
            })

        final = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        content = final.choices[0].message.content or ""
        self.memory.add("assistant", content)
        return content

    def _execute_explicit_command(self, message: str) -> Optional[str]:
        msg_lower = message.strip().lower()

        if msg_lower.startswith("/buscar ") or msg_lower.startswith("/search "):
            query = re.sub(r"^/(buscar|search)\s+", "", message, flags=re.IGNORECASE)
            result = web_search(query)
            return f"He buscado en la web sobre: **{query}**\n\n{result}"

        if msg_lower.startswith("/codigo ") or msg_lower.startswith("/code "):
            code = re.sub(r"^/(codigo|code)\s+", "", message, flags=re.IGNORECASE)
            result = execute_python(code)
            return f"Ejecute el codigo Python:\n\n```python\n{code}\n```\n\n**Resultado:**\n```\n{result}\n```"

        if msg_lower.startswith("/imagen ") or msg_lower.startswith("/image "):
            prompt = re.sub(r"^/(imagen|image)\s+", "", message, flags=re.IGNORECASE)
            url = generate_image(prompt)
            return f"Imagen generada de: **{prompt}**\n\n![{prompt}]({url})"

        return None

    def load_messages(self, messages: list[dict]) -> None:
        self.memory.clear()
        for msg in messages:
            self.memory.add(msg["role"], msg["content"])

    def reset(self) -> None:
        self.memory.clear()
