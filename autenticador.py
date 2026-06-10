import os

# =====================================================================
# CAMADAS 1, 2 e 3: O NÚCLEO DO SHA-256 
# =====================================================================
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

H_INICIAL = (
    0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
    0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19
)

def rotr(x: int, n: int) -> int: return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF
def ch(x: int, y: int, z: int) -> int: return (x & y) ^ (~x & z)
def maj(x: int, y: int, z: int) -> int: return (x & y) ^ (x & z) ^ (y & z)
def sigma0_upper(x: int) -> int: return rotr(x, 2) ^ rotr(x, 13) ^ rotr(x, 22)
def sigma1_upper(x: int) -> int: return rotr(x, 6) ^ rotr(x, 11) ^ rotr(x, 25)
def sigma0_lower(x: int) -> int: return rotr(x, 7) ^ rotr(x, 18) ^ (x >> 3)
def sigma1_lower(x: int) -> int: return rotr(x, 17) ^ rotr(x, 19) ^ (x >> 10)

def gerar_sha256(dados_binarios: bytes) -> str:
    mensagem_bytes = bytearray(dados_binarios)
    tamanho_original_bits = len(mensagem_bytes) * 8

    mensagem_bytes.append(0x80)
    while (len(mensagem_bytes) * 8) % 512 != 448:
        mensagem_bytes.append(0x00)
    mensagem_bytes.extend(tamanho_original_bits.to_bytes(8, 'big'))

    h = list(H_INICIAL)

    for i in range(0, len(mensagem_bytes), 64):
        bloco = mensagem_bytes[i:i+64]
        w = [0] * 64
        for j in range(16):
            w[j] = int.from_bytes(bloco[j*4:(j+1)*4], 'big')
        for j in range(16, 64):
            s0 = sigma0_lower(w[j-15])
            s1 = sigma1_lower(w[j-2])
            w[j] = (w[j-16] + s0 + w[j-7] + s1) & 0xFFFFFFFF

        a, b, c, d, e, f, g, h_var = h

        for j in range(64):
            temp1 = (h_var + sigma1_upper(e) + ch(e, f, g) + K[j] + w[j]) & 0xFFFFFFFF
            temp2 = (sigma0_upper(a) + maj(a, b, c)) & 0xFFFFFFFF
            h_var, g, f, e, d, c, b, a = g, f, e, (d + temp1) & 0xFFFFFFFF, c, b, a, (temp1 + temp2) & 0xFFFFFFFF

        h[0] = (h[0] + a) & 0xFFFFFFFF
        h[1] = (h[1] + b) & 0xFFFFFFFF
        h[2] = (h[2] + c) & 0xFFFFFFFF
        h[3] = (h[3] + d) & 0xFFFFFFFF
        h[4] = (h[4] + e) & 0xFFFFFFFF
        h[5] = (h[5] + f) & 0xFFFFFFFF
        h[6] = (h[6] + g) & 0xFFFFFFFF
        h[7] = (h[7] + h_var) & 0xFFFFFFFF

    return ''.join(f'{valor:08x}' for valor in h)

def obter_hash_de_arquivo(caminho_arquivo: str) -> str:
    with open(caminho_arquivo, 'rb') as arquivo:
        return gerar_sha256(arquivo.read())

def validar_arquivo(caminho_arquivo: str, hash_fornecido: str) -> bool:
    return obter_hash_de_arquivo(caminho_arquivo).lower() == hash_fornecido.lower()


# =====================================================================
# CAMADA 4: NOVA INTERFACE COM LEITURA AUTOMÁTICA DA PASTA
# =====================================================================

def escanear_arquivos_txt():
    """Descobre a pasta atual do script e lista todos os arquivos .txt nela."""
    # 1. Descobre o caminho absoluto da pasta onde este script python está salvo
    pasta_do_script = os.path.dirname(os.path.abspath(__file__))
    
    # 2. Lista todos os arquivos que terminam com '.txt'
    arquivos_txt = [f for f in os.listdir(pasta_do_script) if f.endswith('.txt')]
    
    return arquivos_txt, pasta_do_script

def selecionar_arquivo_do_menu():
    """Exibe os arquivos txt encontrados e pede para o usuário escolher um."""
    arquivos, pasta = escanear_arquivos_txt()
    
    if not arquivos:
        print("\n[Erro] Nenhum arquivo .txt foi encontrado na mesma pasta deste script!")
        print(f"Por favor, crie um arquivo de texto na pasta: \n{pasta}")
        return None
        
    print("\nArquivos .txt encontrados na pasta atual:")
    for indice, nome_arquivo in enumerate(arquivos):
        print(f"[{indice + 1}] {nome_arquivo}")
        
    while True:
        try:
            escolha = int(input("\nDigite o NÚMERO do arquivo que deseja usar: "))
            if 1 <= escolha <= len(arquivos):
                # Retorna o caminho completo e seguro para o arquivo escolhido
                nome_escolhido = arquivos[escolha - 1]
                return os.path.join(pasta, nome_escolhido)
            else:
                print("Número fora da lista. Tente novamente.")
        except ValueError:
            print("Por favor, digite apenas o número correspondente.")

def menu_aplicacao():
    while True:
        print("\n" + "=" * 55)
        print(" VERIFICADOR DE INTEGRIDADE DE ARQUIVOS (Auto-Scan) ")
        print("=" * 55)
        print("1. Gerar Hash de um arquivo .txt local")
        print("2. Validar autenticidade de um arquivo .txt local")
        print("3. Sair")
        
        opcao = input("\nEscolha uma opção: ")
        
        if opcao == '1':
            print("-" * 55)
            caminho_completo = selecionar_arquivo_do_menu()
            
            if caminho_completo:
                print("\n[Processando...] Lendo arquivo e calculando o Hash...")
                hash_gerado = obter_hash_de_arquivo(caminho_completo)
                nome_arquivo = os.path.basename(caminho_completo)
                
                print("-" * 55)
                print(f"HASH GERADO PARA O ARQUIVO '{nome_arquivo}':")
                print(f"{hash_gerado}")
                print("-" * 55)
                
        elif opcao == '2':
            print("-" * 55)
            caminho_completo = selecionar_arquivo_do_menu()
            
            if caminho_completo:
                hash_esperado = input("\nCole o Hash (SHA-256) original esperado: ")
                print("\n[Processando...] Calculando e comparando hashes...")
                
                hash_atual = obter_hash_de_arquivo(caminho_completo)
                nome_arquivo = os.path.basename(caminho_completo)
                
                print("\nResultado da Análise para o arquivo:", nome_arquivo)
                print(f"Hash Fornecido : {hash_esperado.lower()}")
                print(f"Hash do Arquivo: {hash_atual}")
                
                if validar_arquivo(caminho_completo, hash_esperado):
                    print("\nSTATUS: ARQUIVO AUTÊNTICO E VÁLIDO!")
                    print("A assinatura confere perfeitamente. Nenhuma alteração foi feita.")
                else:
                    print("\nSTATUS: ARQUIVO INVÁLIDO / CORROMPIDO!")
                    print("ATENÇÃO: O hash é diferente. O arquivo foi modificado!")
                    
        elif opcao == '3':
            print("Encerrando laboratório. Até a próxima aula!")
            break
        else:
            print("Opção inválida. Tente novamente.")

if __name__ == "__main__":
    menu_aplicacao()