Funcionamento
1. Rodar no servidor principal: uvicorn main:app --port 8000
2. sergundo terminal: python client_app.py
3. Abrir o test_client.html

---
O HTML manda um JSON para o client_app.py -> Ele manda um HTTP POST pro main.py -> O main.py criptografa via RSA e faz um Webhook (POST) pro client_app.py -> O client_app.py descriptografa e exibe na tela do HTML as duas versões. Se o professor quiser ver a criptografia em ação, as letrinhas vermelhas (Base64 do RSA) vão provar que o conteúdo trafegou cifrado na rede!
