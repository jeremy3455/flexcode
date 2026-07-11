import hashlib
import os
import secrets
import socket
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict

import jwt
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
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

JWT_SECRET = os.getenv("JWT_SECRET", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

database.init_db()

agents: Dict[str, Agent] = {}
guest_agents: Dict[str, Agent] = {}

app = FastAPI(title="Agente Conversacional")
security = HTTPBearer(auto_error=False)

@app.middleware("http")
async def ignore_chrome_devtools(request: Request, call_next):
    if request.url.path.startswith("/.well-known/"):
        from starlette.responses import Response
        return Response(status_code=204)
    return await call_next(request)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

LANG_RULES = {
    "auto": (
        "El usuario no ha fijado un idioma especifico. "
        "Responde en el mismo idioma en que el usuario escriba su mensaje."
    ),
    "es": (
        "El usuario tiene configurado ESPAÑOL como idioma de respuesta.\n\n"
        "Reglas obligatorias:\n"
        "1. Responde SIEMPRE en espanol, sin importar en que idioma escriba el usuario.\n"
        "2. No cambies de idioma aunque el usuario escriba en otro idioma, mezcle idiomas, "
        "o pida explicitamente una respuesta en otro idioma. Si lo pide, responde en espanol "
        "y aclara que puede cambiar el idioma desde configuracion.\n"
        "3. Excepciones validas: traducciones especificas que pida el usuario, "
        "contenido solicitado en otro idioma (ej. 'escribeme una frase en frances'), "
        "nombres propios, terminos tecnicos sin traduccion, y codigo (sintaxis original).\n"
        "4. Todo tu razonamiento, formato, ejemplos y aclaraciones deben estar en espanol."
    ),
    "en": (
        "The user has set ENGLISH as their response language.\n\n"
        "Mandatory rules:\n"
        "1. ALWAYS respond in English, no matter what language the user writes in.\n"
        "2. Do not switch languages even if the user writes in another language, mixes languages, "
        "or explicitly asks for a reply in another language. If asked, reply in English "
        "and explain they can change the language in settings.\n"
        "3. Valid exceptions: specific translations the user requests, "
        "content requested in another language (e.g. 'write me a phrase in French'), "
        "proper nouns, untranslated technical terms, and code (original syntax).\n"
        "4. All your reasoning, formatting, examples, and clarifications must be in English."
    ),
    "pt": (
        "O usuario configurou PORTUGUES como idioma de resposta.\n\n"
        "Regras obrigatorias:\n"
        "1. Responda SEMPRE em portugues, independentemente do idioma em que o usuario escrever.\n"
        "2. Nao mude de idioma mesmo que o usuario escreva em outro idioma, misture idiomas, "
        "ou peca explicitamente uma resposta em outro idioma. Se pedir, responda em portugues "
        "e avise que pode mudar o idioma nas configuracoes.\n"
        "3. Excecoes validas: traducoes especificas solicitadas, "
        "conteudo solicitado em outro idioma (ex. 'escreva uma frase em italiano'), "
        "nomes proprios, termos tecnicos sem traducao, e codigo (sintaxe original).\n"
        "4. Todo o seu raciocinio, formato, exemplos e explicacoes devem estar em portugues."
    ),
    "fr": (
        "L'utilisateur a defini le FRANCAIS comme langue de reponse.\n\n"
        "Regles obligatoires :\n"
        "1. Repondez TOUJOURS en francais, quelle que soit la langue utilisee par l'utilisateur.\n"
        "2. Ne changez pas de langue meme si l'utilisateur ecrit dans une autre langue, melange "
        "les langues, ou demande explicitement une reponse dans une autre langue. Si demande, "
        "repondez en francais et precisez qu'il peut changer la langue dans les parametres.\n"
        "3. Exceptions valides : traductions specifiques demandees, "
        "contenu demande dans une autre langue (ex. 'ecris-moi une phrase en italien'), "
        "noms propres, termes techniques sans traduction, et code (syntaxe originale).\n"
        "4. Tout votre raisonnement, format, exemples et explications doivent etre en francais."
    ),
    "de": (
        "Der Benutzer hat DEUTSCH als Antwortsprache eingestellt.\n\n"
        "Verbindliche Regeln:\n"
        "1. Antworte IMMER auf Deutsch, egal in welcher Sprache der Benutzer schreibt.\n"
        "2. Wechsle nicht die Sprache, auch wenn der Benutzer in einer anderen Sprache schreibt, "
        "Sprachen mischt oder explizit eine Antwort in einer anderen Sprache verlangt. "
        "Wenn gefragt, antworte auf Deutsch und weise darauf hin, dass die Sprache in den "
        "Einstellungen geaendert werden kann.\n"
        "3. Gueltige Ausnahmen: spezifische Uebersetzungen, die der Benutzer anfordert, "
        "Inhalt, der in einer anderen Sprache angefordert wird (z.B. 'schreib mir einen Satz "
        "auf Italienisch'), Eigennamen, unuebersetzte Fachbegriffe und Code (Originalsyntax).\n"
        "4. Deine gesamte Argumentation, Formatierung, Beispiele und Erklaerungen muessen "
        "auf Deutsch sein."
    ),
    "it": (
        "L'utente ha impostato ITALIANO come lingua di risposta.\n\n"
        "Regole obbligatorie:\n"
        "1. Rispondi SEMPRE in italiano, indipendentemente dalla lingua in cui scrive l'utente.\n"
        "2. Non cambiare lingua anche se l'utente scrive in un'altra lingua, mescola lingue, "
        "o chiede esplicitamente una risposta in un'altra lingua. Se lo chiede, rispondi in "
        "italiano e spiega che puo cambiare la lingua dalle impostazioni.\n"
        "3. Eccezioni valide: traduzioni specifiche richieste, "
        "contenuto richiesto in un'altra lingua (es. 'scrivimi una frase in francese'), "
        "nomi propri, termini tecnici senza traduzione e codice (sintassi originale).\n"
        "4. Tutto il tuo ragionamento, formato, esempi e chiarimenti devono essere in italiano."
    ),
    "ja": (
        "ユーザーは応答言語を日本語に設定しています。\n\n"
        "必須ルール：\n"
        "1. ユーザーがどの言語で書いても、常に日本語で回答してください。\n"
        "2. ユーザーが別の言語で書いたり、言語を混ぜたり、別の言語での回答を明示的に"
        "求めても、言語を切り替えないでください。求められた場合は日本語で回答し、"
        "設定から言語を変更できることを説明してください。\n"
        "3. 有効な例外：ユーザーが依頼した特定の翻訳、別の言語で依頼されたコンテンツ"
        "（例：「イタリア語でフレーズを書いて」）、固有名詞、翻訳されていない専門用語、"
        "およびコード（元の構文）。\n"
        "4. 推論、形式、例、説明はすべて日本語で行ってください。"
    ),
    "zh": (
        "用户已将响应语言设置为中文。\n\n"
        "强制性规则：\n"
        "1. 无论用户用什么语言书写，必须始终用中文回答。\n"
        "2. 即使用户用其他语言书写、混合语言或明确要求用其他语言回复，"
        "也不要切换语言。如果被要求，请用中文回复并说明可以在设置中更改语言。\n"
        "3. 有效例外：用户要求的特定翻译、用其他语言请求的内容"
        "（例如'用意大利语写一句话'）、专有名词、无通用翻译的术语和代码（原始语法）。\n"
        "4. 你的所有推理、格式、示例和说明必须用中文。"
    ),
}


class AuthRequest(BaseModel):
    username: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: str
    username: str


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


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return salt.hex() + ":" + dk.hex()


def verify_password(password: str, stored: str) -> bool:
    salt_hex, dk_hex = stored.split(":")
    salt = bytes.fromhex(salt_hex)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
    return dk.hex() == dk_hex


def create_token(user_id: str, username: str) -> str:
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> dict | None:
    if credentials is None:
        return None
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"user_id": payload["user_id"], "username": payload["username"]}
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Token inválido")


def get_agent(session_id: str) -> Agent:
    if session_id not in agents:
        agent = Agent(config)
        messages = database.get_messages(session_id)
        if messages:
            agent.load_messages(messages)
        agents[session_id] = agent
    return agents[session_id]


@app.post("/register", response_model=AuthResponse)
def register(req: AuthRequest):
    if not (3 <= len(req.username) <= 30):
        raise HTTPException(400, "El usuario debe tener entre 3 y 30 caracteres")
    if not (8 <= len(req.password) <= 12):
        raise HTTPException(400, "La contraseña debe tener entre 8 y 12 caracteres")
    existing = database.get_user_by_username(req.username)
    if existing:
        raise HTTPException(409, "El usuario ya existe")
    user_id = str(uuid.uuid4())
    pw_hash = hash_password(req.password)
    database.create_user(user_id, req.username, pw_hash)
    token = create_token(user_id, req.username)
    return AuthResponse(token=token, user_id=user_id, username=req.username)


@app.post("/login", response_model=AuthResponse)
def login(req: AuthRequest):
    user = database.get_user_by_username(req.username)
    if not user or not verify_password(req.password, user["password_hash"]):
        raise HTTPException(401, "Usuario o contraseña incorrectos")
    token = create_token(user["id"], user["username"])
    return AuthResponse(token=token, user_id=user["id"], username=user["username"])


@app.get("/me")
def me(user: dict = Depends(get_current_user)):
    if not user:
        raise HTTPException(401, "No autenticado")
    return user


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, user: dict | None = Depends(get_current_user)):
    if req.session_id in guest_agents:
        agent = guest_agents[req.session_id]
    else:
        agent = get_agent(req.session_id)

    lang_rule = LANG_RULES.get(req.language, LANG_RULES["auto"])
    parts = [config.system_prompt]
    parts.append(
        f"## Configuracion de Idioma de Respuesta\n\n"
        f"El usuario tiene seleccionado el idioma: {req.language}\n\n"
        f"{lang_rule}"
    )
    if req.style:
        parts.append(
            f"## Configuracion de Personalidad\n\n"
            f"El usuario ha definido una instruccion de personalidad personalizada:\n\n"
            f"Instruccion: \"{req.style}\"\n\n"
            f"Reglas de aplicacion:\n"
            f"1. Aplica esta instruccion a TODAS tus respuestas, ajustando tono, estilo y forma.\n"
            f"2. La personalidad afecta el tono y la forma, NO el contenido ni la precision.\n"
            f"   - La informacion debe seguir siendo correcta, completa y util.\n"
            f"3. Interpreta la instruccion de forma consistente en toda la conversacion.\n"
            f"4. Limites de seguridad y respeto (no negociables):\n"
            f"   - Nunca uses el estilo para ser cruel, humillante o insultante.\n"
            f"   - Si el tema es sensible (salud, duelo, crisis), suaviza el tono "
            f"automaticamente y prioriza empatia.\n"
            f"   - No permitas que la personalidad te lleve a dar info incorrecta o danina.\n"
            f"5. Si el tema es serio o delicado, modera el estilo en esa respuesta puntual."
        )
    agent.config.system_prompt = "\n\n".join(parts)

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
def create_session(user: dict | None = Depends(get_current_user)):
    session_id = str(uuid.uuid4())
    database.create_session(session_id, user["user_id"] if user else "")
    return SessionIdResponse(session_id=session_id)


@app.post("/sessions/guest", response_model=SessionIdResponse)
def create_guest_session():
    session_id = f"guest_{uuid.uuid4().hex[:12]}"
    guest_agents[session_id] = Agent(config)
    return SessionIdResponse(session_id=session_id)


@app.get("/sessions")
def list_sessions(user: dict | None = Depends(get_current_user)):
    result = database.get_sessions(user["user_id"] if user else "")
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
def save_guest_session(session_id: str, user: dict | None = Depends(get_current_user)):
    if session_id not in guest_agents:
        raise HTTPException(404, "Sesión de invitado no encontrada")
    agent = guest_agents.pop(session_id)
    new_id = str(uuid.uuid4())
    database.create_session(new_id, user["user_id"] if user else "")
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


@app.get("/descargar/{filename}")
def descargar(filename: str):
    import os
    from tools.doc_generator import OUTPUT_DIR
    safe = os.path.basename(filename)
    filepath = os.path.join(OUTPUT_DIR, safe)
    if not os.path.exists(filepath):
        raise HTTPException(404, "Archivo no encontrado")
    return FileResponse(filepath, filename=safe)


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
