#Breno Pinheiro Gallo de Sá - 2110183
#Felippe Petrasso Fonseca Hübner - 210870
#Eduardo Vasques Zacour - 1611696

import heapq
import math
from pathlib import Path
import random
import sys
from typing import Union

# Verifica se a biblioteca Pygame está instalda.
try:
    import pygame
except ImportError:
    print("ERRO: A biblioteca 'pygame' não está instalada.")
    print("Por favor, abra o terminal e digite: pip install pygame")
    sys.exit(1)

# Custo dos Tiles
CUSTOS_TERRENO = {
    '.': 1,    # Plano
    'R': 5,    # Rochoso
    'F': 10,   # Floresta (caractere usado no arquivo TXT)
    'V': 10,   # Floresta (conforme descrição do PDF)
    'A': 15,   # Água
    'M': 200,  # Montanhoso
}

# Personagens e agilidades
PERSONAGENS = [
    ("Aang",   1.8),
    ("Zuko",   1.6),
    ("Toph",   1.6),
    ("Katara", 1.6),
    ("Sokka",  1.4),
    ("Appa",   0.9),
    ("Momo",   0.7),
]

# 32 checkpoints representando as tarefas
CHECKPOINTS_ORDEM = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'B', 'C', 'D', 'E', 'G', 'H', 'I', 'J', 'K', 'L',
    'N', 'O', 'P', 'Q', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
]

# 31 etapas com dificuldade.
DIFICULDADES = [
     10,  20,  30,  40,  50,  60,  70,  80,  90, 100,
    110, 120, 130, 140, 150, 160, 170, 180, 190, 200,
    210, 220, 230, 240, 250, 260, 270, 280, 290, 300,
    310
]

MAX_USOS_POR_PERSONAGEM = 8
NUM_ETAPAS_ATIVAS = len(DIFICULDADES) 

# Configurações Pygame
TAMANHO_CELULA = 4  # pixels por célula da matriz

CORES = {
    '.': (240, 240, 240),         # Plano: branco
    'R': (139, 137, 137),         # Rochoso: cinza
    'F': (34,  139, 34),          # Floresta: verde
    'V': (34,  139, 34),          # Floresta: verde
    'A': (30,  144, 255),         # Água: azul
    'M': (139, 69,  19),          # Montanhoso: marrom
    'CHECKPOINT':         (255, 80,  80),   # Checkpoint: vermelho
    'CAMINHO':            (255, 215, 0),    # Rastro: amarelo
    'AVATAR':             (255, 50,  50),   # Avatar em movimento: vermelho
    'CHECKPOINT_ATINGIDO':(100, 255, 120),  # Avatar ao chegar: verde claro
}


MAPA_ARQUIVO = Path(__file__).resolve().with_name("MAPA_LENDA-AANG.txt") # Caminho relativo ao arquivo de mapa

#Carregar Mapa
def carregar_mapa(caminho_arquivo: Union[str, Path]):
    """
    Lê o arquivo TXT e retorna:
      - mapa: lista de listas de caracteres (82 x 300)
      - posicoes_checkpoints: dict {char -> (linha, coluna)}
    """
    with open(caminho_arquivo, 'r', encoding='utf-8') as f:
        linhas = f.read().splitlines()

    mapa = []
    posicoes_checkpoints = {}
    chars_checkpoint = set(CHECKPOINTS_ORDEM)

    for i, linha in enumerate(linhas):
        linha_lista = list(linha)
        mapa.append(linha_lista)
        for j, char in enumerate(linha_lista):
            if char in chars_checkpoint:
                posicoes_checkpoints[char] = (i, j)

    return mapa, posicoes_checkpoints

# =====================================================================
# 3. BUSCA HEURÍSTICA: A*
# =====================================================================

def distancia_manhattan(p1: tuple, p2: tuple) -> int:
    """
    Heurística admissível para o A*.
    O custo mínimo por célula é 1 (terreno plano), portanto a distância
    Manhattan nunca superestima o custo real → heurística consistente.
    Entrada:
        - p1, p2: tuplas (linha, coluna) representando posições no mapa
    Retorna:
        - distância Manhattan entre p1 e p2
    """
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def a_star(mapa: list, inicio: tuple, objetivo: tuple):
    """
    Algoritmo A* para menor custo entre dois pontos no mapa.

    Células de checkpoint são tratadas como terreno plano (custo 1) para
    fins de passagem — elas marcam posições, não alteram o custo de terreno.
    Entrada:
        - mapa (list[list[str]]): matriz do mapa lida do arquivo
        - inicio (tuple): coordenadas (linha, coluna) do checkpoint de início
        - objetivo (tuple): coordenadas (linha, coluna) do checkpoint de destino
    Retorna:
        - custo_total (int): custo acumulado do caminho ótimo
        - caminho (list[tuple]): lista de posições de 'inicio' até 'objetivo'
    """
    linhas, colunas = len(mapa), len(mapa[0])
    movimentos = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # sem diagonal

    # Heap: (f = g + h, g, posicao) f = custo total estimado, g = custo acumulado até aqui, h = heurística
    fronteira = [(distancia_manhattan(inicio, objetivo), 0, inicio)]
    custo_ate = {inicio: 0}
    veio_de = {}

    while fronteira:
        _, g_atual, no_atual = heapq.heappop(fronteira)

        if no_atual == objetivo:
            # Reconstrói o caminho completo incluindo início e fim
            caminho = []
            no = objetivo
            while no in veio_de:
                caminho.append(no)
                no = veio_de[no]
            caminho.append(inicio)
            return g_atual, caminho[::-1]

        # Descarta entradas desatualizadas do heap
        if g_atual > custo_ate.get(no_atual, float('inf')):
            continue

        for dx, dy in movimentos:
            nx, ny = no_atual[0] + dx, no_atual[1] + dy
            if 0 <= nx < linhas and 0 <= ny < colunas:
                terreno = mapa[nx][ny]
                # Checkpoints são passáveis com custo de terreno plano
                custo_movimento = CUSTOS_TERRENO.get(terreno, 1)
                novo_g = g_atual + custo_movimento

                if novo_g < custo_ate.get((nx, ny), float('inf')):
                    custo_ate[(nx, ny)] = novo_g
                    f = novo_g + distancia_manhattan((nx, ny), objetivo)
                    heapq.heappush(fronteira, (f, novo_g, (nx, ny)))
                    veio_de[(nx, ny)] = no_atual

    return float('inf'), []  # sem caminho

# =================================================================================================
# 4. BUSCA LOCAL: SIMULATED ANNEALING (SA) Meta-heurística para atribuição de personagens às etapas
# =================================================================================================

def calcular_tempo_etapas(estado: list, dificuldades: list, personagens: list) -> float:
    """
    Dado um estado (lista de listas de índices de personagens por etapa),
    calcula o tempo total das etapas ativas:
        T = Σ Dificuldade_i / Σ Agilidade_j  (para j no grupo da etapa i)
    Entrada:
    - estado: list[list[int]] → cada sublista contém os índices dos personagens alocados para aquela etapa
    - dificuldades: list[float] → dificuldade de cada etapa (tamanho 31)
    - personagens: list[tuple] → lista de tuplas (nome, agilidade) dos personagens
    Retorna:
    - tempo_total (float): tempo total calculado para o estado fornecido
    """
    tempo_total = 0.0
    for i, grupo in enumerate(estado):
        soma_agilidade = sum(personagens[c][1] for c in grupo)
        if soma_agilidade == 0:
            return float('inf')
        tempo_total += dificuldades[i] / soma_agilidade
    return tempo_total

def calcular_agilidades_etapas(estado: list, personagens: list) -> list:
    """
    Calcula a soma de agilidade de cada etapa para permitir atualizaÃ§Ãµes
    incrementais do custo no Simulated Annealing.
    """
    return [sum(personagens[c][1] for c in grupo) for grupo in estado]

def inicializar_estado_guloso(num_etapas: int, num_chars: int,
                               personagens: list, dificuldades: list):
    """
    Cria um estado inicial de qualidade para o SA em dois passos,
    respeitando o limite global para que alguém sobreviva.
    Entrada:
        - num_etapas: int → número total de etapas (31)
        - num_chars: int → número total de personagens (7)
        - personagens: list[tuple] → lista de tuplas (nome, agilidade)
        - dificuldades: list[float] → dificuldade de cada etapa (tamanho 31)
    Retorna:
        - estado: list[list[int]] → cada sublista contém os índices dos personagens alocados para aquela etapa
        - usos: list[int] → contagem de quantas vezes cada personagem foi alocado
    """
    estado = [[] for _ in range(num_etapas)]
    usos = [0] * num_chars
    
    #Limite máximo global para garantir que ao menos 1 personagem não gaste tudo
    MAX_TOTAL_USOS = (num_chars * MAX_USOS_POR_PERSONAGEM) - 1

    # --- Fase 1: um personagem obrigatório por etapa ---
    ordem_dificuldade = sorted(range(num_etapas), key=lambda i: -dificuldades[i])
    for i in ordem_dificuldade:
        disponiveis = sorted(
            [c for c in range(num_chars) if usos[c] < MAX_USOS_POR_PERSONAGEM],
            key=lambda c: -personagens[c][1]
        )
        if disponiveis:
            c_melhor = disponiveis[0]
            estado[i].append(c_melhor)
            usos[c_melhor] += 1

    # --- Fase 2: slots restantes por máximo benefício marginal ---
    def beneficio_marginal(i, c):
        """
        Função interna.
        Calcula o benefício marginal de adicionar o personagem c à etapa i.
        Entrada:
            - i: índice da etapa (0 a 30)
            - c: índice do personagem (0 a 6)
        Retorna:
            - benefício marginal (float): redução no tempo da etapa i se c for adicionado
        """
        D = dificuldades[i]
        A = sum(personagens[x][1] for x in estado[i])
        if A == 0:
            return float('inf')
        return D / A - D / (A + personagens[c][1])

    heap_bm = []
    for i in range(num_etapas):
        for c in range(num_chars):
            if c not in estado[i] and usos[c] < MAX_USOS_POR_PERSONAGEM:
                heapq.heappush(heap_bm, (-beneficio_marginal(i, c), i, c))

    # Só continua distribuindo se a soma global não atingir o limite de 55
    while heap_bm and sum(usos) < MAX_TOTAL_USOS:
        neg_b, i, c = heapq.heappop(heap_bm)
        if c in estado[i] or usos[c] >= MAX_USOS_POR_PERSONAGEM:
            continue
        # Revalida: o benefício pode ter mudado se a etapa recebeu outro char
        b_real = beneficio_marginal(i, c)
        if abs(b_real - (-neg_b)) > 1e-9:
            heapq.heappush(heap_bm, (-b_real, i, c))
            continue
        estado[i].append(c)
        usos[c] += 1
        for c2 in range(num_chars):
            if c2 not in estado[i] and usos[c2] < MAX_USOS_POR_PERSONAGEM:
                heapq.heappush(heap_bm, (-beneficio_marginal(i, c2), i, c2))

    return estado, usos

def resolver_etapas_simulated_annealing(dificuldades: list, personagens: list):
    """
    Simulated Annealing otimizando o limite máximo global de uso.
    Entrada:
        - dificuldades: list[float] → dificuldade de cada etapa (tamanho 31)
        - personagens: list[tuple] → lista de tuplas (nome, agilidade)
    Retorna:
        - melhor_global_tempo (float): tempo total das etapas para o melhor estado encontrado
        - melhor_global_estado (list[list[int]]): estado correspondente ao melhor tempo encontrado
    """
    num_etapas = len(dificuldades)
    num_chars  = len(personagens)

    # Configuração enxuta: mantém o SA, mas com custo incremental e
    # execução reprodutível para convergir dentro do tempo esperado.
    T_INICIAL        = 60.0
    T_FINAL          = 0.02
    FATOR_RESFR      = 0.96
    ITER_POR_T       = 500
    NUM_TENTATIVAS   = 7
    
    # Limite máximo global para validação de adições
    MAX_TOTAL_USOS = (num_chars * MAX_USOS_POR_PERSONAGEM) - 1

    melhor_global_tempo = float('inf')
    melhor_global_estado = None
    rng = random.Random(0)

    for tentativa in range(NUM_TENTATIVAS):
        estado, usos = inicializar_estado_guloso(
            num_etapas, num_chars, personagens, dificuldades
        )
        agilidades = calcular_agilidades_etapas(estado, personagens)
        total_usos = sum(usos)
        tempo_atual = sum(
            dificuldades[i] / agilidades[i] for i in range(num_etapas)
        )

        melhor_local_tempo = tempo_atual
        melhor_local_estado = [list(e) for e in estado]

        if tempo_atual < melhor_global_tempo:
            melhor_global_tempo = tempo_atual
            melhor_global_estado = [list(e) for e in estado]
        
        temperatura = T_INICIAL

        while temperatura > T_FINAL:
            for _ in range(ITER_POR_T):
                tipo_mov = rng.random()
                movimento = None
                delta = None

                if tipo_mov < 0.35:
                    # transfere um personagem entre etapas sem deixar a origem vazia
                    c = rng.randrange(num_chars)
                    etapas_com = [
                        i for i in range(num_etapas)
                        if c in estado[i] and len(estado[i]) > 1
                    ]
                    etapas_sem = [i for i in range(num_etapas) if c not in estado[i]]
                    if not etapas_com or not etapas_sem:
                        continue
                    origem = rng.choice(etapas_com)
                    agilidade_char = personagens[c][1]
                    destino = rng.choice(etapas_sem)
                    delta = (
                        dificuldades[origem] / (agilidades[origem] - agilidade_char)
                        - dificuldades[origem] / agilidades[origem]
                        + dificuldades[destino] / (agilidades[destino] + agilidade_char)
                        - dificuldades[destino] / agilidades[destino]
                    )
                    movimento = ("transferir", c, origem, destino)

                elif tipo_mov < 0.70:
                    # permuta personagens entre duas etapas para escapar de mínimos locais
                    e1, e2 = rng.sample(range(num_etapas), 2)
                    op_c1 = [c for c in estado[e1] if c not in estado[e2]]
                    op_c2 = [c for c in estado[e2] if c not in estado[e1]]
                    if not op_c1 or not op_c2:
                        continue
                    c1 = rng.choice(op_c1)
                    c2 = rng.choice(op_c2)
                    a1 = personagens[c1][1]
                    a2 = personagens[c2][1]
                    delta = (
                        dificuldades[e1] / (agilidades[e1] - a1 + a2)
                        - dificuldades[e1] / agilidades[e1]
                        + dificuldades[e2] / (agilidades[e2] - a2 + a1)
                        - dificuldades[e2] / agilidades[e2]
                    )
                    movimento = ("trocar", e1, c1, e2, c2)

                elif tipo_mov < 0.85:
                    # insere personagem, respeitando o limite global e o individual
                    if total_usos >= MAX_TOTAL_USOS:
                        continue
                        
                    c = rng.randrange(num_chars)
                    if usos[c] >= MAX_USOS_POR_PERSONAGEM:
                        continue
                    etapas_sem = [i for i in range(num_etapas) if c not in estado[i]]
                    if not etapas_sem:
                        continue
                    etapa = rng.choice(etapas_sem)
                    agilidade_char = personagens[c][1]
                    delta = (
                        dificuldades[etapa] / (agilidades[etapa] + agilidade_char)
                        - dificuldades[etapa] / agilidades[etapa]
                    )
                    movimento = ("inserir", c, etapa)

                else:
                    # retira personagem de uma etapa sem deixá-la vazia
                    candidatas = [i for i in range(num_etapas) if len(estado[i]) > 1]
                    if not candidatas:
                        continue
                    etapa = rng.choice(candidatas)
                    c = rng.choice(estado[etapa])
                    agilidade_char = personagens[c][1]
                    delta = (
                        dificuldades[etapa] / (agilidades[etapa] - agilidade_char)
                        - dificuldades[etapa] / agilidades[etapa]
                    )
                    movimento = ("retirar", c, etapa)

                if movimento is None:
                    continue

                if delta < 0 or rng.random() < math.exp(-delta / temperatura):
                    tipo = movimento[0]

                    if tipo == "transferir":
                        _, c, origem, destino = movimento
                        agilidade_char = personagens[c][1]
                        estado[origem].remove(c)
                        estado[destino].append(c)
                        agilidades[origem] -= agilidade_char
                        agilidades[destino] += agilidade_char

                    elif tipo == "trocar":
                        _, e1, c1, e2, c2 = movimento
                        a1 = personagens[c1][1]
                        a2 = personagens[c2][1]
                        estado[e1].remove(c1)
                        estado[e1].append(c2)
                        estado[e2].remove(c2)
                        estado[e2].append(c1)
                        agilidades[e1] += a2 - a1
                        agilidades[e2] += a1 - a2

                    elif tipo == "inserir":
                        _, c, etapa = movimento
                        agilidade_char = personagens[c][1]
                        estado[etapa].append(c)
                        usos[c] += 1
                        total_usos += 1
                        agilidades[etapa] += agilidade_char

                    else:
                        _, c, etapa = movimento
                        agilidade_char = personagens[c][1]
                        estado[etapa].remove(c)
                        usos[c] -= 1
                        total_usos -= 1
                        agilidades[etapa] -= agilidade_char

                    tempo_atual += delta
                    if tempo_atual < melhor_local_tempo - 1e-12:
                        melhor_local_tempo = tempo_atual
                        melhor_local_estado = [list(e) for e in estado]
                        if melhor_local_tempo < melhor_global_tempo - 1e-12:
                            melhor_global_tempo = melhor_local_tempo
                            melhor_global_estado = [list(e) for e in estado]

            temperatura *= FATOR_RESFR

        print(f"  Tentativa {tentativa + 1}/{NUM_TENTATIVAS}: "
              f"{melhor_local_tempo:.6f} min  "
              f"(melhor global: {melhor_global_tempo:.6f} min)")

    return melhor_global_tempo, melhor_global_estado or melhor_local_estado

# =====================================================================
# 5. SAÍDA DE RESULTADOS NO TERMINAL
# =====================================================================

def exibir_resultado_etapas(esquema: list, personagens: list, dificuldades: list):
    """
    Imprime a tabela de atribuição de personagens por etapa.
    Entrada:
        - esquema: list[list[int]] → cada sublista contém os índices dos personagens alocados para aquela etapa
        - personagens: list[tuple] → lista de tuplas (nome, agilidade)
        - dificuldades: list[float] → dificuldade de cada etapa
    Retorna:
        - None (imprime a tabela formatada no terminal)
    """
    print(f"\n  {'Etapa':>5} | {'Dif.':>4} | {'Personagens':<36} | {'Agil.':>5} | {'Tempo':>8}")
    print("  " + "-" * 72)
    usos_totais = {p[0]: 0 for p in personagens}
    for i, grupo in enumerate(esquema):
        num_etapa = i + 1  # etapas 1 a 31
        D = dificuldades[i]
        A = sum(personagens[c][1] for c in grupo)
        t = D / A
        nomes = ", ".join(personagens[c][0] for c in sorted(grupo))
        for c in grupo:
            usos_totais[personagens[c][0]] += 1
        print(f"  {num_etapa:>5} | {D:>4} | {nomes:<36} | {A:>5.2f} | {t:>13.6f}")

    print("\n  Usos por personagem:")
    for nome, cnt in usos_totais.items():
        barra = '█' * cnt + '░' * (MAX_USOS_POR_PERSONAGEM - cnt)
        print(f"    {nome:<8}: [{barra}] {cnt}/{MAX_USOS_POR_PERSONAGEM}")

# =====================================================================
# 6. INTERFACE GRÁFICA (PYGAME)
# =====================================================================

def pre_renderizar_mapa(mapa: list) -> pygame.Surface:
    """
    Pré-renderiza todo o bioma do mapa em uma Surface estática.
    Isso evita redesenhar cada célula a cada frame, reduzindo o custo de CPU.
    Entrada:
        - mapa: list[list[str]] → matriz do mapa lida do arquivo
    Retorna:
        - superficie: pygame.Surface → superfície pré-renderizada do mapa
    """
    linhas   = len(mapa)
    colunas  = len(mapa[0])
    largura  = colunas * TAMANHO_CELULA
    altura   = linhas  * TAMANHO_CELULA
    superficie = pygame.Surface((largura, altura))

    chars_ckpt = set(CHECKPOINTS_ORDEM)
    for i, linha in enumerate(mapa):
        for j, char in enumerate(linha):
            cor = CORES['CHECKPOINT'] if char in chars_ckpt else CORES.get(char, CORES['.'])
            pygame.draw.rect(
                superficie, cor,
                pygame.Rect(j * TAMANHO_CELULA, i * TAMANHO_CELULA,
                            TAMANHO_CELULA, TAMANHO_CELULA)
            )
    return superficie

def executar_visualizacao(mapa: list, rota_completa: list,
                           indices_checkpoints: dict, custo_final: float, 
                           tempos_por_etapa: list): # <-- Recebe os tempos das etapas calculados pelo SA
    """
    Loop principal do Pygame.
    Anima o avatar percorrendo a rota_completa passo a passo,
    pausa brevemente ao atingir cada checkpoint, e exibe um HUD com
    o contador de checkpoints e o custo acumulado em tempo real.
    Entrada:
        - mapa: list[list[str]] → matriz do mapa lida do arquivo
        - rota_completa: list[tuple] → lista de posições (linha, coluna)
        - indices_checkpoints: dict → dicionário com os índices dos checkpoints
        - custo_final: float → custo total da rota
        - tempos_por_etapa: list[float] → tempos calculados para cada etapa
    Retorna:
        - None (inicia a janela gráfica e executa a animação)
    """
    pygame.init()
    fonte_titulo = pygame.font.SysFont('Arial', 20, bold=True)
    fonte_info   = pygame.font.SysFont('Arial', 16, bold=True)

    linhas_mapa  = len(mapa)
    colunas_mapa = len(mapa[0])
    largura_tela = colunas_mapa * TAMANHO_CELULA
    altura_tela  = linhas_mapa  * TAMANHO_CELULA

    tela = pygame.display.set_mode((largura_tela, altura_tela))
    pygame.display.set_caption(f"Jornada de Aang — Custo Total: {custo_final:.2f} min")

    sup_mapa = pre_renderizar_mapa(mapa)

    sup_rastro = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
    sup_rastro.fill((0, 0, 0, 0))

    relogio           = pygame.time.Clock()
    rodando           = True
    passo_atual       = 0
    total_passos      = len(rota_completa)
    ckpts_visitados   = set()
    etapas_concluidas = 0
    
    # Alterado para float para comportar os decimais das etapas com precisão
    custo_acumulado   = 0.0  

    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

        chegou_em_checkpoint = False

        if passo_atual < total_passos:
            i_pos, j_pos = rota_completa[passo_atual]

            pygame.draw.rect(
                sup_rastro,
                (*CORES['CAMINHO'], 210),
                pygame.Rect(j_pos * TAMANHO_CELULA, i_pos * TAMANHO_CELULA,
                            TAMANHO_CELULA, TAMANHO_CELULA)
            )

            # 1. Soma o custo do terreno (A*) ao dar um passo
            if passo_atual > 0:
                terreno = mapa[i_pos][j_pos]
                custo_passo = CUSTOS_TERRENO.get(terreno, 1)
                custo_acumulado += custo_passo

            # 2. Verifica se chegou no Checkpoint final de uma etapa
            for char, idx in indices_checkpoints.items():
                if passo_atual == idx and char not in ckpts_visitados:
                    ckpts_visitados.add(char)
                    
                    # --- NOVA LÓGICA: SOMA O CUSTO DA ETAPA (SA) ---
                    # Se houver uma etapa correspondente, soma o tempo calculado para ela
                    if etapas_concluidas < len(tempos_por_etapa):
                        custo_acumulado += tempos_por_etapa[etapas_concluidas]
                    # -----------------------------------------------
                    
                    etapas_concluidas += 1
                    chegou_em_checkpoint = True

            passo_atual += 1

        tela.blit(sup_mapa,   (0, 0))
        tela.blit(sup_rastro, (0, 0))

        if passo_atual > 0:
            idx_atual = min(passo_atual - 1, total_passos - 1)
            i_av, j_av = rota_completa[idx_atual]
            cx = j_av * TAMANHO_CELULA + TAMANHO_CELULA // 2
            cy = i_av * TAMANHO_CELULA + TAMANHO_CELULA // 2
            cor_av = (CORES['CHECKPOINT_ATINGIDO']
                      if chegou_em_checkpoint else CORES['AVATAR'])
            pygame.draw.circle(tela, cor_av, (cx, cy), TAMANHO_CELULA + 1)

        txt_etapas = fonte_titulo.render(
            f"Checkpoints: {etapas_concluidas} / 31", True, (255, 255, 255)
        )
        
        # UI Condicional: Caminho em progresso vs Custo Final
        if passo_atual < total_passos:
            # Texto atualizado para "Custo Acumulado" e formatado com duas casas decimais
            txt_custo = fonte_info.render(
                f"Custo Acumulado: {custo_acumulado:.2f} min", True, (255, 255, 255)
            )
        else:
            txt_custo = fonte_info.render(
                f"CUSTO FINAL: {custo_final:.2f} min", True, (100, 255, 120)
            )

        hud_w = max(txt_etapas.get_width(), txt_custo.get_width()) + 24
        hud_h = txt_etapas.get_height() + txt_custo.get_height() + 16
        hud   = pygame.Surface((hud_w, hud_h))
        hud.fill((0, 0, 0))
        hud.set_alpha(180)
        
        tela.blit(hud,        (10, 10))
        tela.blit(txt_etapas, (22, 15))
        tela.blit(txt_custo,  (22, 15 + txt_etapas.get_height() + 5))

        pygame.display.flip()

        if chegou_em_checkpoint:
            pygame.time.delay(300)

        relogio.tick(60)

    pygame.quit()

# =====================================================================
# 7. EXECUÇÃO PRINCIPAL
# =====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("      Jornada de Aang — Agente Inteligente (INF1771)")
    print("=" * 60)

    print("\n[1/3] Carregando mapa...")
    mapa, checkpoints = carregar_mapa(MAPA_ARQUIVO)
    print(f"      Dimensões: {len(mapa)} x {len(mapa[0])}  |  "
          f"Checkpoints encontrados: {len(checkpoints)}")

    print("\n[2/3] Executando A* entre checkpoints...")
    tempo_viagem_total = 0
    rota_completa      = []
    indices_checkpoints = {}

    for i in range(len(CHECKPOINTS_ORDEM) - 1):
        origem_char  = CHECKPOINTS_ORDEM[i]
        destino_char = CHECKPOINTS_ORDEM[i + 1]

        custo, rota = a_star(mapa, checkpoints[origem_char], checkpoints[destino_char])
        tempo_viagem_total += custo

        if i == 0:
            rota_completa.extend(rota)
        else:
            rota_completa.extend(rota[1:])

        indices_checkpoints[destino_char] = len(rota_completa) - 1
        print(f"      {origem_char} → {destino_char}: {custo} min")

    print(f"\n      Tempo total de viagem (A*): {tempo_viagem_total} minutos")

    print("\n[3/3] Otimizando atribuição de personagens (Simulated Annealing (SA))...")
    tempo_etapas, esquema = resolver_etapas_simulated_annealing(DIFICULDADES, PERSONAGENS)
    exibir_resultado_etapas(esquema, PERSONAGENS, DIFICULDADES)

    # --- NOVO: Extração dos tempos individuais por etapa gerados pelo SA ---
    tempos_por_etapa = []
    for i, grupo in enumerate(esquema):
        D = DIFICULDADES[i]
        A = sum(PERSONAGENS[c][1] for c in grupo)
        tempos_por_etapa.append(D / A)
    # -----------------------------------------------------------------------

    custo_final = tempo_viagem_total + tempo_etapas

    print("\n" + "=" * 60)
    print("                   RESULTADO FINAL")
    print("=" * 60)
    print(f"  Tempo de viagem  (A*) :  {tempo_viagem_total:>10} minutos")
    print(f"  Tempo das etapas (SA) :  {tempo_etapas:>16.6f} minutos")
    print(f"  CUSTO FINAL DO AGENTE:   {custo_final:>16.6f} minutos")
    print("=" * 60)
    print("\nAbrindo visualização gráfica... (feche a janela para encerrar)\n")

    # Passamos a lista de tempos das etapas para a visualização gráfica
    executar_visualizacao(mapa, rota_completa, indices_checkpoints, custo_final, tempos_por_etapa)
