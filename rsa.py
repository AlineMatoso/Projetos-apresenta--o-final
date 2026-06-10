import random
import math

# =====================================================================
# CAMADA 1: UTILITÁRIOS MATEMÁTICOS BASE
# =====================================================================

def eh_primo(num: int) -> bool:
    """Verifica se um número é primo usando o método da raiz quadrada."""
    if num < 2:
        return False
    for i in range(2, int(math.isqrt(num)) + 1):
        if num % i == 0:
            return False
    return True

def mdc(a: int, b: int) -> int:
    """Calcula o Máximo Divisor Comum (MDC) pelo Algoritmo de Euclides."""
    while b != 0:
        a, b = b, a % b
    return a

def inverso_modular(e: int, phi: int) -> int:
    """Calcula o inverso multiplicativo modular usando o algoritmo estendido."""
    d = 0
    x1, x2, x3 = 1, 0, phi
    y1, y2, y3 = 0, 1, e
    
    while y3 != 0:
        q = x3 // y3
        y1, y2, y3, x1, x2, x3 = (x1 - q * y1), (x2 - q * y2), (x3 - q * y3), y1, y2, y3
        
    if x2 < 0:
        x2 += phi
    return x2


# =====================================================================
# CAMADA 2: GERENCIAMENTO DE CHAVES
# =====================================================================

def gerar_par_de_chaves(p: int, q: int) -> tuple:
    """Gera as chaves pública e privada a partir de dois números primos."""
    if not (eh_primo(p) and eh_primo(q)):
        raise ValueError("Ambos os números fornecidos precisam ser primos.")
    if p == q:
        raise ValueError("Os números primos p e q não podem ser iguais.")

    # n = módulo (determina o espaço dos blocos)
    n = p * q

    # phi = Função totiente de Euler
    phi = (p - 1) * (q - 1)

    # Escolha do expoente público 'e' que seja coprimo com phi
    e = random.randrange(2, phi)
    while mdc(e, phi) != 1:
        e = random.randrange(2, phi)

    # Cálculo do expoente privado 'd' (inverso modular de e)
    d = inverso_modular(e, phi)

    # Retorna ((Chave Pública), (Chave Privada))
    return ((e, n), (d, n))


# =====================================================================
# CAMADA 3: PROCESSAMENTO DA CIFRA
# =====================================================================

def criptografar(chave_publica: tuple, texto_puro: str) -> list:
    """Criptografa uma string usando a fórmula: C = M^e mod n."""
    e, n = chave_publica
    
    # Converte cada caractere textual para seu valor numérico ASCII (ord) 
    # e depois aplica a exponenciação modular.
    texto_cifrado = [pow(ord(caractere), e, n) for caractere in texto_puro]
    return texto_cifrado

def descriptografar(chave_privada: tuple, texto_cifrado: list) -> str:
    """Descriptografa uma lista de números usando a fórmula: M = C^d mod n."""
    d, n = chave_privada
    
    # Aplica a descriptografia modular em cada número e reconverte 
    # o resultado de volta para o caractere original (chr).
    texto_puro = "".join([chr(pow(numero, d, n)) for numero in texto_cifrado])
    return texto_puro


# =====================================================================
# CAMADA 4: INTERFACE DE EXECUÇÃO DO USUÁRIO
# =====================================================================

def executar_sistema_rsa():
    print("=" * 60)
    print("     SISTEMA ACADÊMICO DE CRIPTOGRAFIA RSA - INTERATIVO     ")
    print("=" * 60)
    
    # Para fins educacionais e suporte a caracteres ASCII estendidos, 
    # usamos primos pequenos predefinidos, mas que garantem estabilidade.
    p = 127
    q = 131
    
    print(f"[⚙️ Configuração] Gerando ambiente seguro...")
    print(f" -> Escolhendo primos bases: p = {p}, q = {q}")
    
    try:
        publica, privada = gerar_par_de_chaves(p, q)
        print(f" -> Chave Pública gerada (e, n): {publica}")
        print(f" -> Chave Privada gerada (d, n): [OCULTA PARA SEGURANÇA]")
        print("-" * 60)
        
        # 1. Entrada de dados do Usuário
        mensagem_usuario = input("Digite a mensagem que deseja criptografar: ")
        
        if not mensagem_usuario:
            print("[Erro] A mensagem não pode ser vazia.")
            return

        print("\n--- INICIANDO FLUXO CRIPTOGRÁFICO ---")
        
        # 2. Criptografia
        print("\n[Passo 1] Criptografando o texto...")
        mensagem_protegida = criptografar(publica, mensagem_usuario)
        print(f" -> Mensagem cifrada (numérica): {mensagem_protegida}")
        print(" -> Status: O texto agora está completamente ilegível para interceptores.")
        
        # 3. Descriptografia
        print("\n[Passo 2] Descriptografando com a Chave Privada correspondente...")
        input("Pressione ENTER para autorizar o receptor a ler a mensagem com a chave privada...")
        
        mensagem_recuperada = descriptografar(privada, mensagem_protegida)
        
        # 4. Resultado Final
        print("\n[Sucesso] Processo Concluído!")
        print(f" -> Mensagem original recuperada: '{mensagem_recuperada}'")
        print("=" * 60)
        
    except ValueError as error:
        print(f"\n[Erro no Sistema]: {error}")

if __name__ == "__main__":
    executar_sistema_rsa()