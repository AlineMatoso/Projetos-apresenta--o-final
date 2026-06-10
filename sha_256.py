# =====================================================================
# CAMADA 1: CONSTANTES MATEMÁTICAS SHA-256
# =====================================================================

# As 64 constantes representam os 32 primeiros bits das partes fracionárias 
# das raízes cúbicas dos primeiros 64 números primos.
K = (
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
)

# Valores de hash iniciais (raízes quadradas dos 8 primeiros primos)
H_INICIAL = (
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
)

# =====================================================================
# CAMADA 2: OPERAÇÕES LÓGICAS (BITWISE)
# =====================================================================

def rotr(x: int, n: int) -> int:
    """Rotaciona os bits para a direita (Right Rotate)."""
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF

def ch(x: int, y: int, z: int) -> int:
    """Função Choose: Se x, então y; senão, z."""
    return (x & y) ^ (~x & z)

def maj(x: int, y: int, z: int) -> int:
    """Função Maioria: Retorna o bit mais comum entre x, y e z."""
    return (x & y) ^ (x & z) ^ (y & z)

def sigma0_upper(x: int) -> int:
    return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)

def sigma1_upper(x: int) -> int:
    return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)

def sigma0_lower(x: int) -> int:
    return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3)

def sigma1_lower(x: int) -> int:
    return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10)

# =====================================================================
# CAMADA 3: O ALGORITMO PRINCIPAL
# =====================================================================

def gerar_sha256(mensagem_texto: str) -> str:
    """Converte a string de entrada para um hash SHA-256 hexadecimal."""
    # 1. Preparação: Converter texto para bytes
    mensagem_bytes = bytearray(mensagem_texto, 'utf-8')
    tamanho_original_bits = len(mensagem_bytes) * 8

    # 2. Preenchimento (Padding)
    # Adiciona o bit '1' (0x80 em bytes)
    mensagem_bytes.append(0x80)
    
    # Adiciona '0's até que o tamanho em bits seja côngruo a 448 (mod 512)
    while (len(mensagem_bytes) * 8) % 512 != 448:
        mensagem_bytes.append(0x00)
        
    # Adiciona o tamanho original como um inteiro de 64 bits (8 bytes)
    mensagem_bytes.extend(tamanho_original_bits.to_bytes(8, 'big'))

    # Inicializa os buffers de hash com as constantes
    h = list(H_INICIAL)

    # 3. Processamento em blocos de 512 bits (64 bytes)
    for i in range(0, len(mensagem_bytes), 64):
        bloco = mensagem_bytes[i:i+64]
        
        # Cria um cronograma de mensagens de 64 palavras (w)
        w = [0] * 64
        for j in range(16):
            w[j] = int.from_bytes(bloco[j*4:(j+1)*4], 'big')
            
        for j in range(16, 64):
            s0 = sigma0_lower(w[j-15])
            s1 = sigma1_lower(w[j-2])
            w[j] = (w[j-16] + s0 + w[j-7] + s1) & 0xFFFFFFFF

        # Inicializa variáveis de trabalho (a até h)
        a, b, c, d, e, f, g, h_var = h

        # 4. As 64 rodadas de compressão
        for j in range(64):
            temp1 = (h_var + sigma1_upper(e) + ch(e, f, g) + K[j] + w[j]) & 0xFFFFFFFF
            temp2 = (sigma0_upper(a) + maj(a, b, c)) & 0xFFFFFFFF
            
            h_var = g
            g = f
            f = e
            e = (d + temp1) & 0xFFFFFFFF
            d = c
            c = b
            b = a
            a = (temp1 + temp2) & 0xFFFFFFFF

        # Adiciona o resultado comprimido ao hash atual
        h[0] = (h[0] + a) & 0xFFFFFFFF
        h[1] = (h[1] + b) & 0xFFFFFFFF
        h[2] = (h[2] + c) & 0xFFFFFFFF
        h[3] = (h[3] + d) & 0xFFFFFFFF
        h[4] = (h[4] + e) & 0xFFFFFFFF
        h[5] = (h[5] + f) & 0xFFFFFFFF
        h[6] = (h[6] + g) & 0xFFFFFFFF
        h[7] = (h[7] + h_var) & 0xFFFFFFFF

    # 5. Formatação da saída (Concatena em uma string Hexadecimal)
    hash_final = ''.join(f'{valor:08x}' for valor in h)
    return hash_final

# =====================================================================
# CAMADA 4: INTERFACE DE EXECUÇÃO DO USUÁRIO
# =====================================================================

def executar_sistema_hash():
    print("=" * 60)
    print("        LABORATÓRIO DE HASH: ALGORITMO SHA-256        ")
    print("=" * 60)
    print("[Nota do Professor] O processo que ocorrerá aqui é de mão única.\n")
    
    mensagem_usuario = input("Digite a mensagem, documento ou senha para gerar o Hash: ")
    
    if not mensagem_usuario:
        print("[Erro] O texto de entrada não pode ser vazio.")
        return
        
    print("\n[Passo 1] Quebrando a mensagem em bits e adicionando padding...")
    print("[Passo 2] Rodando 64 rodadas de operações bitwise...")
    
    # Chama nossa implementação construída do zero
    resultado_hash = gerar_sha256(mensagem_usuario)
    
    print("-" * 60)
    print(f"Texto Original : '{mensagem_usuario}'")
    print(f"Hash SHA-256   : {resultado_hash}")
    print("Tamanho        : 256 Bits (64 caracteres hexadecimais)")
    print("-" * 60)

if __name__ == "__main__":
    executar_sistema_hash()