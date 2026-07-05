import re
from dataclasses import dataclass
from typing import Optional

from openai import OpenAI

from .memory import ConversationMemory
from tools import web_search, execute_python, generate_image


@dataclass
class AgentConfig:
    system_prompt: str = (
        "Eres un asistente conversacional amable y servicial. "
        "Respondes en el mismo idioma en que te hablan."
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
        tool_reply = self._execute_explicit_command(message)
        if tool_reply is not None:
            self.memory.add("user", message)
            self.memory.add("assistant", tool_reply)
            return tool_reply

        self.memory.add("user", message)

        messages = [{"role": "system", "content": self.config.system_prompt}]
        messages.extend(self.memory.get_history())

        response = self._client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )

        reply = response.choices[0].message.content
        self.memory.add("assistant", reply)
        return reply

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
