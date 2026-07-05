import os
import socket
import uuid
from typing import Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from conversational_agent import Agent, AgentConfig
import database

load_dotenv()

OLLAMA_DEFAULT = "http://localhost:11434/v1"
api_key = os.getenv("OPENAI_API_KEY")
base_url = os.getenv("OPENAI_BASE_URL")
if not api_key and not base_url:
    base_url = OLLAMA_DEFAULT

config = AgentConfig(
    api_key=api_key or "ollama",
    base_url=base_url,
    model=os.getenv("OPENAI_MODEL", "llama3.2"),
)

database.init_db()
agents: Dict[str, Agent] = {}
guest_agents: Dict[str, Agent] = {}

app = FastAPI(title="Agente Conversacional")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_agent(session_id: str) -> Agent:
    if session_id not in agents:
        agent = Agent(config)
        messages = database.get_messages(session_id)
        if messages:
            agent.load_messages(messages)
        agents[session_id] = agent
    return agents[session_id]


LANGUAGES = {
    "auto": ("Eres un asistente conversacional amable y servicial.", "Respondes en el mismo idioma en que te hablan."),
    "es": ("Eres un asistente conversacional amable y servicial.", "IMPORTANTE: Debes responder SIEMPRE únicamente en español, sin importar el idioma en que te escriban. El usuario puede escribir en cualquier idioma, pero tu respuesta debe ser siempre en español."),
    "en": ("You are a friendly and helpful conversational assistant.", "IMPORTANT: You MUST ALWAYS respond ONLY in English, no matter what language the user writes in. The user may write in any language, but your reply must always be in English. Never switch to another language."),
    "pt": ("Você é um assistente conversacional amigável e útil.", "IMPORTANTE: Você deve SEMPRE responder apenas em português, independentemente do idioma em que o usuário escrever. Sua resposta deve ser sempre em português."),
    "fr": ("Vous êtes un assistant conversationnel amical et serviable.", "IMPORTANT : Vous devez TOUJOURS répondre uniquement en français, quelle que soit la langue utilisée par l'utilisateur. Votre réponse doit toujours être en français."),
    "de": ("Du bist ein freundlicher und hilfsbereiter Gesprächsassistent.", "WICHTIG: Du musst IMMER nur auf Deutsch antworten, egal in welcher Sprache der Benutzer schreibt. Deine Antwort muss immer auf Deutsch sein."),
    "it": ("Sei un assistente conversazionale amichevole e disponibile.", "IMPORTANTE: Devi SEMPRE rispondere solo in italiano, indipendentemente dalla lingua in cui l'utente scrive. La tua risposta deve essere sempre in italiano."),
    "ja": ("あなたはフレンドリーで役立つ会話アシスタントです。", "重要: ユーザーがどの言語で書いても、常に日本語でのみ回答してください。回答は必ず日本語にしてください。"),
    "zh": ("你是一个友好且乐于助人的对话助手。", "重要：无论用户用什么语言书写，你必须始终只用中文回答。你的回答必须始终是中文。"),
}


class ChatRequest(BaseModel):
    message: str
    session_id: str
    language: str = "auto"
    style: str = ""


class ChatResponse(BaseModel):
    reply: str


class SessionIdResponse(BaseModel):
    session_id: str


class GuestSessionInfo(BaseModel):
    id: str
    title: str
    is_guest: bool = True


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if req.session_id in guest_agents:
        agent = guest_agents[req.session_id]
    else:
        agent = get_agent(req.session_id)

    base, lang_instr = LANGUAGES.get(req.language, LANGUAGES["auto"])
    style_instr = f"\n{req.style}" if req.style else ""
    agent.config.system_prompt = f"{base}\n\n{lang_instr}{style_instr}"

    print(f"[DEBUG] language={req.language}, style={req.style}")
    print(f"[DEBUG] system_prompt={agent.config.system_prompt[:200]}")

    reply = agent.ask(req.message)

    if req.session_id not in guest_agents:
        database.add_message(req.session_id, "user", req.message)
        database.add_message(req.session_id, "assistant", reply)
        db_messages = database.get_messages(req.session_id)
        if len(db_messages) == 2:
            title = req.message[:55] + ("..." if len(req.message) > 55 else "")
            database.update_session_title(req.session_id, title)
    return ChatResponse(reply=reply)


@app.post("/sessions", response_model=SessionIdResponse)
def create_session():
    session_id = str(uuid.uuid4())
    database.create_session(session_id)
    return SessionIdResponse(session_id=session_id)


@app.post("/sessions/guest", response_model=SessionIdResponse)
def create_guest_session():
    session_id = f"guest_{uuid.uuid4().hex[:12]}"
    guest_agents[session_id] = Agent(config)
    return SessionIdResponse(session_id=session_id)


@app.get("/sessions")
def list_sessions():
    result = database.get_sessions()
    for gid, agent in guest_agents.items():
        title = "Invitado"
        last = agent.memory.last()
        if last and last.role == "user":
            title = last.content[:40] + ("..." if len(last.content) > 40 else "")
        result.insert(0, {"id": gid, "title": title, "is_guest": True})
    return result


@app.get("/sessions/{session_id}/messages")
def get_session_messages(session_id: str):
    if session_id in guest_agents:
        agent = guest_agents[session_id]
        return [{"role": m.role, "content": m.content} for m in agent.memory.get_history()]
    return database.get_messages(session_id)


@app.delete("/sessions/{session_id}")
def delete_session_endpoint(session_id: str):
    agents.pop(session_id, None)
    guest_agents.pop(session_id, None)
    database.delete_session(session_id)
    return {"ok": True}


@app.post("/sessions/{session_id}/save", response_model=SessionIdResponse)
def save_guest_session(session_id: str):
    if session_id not in guest_agents:
        raise HTTPException(404, "Sesión de invitado no encontrada")
    agent = guest_agents.pop(session_id)
    new_id = str(uuid.uuid4())
    database.create_session(new_id)
    history = agent.memory.get_history()
    for msg in history:
        database.add_message(new_id, msg["role"], msg["content"])
    first_user = next((m["content"] for m in history if m["role"] == "user"), "")
    if first_user:
        title = first_user[:55] + ("..." if len(first_user) > 55 else "")
        database.update_session_title(new_id, title)
    agents[new_id] = agent
    return SessionIdResponse(session_id=new_id)


@app.post("/reset", response_model=SessionIdResponse)
def reset_session():
    session_id = str(uuid.uuid4())
    database.create_session(session_id)
    return SessionIdResponse(session_id=session_id)


@app.get("/", response_class=HTMLResponse)
def index():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def start_ngrok(port: int):
    import subprocess
    import sys

    ngrok_paths = [
        r"C:\Users\USER\AppData\Local\Microsoft\WinGet\Packages\Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe\ngrok.exe",
    ]
    ngrok_exe = None
    for p in ngrok_paths:
        if os.path.exists(p):
            ngrok_exe = p
            break
    if not ngrok_exe:
        print("  [ngrok] no encontrado, saltando...")
        return

    subprocess.run(["taskkill", "/f", "/im", "ngrok.exe"], capture_output=True)
    proc = subprocess.Popen(
        [ngrok_exe, "http", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    import time

    time.sleep(3)
    try:
        import urllib.request, json

        resp = urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=5)
        data = json.loads(resp.read())
        url = data["tunnels"][0]["public_url"]
        print(f"  ngrok:    {url}")
    except Exception:
        print("  [ngrok] no se pudo obtener la URL pública")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8001))
    ip = get_local_ip()
    print(f"  Local:    http://127.0.0.1:{port}")
    print(f"  Red:      http://{ip}:{port}")
    print(f"  Abre http://{ip}:{port} en Google Chrome desde cualquier dispositivo en la misma red")
    start_ngrok(port)
    uvicorn.run("web_app:app", host="0.0.0.0", port=port, reload=True)
