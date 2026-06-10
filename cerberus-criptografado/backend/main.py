# main.py
import asyncio
import os
import logging
import httpx
import redis.asyncio as aioredis
from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv

# Componentes necessários para a criptografia assimétrica RSA
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

load_dotenv()

SERVER_ID = os.getenv("SERVER_ID", "server1")
REDIS_URL = os.getenv("REDIS_URL", None)
SUPABASE_URL = os.getenv("SUPABASE_URL", None)
SUPABASE_KEY = os.getenv("SUPABASE_KEY", None)

logging.basicConfig(
    level=logging.INFO,
    format=f"[{SERVER_ID}] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(SERVER_ID)

app = FastAPI()

# --- Gerenciamento de Chaves RSA do Servidor ---
# O servidor gera seu próprio par de chaves ao iniciar para assinar ou cifrar dados se necessário
server_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
server_public_key = server_private_key.public_key()

def encrypt_message(public_key_pem: str, message: str) -> bytes:
    """Criptografa o texto plano usando a chave pública RSA do cliente de destino."""
    try:
        public_key = serialization.load_pem_public_key(public_key_pem.encode('utf-8'))
        ciphertext = public_key.encrypt(
            message.encode('utf-8'),
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        return ciphertext
    except Exception as e:
        log.error(f"Erro crítico durante a criptografia RSA: {e}")
        return None

# --- Modelos de Dados (Pydantic) ---
class WebhookClient(BaseModel):
    url: str
    public_key: str  # Chave pública transmitida pelo cliente em formato PEM

class MessagePayload(BaseModel):
    content: str

# --- Gerenciador de Webhooks (Substitui o antigo ConnectionManager) ---
class WebhookManager:
    def __init__(self):
        # Estrutura de armazenamento: {"nome_da_sala": [{"url": "...", "public_key": "..."}]}
        self.rooms: dict[str, list[dict]] = {}

    def register(self, room: str, client: WebhookClient):
        sala = self.rooms.setdefault(room, [])
        
        # Validação para evitar mensagens duplicadas na rede
        for cliente_existente in sala:
            if cliente_existente["url"] == client.url:
                # Se a URL já existe, apenas atualiza a chave pública correspondente e ignora o append
                cliente_existente["public_key"] = client.public_key
                log.info(f"Webhook atualizado (registro já existente) na sala '{room}' — URL: {client.url}")
                return
        
        # Se for uma URL inédita, adiciona normalmente na lista da sala
        sala.append({"url": client.url, "public_key": client.public_key})
        log.info(f"Novo webhook registrado com sucesso na sala '{room}' — URL: {client.url}")

    async def broadcast_local(self, message: str, room: str):
        clientes = self.rooms.get(room, [])
        log.info(f"Iniciando disparos de webhooks — sala: '{room}', destinatários ativos: {len(clientes)}")
        
        async with httpx.AsyncClient() as http_client:
            for cliente in clientes:
                # Criptografia customizada baseada na chave pública individual do nó atual
                encrypted_content = encrypt_message(cliente["public_key"], message)
                
                if encrypted_content:
                    try:
                        # O payload trafega pela rede puramente como bytes criptografados (octet-stream)
                        await http_client.post(
                            cliente["url"], 
                            content=encrypted_content,
                            headers={"Content-Type": "application/octet-stream"}
                        )
                        log.info(f"Webhook despachado com sucesso para a URL: {cliente['url']}")
                    except Exception as e:
                        log.error(f"Falha na entrega do webhook para {cliente['url']}: {e}")

manager = WebhookManager()
redis_client = None 

# --- Ouvinte do Barramento Redis (Pub/Sub Multi-Server) ---
async def redis_listener():
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("room:*")
    log.info("Instância do Redis listener ativa — escutando padrão room:*")
    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            room = message["channel"].decode().split(":", 1)[1]
            payload = message["data"].decode()
            origin_server, data = payload.split("|", 1)
            log.info(f"Redis Pub/Sub → Mensagem vinda do '{origin_server}' na sala '{room}'")
            if origin_server != SERVER_ID:
                await manager.broadcast_local(data, room)

def get_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# --- Eventos de Inicialização e Encerramento ---
@app.on_event("startup")
async def startup():
    global redis_client
    if REDIS_URL:
        redis_client = await aioredis.from_url(REDIS_URL)
        asyncio.create_task(redis_listener())
        log.info("Infraestrutura Redis conectada com sucesso")
    else:
        log.info("Aviso: Redis ausente. Operando estritamente em modo local")

    if SUPABASE_URL and SUPABASE_KEY:
        log.info("Persistência no Supabase ativa")
    else:
        log.info("Aviso: Variáveis do Supabase ausentes ou incorretas. Histórico desativado")

@app.on_event("shutdown")
async def shutdown():
    log.info("Encerrando serviços do servidor...")
    if redis_client:
        await redis_client.close()

# --- Rotas da API HTTP ---

@app.get("/public-key")
async def get_public_key():
    """Fornece a chave pública do servidor no formato PEM padrão."""
    pem = server_public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return {"public_key": pem.decode('utf-8')}

@app.post("/webhook/register/{room}")
async def register_webhook(room: str, client: WebhookClient):
    """Inscreve um endpoint de escuta (webhook) e associa sua respectiva chave pública à sala."""
    manager.register(room, client)
    return {"message": f"Inscrição homologada com sucesso na sala: {room}"}

@app.post("/message/{room}")
async def send_message(room: str, payload: MessagePayload, background_tasks: BackgroundTasks):
    """Ponto de entrada de novas mensagens. Processa, persiste e agenda o broadcast assíncrono."""
    data = payload.content
    log.info(f"Requisição de mensagem recebida para a sala '{room}': {data}")

    # Persistência síncrona isolada em thread de execução paralela para evitar gargalos na API
    if SUPABASE_URL and SUPABASE_KEY:
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: get_supabase().table("mensagem").insert({
                "room": room,
                "content": data,
                "server_id": SERVER_ID
            }).execute())
        except Exception as e:
            log.error(f"Erro ao salvar registro no Supabase: {e}")

    # Delegação dos disparos HTTP para Background Tasks (evita que a rota fique travada aguardando a rede)
    if redis_client:
        background_tasks.add_task(manager.broadcast_local, data, room)
        await redis_client.publish(f"room:{room}", f"{SERVER_ID}|{data}")
    else:
        background_tasks.add_task(manager.broadcast_local, data, room)

    return {"status": "Processamento concluído. Mensagem direcionada para a fila de transmissão"}

@app.get("/history/{room}")
async def get_history(room: str):
    """Recupera as últimas 50 mensagens registradas para a sala informada."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        return {"error": "Serviço de histórico inativo no servidor"}
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, lambda: get_supabase().table("mensagem").select("*").eq("room", room).order("id", desc=True).limit(50).execute())
        return result.data
    except Exception as e:
        return {"error": f"Falha ao consultar banco de dados: {e}"}