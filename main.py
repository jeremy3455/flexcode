import os
import subprocess
import sys
import time

from dotenv import load_dotenv

from conversational_agent import Agent, AgentConfig

load_dotenv()

OLLAMA_DEFAULT = "http://localhost:11434/v1"


def _try_start_ollama():
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        time.sleep(2)
        return True
    except FileNotFoundError:
        return False


def main():
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")

    if not api_key and not base_url:
        print("No se encontró OPENAI_API_KEY.")
        print(f"Usando Ollama por defecto ({OLLAMA_DEFAULT})\n")
        base_url = OLLAMA_DEFAULT

    config = AgentConfig(
        api_key=api_key or "ollama",
        base_url=base_url,
        model=os.getenv("OPENAI_MODEL", "llama3.2"),
    )

    try:
        agent = Agent(config)
    except Exception:
        print("Ollama no está corriendo. Intentando arrancarlo...")
        if not _try_start_ollama():
            print("Ollama no está instalado.")
            print("→ Ejecuta:   .\\setup_ollama.ps1")
            print("→ O instala desde: https://ollama.com\n")
            sys.exit(1)
        try:
            agent = Agent(config)
        except Exception:
            print("No se pudo conectar. ¿Corriste 'ollama pull llama3.2'?\n")
            sys.exit(1)

    print(f"Agente listo (modelo: {config.model} | {config.base_url})")
    print("Escribe 'salir' para terminar, 'reset' para reiniciar.\n")

    while True:
        try:
            user_input = input("Tu > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not user_input:
            continue
        if user_input.lower() in ("salir", "exit", "quit"):
            break
        if user_input.lower() == "reset":
            agent.reset()
            print("Conversacion reiniciada.\n")
            continue

        try:
            reply = agent.ask(user_input)
        except Exception as e:
            print(f"Error: {e}")
            print("¿Tienes Ollama corriendo? -> ollama serve\n")
            continue

        print(f"Agent > {reply}\n")


if __name__ == "__main__":
    main()
