# ChatCerberus — Documentação Técnica

---

## Visão geral da arquitetura

O sistema é composto por três camadas que trabalham juntas:

- **FastAPI + WebSocket** — servidor Python que aceita conexões em tempo real
- **Redis Pub/Sub (Upstash)** — barramento de mensagens que sincroniza múltiplos servidores
- **PostgreSQL (Supabase)** — banco de dados que persiste o histórico de mensagens

O fluxo de uma mensagem é:

```
Cliente envia mensagem
        ↓
Servidor recebe via WebSocket
        ↓
Salva no PostgreSQL (histórico permanente)
        ↓
Faz broadcast local (entrega para clientes deste servidor)
        ↓
Publica no Redis (avisa outros servidores)
        ↓
Outros servidores recebem via redis_listener
        ↓
Cada servidor entrega para seus clientes locais
```

---

## Estrutura do projeto

```
chatcerberus/
└── backend/
    ├── main.py           # servidor principal
    ├── requirements.txt  # dependências Python
    ├── .env              # variáveis de ambiente (não vai ao Git)
    └── test_client.html  # cliente de teste
```

---

## Variáveis de ambiente (.env)

| Variável | Descrição |
|---|---|
| `SERVER_ID` | Identificador único do servidor (ex: server1, server2) |
| `REDIS_URL` | URL de conexão com o Redis do Upstash |
| `SUPABASE_URL` | URL do projeto no Supabase |
| `SUPABASE_KEY` | Chave pública (anon) do Supabase |

Exemplo:
```env
REDIS_URL=rediss://default:senha@endpoint.upstash.io:6379
SERVER_ID=server1
SUPABASE_URL=https://projeto.supabase.co
SUPABASE_KEY=sb_publishable_...
```

---

## Como rodar

```bash
# Terminal 1 — servidor 1
cd backend
source venv/bin/activate
SERVER_ID=server1 uvicorn main:app --port 8001

# Terminal 2 — servidor 2
cd backend
source venv/bin/activate
SERVER_ID=server2 uvicorn main:app --port 8002
```

---

## Documentação da main.py

### Imports e configuração inicial

```python
import asyncio
import os
import logging
import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from dotenv import load_dotenv
```

- `asyncio` — permite programação assíncrona. Sem ele o servidor bloquearia a cada operação de I/O (rede, banco).
- `redis.asyncio` — cliente Redis assíncrono. Importado como `aioredis` para não conflitar com a variável global `redis_client`.
- `WebSocket` — classe do FastAPI que representa uma conexão WebSocket aberta.
- `WebSocketDisconnect` — exceção lançada quando o cliente fecha a conexão.
- `load_dotenv()` — lê o arquivo `.env` e injeta as variáveis no ambiente do processo.

### Variáveis globais

```python
SERVER_ID = os.getenv("SERVER_ID", "server1")
REDIS_URL = os.getenv("REDIS_URL", None)
SUPABASE_URL = os.getenv("SUPABASE_URL", None)
SUPABASE_KEY = os.getenv("SUPABASE_KEY", None)
```

`os.getenv(chave, padrão)` lê variáveis de ambiente. O segundo argumento é o valor padrão caso a variável não esteja definida. Isso permite rodar o servidor sem `.env` (em modo degradado).

### Configuração de logging

```python
logging.basicConfig(
    level=logging.INFO,
    format=f"[{SERVER_ID}] %(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(SERVER_ID)
```

Configura o sistema de logs. O `format` define que toda linha de log começa com `[server1]` ou `[server2]` — essencial em sistemas distribuídos para saber qual servidor processou cada evento. `%(asctime)s` é o horário, `%(levelname)s` é o nível (INFO, ERROR), `%(message)s` é o texto.

---

### Classe ConnectionManager

```python
class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, list[WebSocket]] = {}
```

Gerencia todas as conexões WebSocket ativas. O atributo `rooms` é um dicionário onde a chave é o nome da sala e o valor é uma lista de WebSockets conectados. Exemplo: `{"sala1": [ws_cliente_a, ws_cliente_b]}`.

#### Método connect

```python
async def connect(self, ws: WebSocket, room: str):
    await ws.accept()
    self.rooms.setdefault(room, []).append(ws)
```

Aceita a conexão WebSocket (`ws.accept()` é obrigatório — sem ele o handshake não completa) e adiciona o WebSocket na lista da sala. `setdefault` cria a lista se a sala ainda não existir.

#### Método disconnect

```python
def disconnect(self, ws: WebSocket, room: str):
    self.rooms[room].remove(ws)
```

Remove o WebSocket da lista quando o cliente desconecta. Chamado no bloco `except WebSocketDisconnect`.

#### Método broadcast_local

```python
async def broadcast_local(self, message: str, room: str):
    clientes = self.rooms.get(room, [])
    for ws in clientes:
        await ws.send_text(message)
```

Envia uma mensagem para todos os clientes conectados **neste servidor** nesta sala. O `.get(room, [])` retorna lista vazia se a sala não existir, evitando KeyError. É chamado tanto diretamente (modo local) quanto pelo `redis_listener` (modo distribuído).

---

### Função redis_listener

```python
async def redis_listener():
    pubsub = redis_client.pubsub()
    await pubsub.psubscribe("room:*")
    log.info("Redis listener iniciado — escutando room:*")
    async for message in pubsub.listen():
        if message["type"] == "pmessage":
            room = message["channel"].decode().split(":", 1)[1]
            payload = message["data"].decode()
            origin_server, data = payload.split("|", 1)
            if origin_server != SERVER_ID:
                await manager.broadcast_local(data, room)
```

Função assíncrona que roda em background enquanto o servidor está ativo. Detalhes:

- `pubsub()` — cria um objeto de assinatura, análogo a sintonizar um canal de rádio.
- `psubscribe("room:*")` — se inscreve em todos os canais que começam com `room:`. O `*` é wildcard, então captura `room:sala1`, `room:private_Aline_Helena`, etc.
- `async for message in pubsub.listen()` — loop infinito que bloqueia aguardando mensagens sem travar o event loop.
- `message["type"] == "pmessage"` — filtra só mensagens de dados. O Redis também envia mensagens de controle (como `psubscribe`) com outros tipos.
- `payload.split("|", 1)` — separa `server1|Aline: olá` em `origin_server=server1` e `data=Aline: olá`.
- `if origin_server != SERVER_ID` — evita duplicação: o servidor que enviou já fez o broadcast local, então só os outros precisam entregar.

---

### Função get_supabase

```python
def get_supabase():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)
```

Cria e retorna um novo cliente Supabase. O import é feito dentro da função para evitar que a inicialização do cliente bloqueie o startup do servidor. É chamada sob demanda (ao receber mensagem ou ao buscar histórico).

---

### Evento startup

```python
@app.on_event("startup")
async def startup():
    global redis_client
    if REDIS_URL:
        redis_client = await aioredis.from_url(REDIS_URL)
        asyncio.create_task(redis_listener())
        log.info("Redis conectado")
    else:
        log.info("Redis não configurado — modo local apenas")
```

Executado automaticamente quando o servidor inicia. `asyncio.create_task(redis_listener())` inicia o listener em background — sem isso ele travaria o startup. O `global redis_client` é necessário para modificar a variável global de dentro de uma função.

### Evento shutdown

```python
@app.on_event("shutdown")
async def shutdown():
    if redis_client:
        await redis_client.close()
```

Executado quando o servidor para (Ctrl+C). Fecha a conexão com o Redis corretamente, liberando recursos.

---

### Endpoint WebSocket

```python
@app.websocket("/ws/{room}")
async def websocket_endpoint(ws: WebSocket, room: str):
```

Define o endpoint WebSocket em `/ws/{room}`. O `{room}` é um parâmetro de path — `ws://localhost:8001/ws/sala1` resulta em `room="sala1"`.

#### Carregamento do histórico

```python
result = await loop.run_in_executor(None, lambda: get_supabase()
    .table("mensagem")
    .select("*")
    .eq("room", room)
    .order("id")
    .limit(50)
    .execute())
for msg in result.data:
    await ws.send_text(f"[histórico] {msg['server_id']} — {msg['content']}")
```

Ao conectar, busca as últimas 50 mensagens da sala no Supabase e envia para o cliente com o prefixo `[histórico]`. O `run_in_executor` executa a chamada síncrona do Supabase em uma thread separada, sem bloquear o event loop assíncrono.

#### Loop principal de mensagens

```python
while True:
    data = await ws.receive_text()
    # salva no Supabase
    # faz broadcast local
    # publica no Redis
```

Loop que aguarda mensagens do cliente. `receive_text()` é assíncrono — enquanto espera uma mensagem deste cliente, o servidor pode atender outros. Quando chega uma mensagem:

1. Salva no Supabase com `INSERT`
2. Faz `broadcast_local` para clientes deste servidor
3. Publica no Redis com `SERVER_ID|mensagem` para outros servidores entregarem

#### Tratamento de desconexão

```python
except WebSocketDisconnect:
    manager.disconnect(ws, room)
```

`WebSocketDisconnect` é lançada quando o cliente fecha o navegador ou perde conexão. Remove o WebSocket do `ConnectionManager` para evitar tentar enviar mensagens para uma conexão morta.

---

### Endpoint HTTP de histórico

```python
@app.get("/history/{room}")
async def get_history(room: str):
    result = await loop.run_in_executor(None, lambda: get_supabase()
        .table("mensagem")
        .select("*")
        .eq("room", room)
        .order("id", desc=True)
        .limit(50)
        .execute())
    return result.data
```

Endpoint REST que retorna o histórico de uma sala em JSON. Pode ser acessado via `GET http://localhost:8001/history/sala1`. Útil para depuração e para clientes que não usam WebSocket.

---

## Banco de dados — tabela mensagem

| Coluna | Tipo | Descrição |
|---|---|---|
| `id` | SERIAL | Chave primária, auto-incremento |
| `room` | VARCHAR | Nome da sala |
| `content` | VARCHAR | Conteúdo da mensagem |
| `server_id` | VARCHAR | Qual servidor processou |
| `created_at` | TIMESTAMP | Horário de criação (automático) |

O campo `server_id` é fundamental para sistemas distribuídos — permite rastrear qual instância do servidor processou cada mensagem, útil para debugging e auditoria.

---

## Conceitos de sistemas distribuídos aplicados

**Escalabilidade horizontal** — o mesmo código roda em múltiplas instâncias (server1, server2) diferenciadas apenas pelo `SERVER_ID`. Adicionar um server3 é só subir outro processo.

**Barramento de mensagens** — o Redis Pub/Sub desacopla os servidores. Nenhum servidor conhece os outros diretamente; todos publicam e assinam o mesmo canal.

**Persistência vs. cache** — PostgreSQL persiste dados permanentemente (histórico). Redis é volátil (mensagens em trânsito). Cada um cumpre seu papel.

**Modo degradado** — o servidor funciona sem Redis (modo local) e sem Supabase (sem histórico). Isso é resiliência: falha parcial não derruba o sistema todo.

**Idempotência de salas** — salas privadas são geradas com nomes ordenados (`[myName, other].sort().join("_")`), garantindo que `private_Aline_Helena` é sempre a mesma sala independente de quem inicia a conversa.

---

## Dúvidas!

**Por que WebSocket e não HTTP?**
HTTP é request-response — o cliente sempre inicia. WebSocket mantém uma conexão bidirecional aberta, permitindo que o servidor envie mensagens sem o cliente pedir. Essencial para chat em tempo real.

**Por que o Redis é necessário se já temos o ConnectionManager?**
O `ConnectionManager` só conhece os clientes conectados **neste processo**. Se o cliente A está no server1 e o cliente B no server2, o manager do server1 não tem o WebSocket do B. O Redis resolve isso sendo um barramento compartilhado entre todos os servidores.

**O que acontece se o Redis cair?**
O servidor detecta que `redis_client` está indisponível e cai no `else: broadcast_local`. Clientes no mesmo servidor continuam se comunicando; clientes em servidores diferentes ficam isolados. O histórico continua funcionando normalmente.

**Por que `run_in_executor` nas chamadas ao Supabase?**
O cliente Supabase Python é síncrono — bloqueia a thread até a resposta chegar. Num servidor assíncrono isso travaria o event loop, impedindo outras conexões de serem atendidas. `run_in_executor` roda a chamada em uma thread separada, liberando o event loop.

**Por que o `origin_server` é incluído no payload do Redis?**
Para evitar que o servidor que enviou a mensagem a receba de volta via Redis e faça um segundo broadcast (duplicação). O listener verifica `if origin_server != SERVER_ID` antes de entregar.