# client_app.py
import base64
import json
import httpx
import uvicorn
from fastapi import FastAPI, WebSocket, Request
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization

app = FastAPI()

# Configurações de porta
MAIN_SERVER_URL = "http://localhost:8000"  # Onde o main.py está rodando
CLIENT_PORT = 9001                         # A porta deste cliente
MY_WEBHOOK_URL = f"http://localhost:{CLIENT_PORT}/webhook/receive"

print("Gerando par de chaves RSA do cliente...")
client_private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
client_public_key = client_private_key.public_key()
public_key_pem = client_public_key.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode('utf-8')

# Variável global para guardar a conexão com a interface HTML
html_connection = None

@app.post("/webhook/receive")
async def receive_webhook(request: Request):
    """
    Este é o WEBHOOK. O main.py vai fazer um POST aqui enviando 
    os bytes criptografados.
    """
    global html_connection
    encrypted_bytes = await request.body()
    
    try:
        # Descriptografa usando a chave privada (RSA)
        decrypted_bytes = client_private_key.decrypt(
            encrypted_bytes,
            padding.OAEP(
                mgf=padding.MGF1(algorithm=hashes.SHA256()),
                algorithm=hashes.SHA256(),
                label=None
            )
        )
        
        plaintext = decrypted_bytes.decode('utf-8')
        
        # Converte os bytes criptografados para Base64 só para podermos
        # exibir a 'sujeira' no HTML visualmente
        ciphertext_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        
        if html_connection:
            await html_connection.send_json({
                "type": "message",
                "ciphertext": ciphertext_b64,
                "plaintext": plaintext
            })
            
        return {"status": "Mensagem recebida e descriptografada com sucesso"}
    except Exception as e:
        print(f"Falha na descriptografia: {e}")
        return {"status": "Erro na descriptografia"}

@app.websocket("/ws_local")
async def websocket_local(ws: WebSocket):
    """
    Comunicação interna apenas entre esse script Python e o seu arquivo HTML.
    """
    global html_connection
    await ws.accept()
    html_connection = ws
    
    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action")
            room = data.get("room")
            
            if action == "register":
                # O HTML pediu para entrar na sala. Vamos registrar o webhook no main.py.
                async with httpx.AsyncClient() as client:
                    payload = {
                        "url": MY_WEBHOOK_URL,
                        "public_key": public_key_pem
                    }
                    print(f"Registrando webhook no servidor principal para a sala: {room}")
                    await client.post(f"{MAIN_SERVER_URL}/webhook/register/{room}", json=payload)
                    
            elif action == "send":
                # O HTML quer enviar uma mensagem. Faremos um POST para o main.py.
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{MAIN_SERVER_URL}/message/{room}", 
                        json={"content": data["msg"]}
                    )
                    
    except Exception:
        print("Interface HTML desconectada.")
        html_connection = None

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=CLIENT_PORT)