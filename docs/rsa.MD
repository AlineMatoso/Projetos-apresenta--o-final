

O algoritmo **RSA** (Rivest-Shamir-Adleman). Lançado em 1977, ele resolveu um dos maiores dilemas da história da computação: **como duas pessoas podem trocar mensagens seguras sem que precisem combinar uma senha secreta presencialmente antes?**

## 1. O Conceito Fundamental: Criptografia Assimétrica

Até a invenção da criptografia de chave pública, o mundo utilizava a **criptografia simétrica** (como o AES ou a Cifra de César), onde a mesma chave que tranca a mensagem é utilizada para destrancá-la. O problema? Se um canal de comunicação for interceptado, como enviar a chave para o destinatário sem que o invasor também a pegue?

O RSA quebra esse paradigma utilizando a **Criptografia Assimétrica**. Em vez de uma chave, trabalhamos com um **Par de Chaves**:

* **Chave Pública (Public Key):** Funciona como uma caixa de correio com uma fenda. Qualquer pessoa no mundo pode colocar uma carta lá dentro (criptografar), mas ninguém consegue puxar a carta de volta pela fenda. Ela pode — e deve — ser distribuída livremente.
* **Chave Privada (Private Key):** É a chave física que abre a portinha traseira da caixa de correio. Apenas o dono da caixa possui essa chave. Ela é usada para ler as mensagens (descriptografar) e **nunca** deve ser compartilhada.

---

## 2. Arquitetura Limpa para o Algoritmo

Para construir um software sustentável, modular e testável, não podemos colocar toda a matemática e a lógica de texto em um único bloco de código. Dividimos o RSA em uma arquitetura de três camadas principais com responsabilidades únicas:

[ Camada 1: Utilitários Matemáticos ]
│ (Primalidade, MDC, Inverso Modular)
▼
[ Camada 2: Geração de Chaves ]
│ (Criação do par de chaves usando p, q, n, e, d)
▼
[ Camada 3: Criptografia / Descriptografia ]
(Manipulação de Mensagens e Operações Modulares)



1.  **Módulo Matemático Base:** Contém as funções aritméticas de alta precisão (MDC, Teste de Primalidade, Algoritmo de Euclides Estendido).
2.  **Módulo de Gerenciamento de Chaves:** Orquestra a escolha dos números primos e calcula as variáveis estruturais.
3.  **Módulo de Cifra:** Transforma cadeias de caracteres (strings) em representações numéricas e aplica as exponenciações modulares necessárias para encriptar e desencriptar.

---

## 3. O Processo das Chaves: A Matemática Passo a Passo

A segurança do RSA repousa sobre um fato matemático simples: **é muito fácil multiplicar dois números primos grandes, mas é extremamente difícil fazer o caminho inverso (fatorar o resultado) se você não souber quais eram os números originais.**

Vamos ao algoritmo de geração de chaves:

### Passo 1: Escolha dos Primos
Escolhemos dois números primos muito grandes e distintos, chamados $p$ e $q$.
* *Nota do Professor:* Em sistemas reais, $p$ e $q$ possuem milhares de bits. Para o nosso exemplo didático, usaremos números menores.

### Passo 2: Cálculo do Módulo ($n$)
Multiplicamos os dois primos para obter o módulo $n$:
$$n = p \times q$$
O número $n$ define o tamanho máximo da mensagem que podemos criptografar e fará parte de **ambas** as chaves.

### Passo 3: Cálculo da Função Totiente de Euler ($\phi(n)$)
Calculamos quantos números menores que $n$ são coprimos a ele. Para dois primos, a fórmula é direta:
$$\phi(n) = (p - 1) \times (q - 1)$$

### Passo 4: Escolha do Expoente Público ($e$)
Escolhemos um número inteiro $e$ que satisfaça duas condições:
1.  $1 < e < \phi(n)$
2.  $e$ deve ser **coprimo** com $\phi(n)$, ou seja, $\text{MDC}(e, \phi(n)) = 1$.
* *Dica de mercado:* O valor mais comum utilizado na internet hoje para $e$ é $65537$, por ser computacionalmente eficiente.

### Passo 5: Cálculo do Expoente Privado ($d$)
Calculamos $d$ como o **inverso multiplicativo modular** de $e$ em relação a $\phi(n)$. Isso significa que:
$$(d \times e) \pmod{\phi(n)} = 1$$
Para encontrar esse número de forma eficiente, usamos o **Algoritmo de Euclides Estendido**.

### Composição Final das Chaves:
* **Chave Pública:** Composta pelo par $(e, n)$
* **Chave Privada:** Composta pelo par $(d, n)$

Os valores de $p$, $q$ e $\phi(n)$ devem ser **destruídos** ou ocultados imediatamente após esse processo, pois se alguém os descobrir, conseguirá calcular $d$ a partir de $e$.

---

## 4. O Fluxo de Funcionamento (Cifra e Decifra)

Com as chaves em mãos, o fluxo de envio de uma mensagem de texto de Alice para Bob funciona da seguinte forma:

Alice (Emissora)                                      Bob (Receptor)
┌───────────────┐                                     ┌───────────────┐
│ Texto Puro (M)│                                     │Texto Decifrado│
└───────┬───────┘                                     └───────▲───────┘
│                                                     │
▼                                                     │
┌───────────────┐                                     ┌───────┴───────┐
│Criptografia   │ ── C = M^e mod n ──> [ Canal ] ───> │Descriptografia│
│(Chave Pública)│                      Inseguro       │(Chave Privada)│
└───────────────┘                                     └───────────────┘


### Criptografia (Encerramento da Mensagem)
1. Alice transforma seu texto em um número (ou lista de números) $M$, garantindo que $M < n$.
2. Ela aplica a fórmula matemática usando a **Chave Pública** de Bob $(e, n)$:
   $$C = M^e \pmod n$$
3. $C$ é o texto cifrado (número resultante), que pode ser enviado publicamente sem perigo.

### Descriptografia (Abertura da Mensagem)
1. Bob recebe o número cifrado $C$.
2. Ele usa sua **Chave Privada** $(d, n)$ para reverter a operação:
   $$M = C^d \pmod n$$
3. Graças ao Pequeno Teorema de Fermat e ao Teorema de Euler, a matemática garante que o resultado final $M$ recuperado será exatamente igual ao $M$ original enviado por Alice.
4. Bob reconverte o número $M$ em caracteres legíveis.

---

## 5. Código de Referência Comentado

Aqui está a tradução perfeita desta arquitetura limpa em código Python:

```python
import random
import math

# =====================================================================
# CAMADA 1: UTILIÁRIOS MATEMÁTICOS BASE
# =====================================================================

def eh_primo(num: int) -> bool:
    \"\"\"Verifica a primalidade usando o método da raiz quadrada.\"\"\"
    if num < 2:
        return False
    for i in range(2, int(math.isqrt(num)) + 1):
        if num % i == 0:
            return False
    return True

def mdc(a: int, b: int) -> int:
    \"\"\"Algoritmo de Euclides para o Máximo Divisor Comum.\"\"\"
    while b != 0:
        a, b = b, a % b
    return a

def inverso_modular(e: int, phi: int) -> int:
    \"\"\"Algoritmo de Euclides Estendido para encontrar o inverso modular d.\"\"\"
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
    \"\"\"Gera as chaves pública e privada a partir de dois primos.\"\"\"
    if not (eh_primo(p) and eh_primo(q)):
        raise ValueError("Ambos os números precisam ser primos.")
    if p == q:
        raise ValueError("Os números primos p e q não podem ser iguais.")

    # n = módulo
    n = p * q

    # phi = função totiente de Euler
    phi = (p - 1) * (q - 1)

    # Escolha do expoente público 'e' coprimo com phi
    e = random.randrange(2, phi)
    while mdc(e, phi) != 1:
        e = random.randrange(2, phi)

    # Cálculo do expoente privado 'd'
    d = inverso_modular(e, phi)

    # Retorna ((Chave Pública), (Chave Privada))
    return ((e, n), (d, n))

# =====================================================================
# CAMADA 3: PROCESSAMENTO DA CIFRA
# =====================================================================

def criptografar(chave_publica: tuple, texto_puro: str) -> list:
    \"\"\"Criptografa o texto usando a fórmula C = M^e mod n.\"\"\"
    e, n = chave_publica
    # Converte cada letra para ASCII e encripta numericamente
    texto_cifrado = [pow(ord(caractere), e, n) for caractere in texto_puro]
    return texto_cifrado

def descriptografar(chave_privada: tuple, texto_cifrado: list) -> str:
    \"\"\"Descriptografar os números usando a fórmula M = C^d mod n.\"\"\"
    d, n = chave_privada
    # Desfaz a criptografia modular e reverte de ASCII para caractere
    texto_puro = "".join([chr(pow(numero, d, n)) for numero in texto_cifrado])
    return texto_puro

# =====================================================================
# DEMONSTRAÇÃO PRÁTICA EM COMPUTAÇÃO
# =====================================================================
if __name__ == "__main__":
    print("--- Execução do Algoritmo RSA ---")
    
    # 1. Definição de primos acadêmicos (Na prática seriam primos imensos)
    primo_p = 61
    primo_q = 53
    
    # 2. Geração das Chaves
    publica, privada = gerar_par_de_chaves(primo_p, primo_q)
    print(f"[INFO] Chave Pública (e, n): {publica}")
    print(f"[INFO] Chave Privada (d, n): {privada}\\n")
    
    # 3. Mensagem original
    mensagem = "RSA_E_FANTASTICO"
    print(f"Mensagem Original: {mensagem}")
    
    # 4. Processo de Criptografia
    mensagem_protegida = criptografar(publica, mensagem)
    print(f"Mensagem Enviada (Cifrada): {mensagem_protegida}")
    
    # 5. Processo de Descriptografia
    mensagem_recuperada = descriptografar(privada, mensagem_protegida)
    print(f"Mensagem Recebida (Decifrada): {mensagem_recuperada}")

```

**Resumo para a prova:**

* A criptografia assimétrica usa chaves diferentes para criptografar e descriptografar.
* A segurança vem da **fatoração de números primos**.
* A arquitetura limpa isola a matemática pesada das funções que operam dados textuais.

Bons estudos, turma. Nos vemos no próximo laboratório de algoritmos!
"""
