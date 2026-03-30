import heapq
import math
import random
import sys

try:
    import pygame
except ImportError:
    print("ERRO: A biblioteca 'pygame' não está instalada.")
    print("Por favor, abra o terminal e digite: pip install pygame")
    sys.exit(1)

# =====================================================================
# 1. CONFIGURAÇÕES DO AMBIENTE E DADOS
# =====================================================================

CUSTOS_TERRENO = {
    '.': 1,    # Plano
    'R': 5,    # Rochoso
    'F': 10,   # Floresta (caractere usado no arquivo TXT)
    'V': 10,   # Floresta (conforme descrição do PDF)
    'A': 15,   # Água
    'M': 200,  # Montanhoso
}

# Personagens e agilidades conforme o PDF
PERSONAGENS = [
    ("Aang",   1.8),
    ("Zuko",   1.6),
    ("Toph",   1.6),
    ("Katara", 1.6),
    ("Sokka",  1.4),
    ("Appa",   0.9),
    ("Momo",   0.7),
]

# 32 checkpoints na ordem da jornada
CHECKPOINTS_ORDEM = [
    '0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'B', 'C', 'D', 'E', 'G', 'H', 'I', 'J', 'K', 'L',
    'N', 'O', 'P', 'Q', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
]

# 31 etapas com dificuldade (etapas 1 a 31), conforme a Tabela 1 do PDF.
# Cada valor corresponde ao segmento entre checkpoints consecutivos:
#   0→1 (etapa 1, dif. 10), 1→2 (etapa 2, dif. 20), ..., Y→Z (etapa 31, dif. 310)
DIFICULDADES = [
     10,  20,  30,  40,  50,  60,  70,  80,  90, 100,
    110, 120, 130, 140, 150, 160, 170, 180, 190, 200,
    210, 220, 230, 240, 250, 260, 270, 280, 290, 300,
    310
]

MAX_USOS_POR_PERSONAGEM = 8
NUM_ETAPAS_ATIVAS = len(DIFICULDADES)  # 31

# Configurações visuais (Pygame)
TAMANHO_CELULA = 4  # pixels por célula da matriz

CORES = {
    '.': (240, 240, 240),         # Plano: branco
    'R': (139, 137, 137),         # Rochoso: cinza
    'F': (34,  139, 34),          # Floresta: verde
    'V': (34,  139, 34),          # Floresta: verde
    'A': (30,  144, 255),         # Água: azul
    'M': (139, 69,  19),          # Montanhoso: marrom
    'CHECKPOINT':         (255, 80,  80),   # Checkpoint: vermelho
    'CAMINHO':            (255, 215, 0),    # Rastro: dourado
    'AVATAR':             (255, 50,  50),   # Avatar em movimento: vermelho
    'CHECKPOINT_ATINGIDO':(100, 255, 120),  # Avatar ao chegar: verde claro
}

# =====================================================================
# 2. CARREGAMENTO DO MAPA
# =====================================================================

def carregar_mapa(caminho_arquivo: str):
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
    """
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])


def a_star(mapa: list, inicio: tuple, objetivo: tuple):
    """
    Algoritmo A* para menor custo entre dois pontos no mapa.

    Células de checkpoint são tratadas como terreno plano (custo 1) para
    fins de passagem — elas marcam posições, não alteram o custo de terreno.

    Retorna:
      - custo_total (int): custo acumulado do caminho ótimo
      - caminho (list[tuple]): lista de posições de 'inicio' até 'objetivo'
    """
    linhas, colunas = len(mapa), len(mapa[0])
    movimentos = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # sem diagonal

    # Heap: (f = g + h, g, posicao)
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

# =====================================================================
# 4. BUSCA LOCAL: SIMULATED ANNEALING
# =====================================================================

def calcular_tempo_etapas(estado: list, dificuldades: list, personagens: list) -> float:
    """
    Dado um estado (lista de listas de índices de personagens por etapa),
    calcula o tempo total das etapas ativas:
        T = Σ Dificuldade_i / Σ Agilidade_j  (para j no grupo da etapa i)
    """
    tempo_total = 0.0
    for i, grupo in enumerate(estado):
        soma_agilidade = sum(personagens[c][1] for c in grupo)
        if soma_agilidade == 0:
            return float('inf')
        tempo_total += dificuldades[i] / soma_agilidade
    return tempo_total


def inicializar_estado_guloso(num_etapas: int, num_chars: int,
                               personagens: list, dificuldades: list):
    """
    Cria um estado inicial de qualidade para o SA em dois passos:

    Fase 1 — atribui 1 personagem por etapa:
      Processa as etapas da mais difícil para a mais fácil, alocando sempre
      o personagem mais ágil ainda disponível (com slots restantes).

    Fase 2 — distribui os slots restantes por benefício marginal:
      Usa um heap de prioridade para sempre adicionar o par (etapa, personagem)
      que gera a maior redução de tempo, até esgotar todos os slots disponíveis.
    """
    estado = [[] for _ in range(num_etapas)]
    usos = [0] * num_chars

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

    while heap_bm:
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
    Simulated Annealing para minimizar o tempo total das etapas.
    Cada personagem pode participar de no máximo MAX_USOS_POR_PERSONAGEM etapas.

    Vizinhança inclui 4 movimentos:
      1. MOVER  — transfere um personagem de uma etapa para outra
      2. TROCAR — permuta personagens entre duas etapas (sem alterar contadores)
      3. ADICIONAR — insere um personagem em uma etapa (se tiver slot)
      4. REMOVER  — retira um personagem de uma etapa com mais de 1 participante

    A temperatura inicial (500) é proporcional à magnitude dos custos;
    o resfriamento geométrico (×0.95 a cada 300 avaliações) garante uma
    exploração ampla nas fases iniciais e convergência suave ao final.
    """
    num_etapas = len(dificuldades)
    num_chars  = len(personagens)

    T_INICIAL        = 500.0
    T_FINAL          = 0.01
    FATOR_RESFR      = 0.95
    ITER_POR_T       = 300
    NUM_TENTATIVAS   = 5

    melhor_global_tempo = float('inf')
    melhor_global_estado = None

    for tentativa in range(NUM_TENTATIVAS):
        estado, usos = inicializar_estado_guloso(
            num_etapas, num_chars, personagens, dificuldades
        )
        tempo_atual = calcular_tempo_etapas(estado, dificuldades, personagens)

        melhor_local_tempo  = tempo_atual
        melhor_local_estado = [list(e) for e in estado]
        temperatura = T_INICIAL

        while temperatura > T_FINAL:
            for _ in range(ITER_POR_T):
                estado_viz = [list(e) for e in estado]
                usos_viz   = list(usos)
                tipo_mov   = random.random()

                if tipo_mov < 0.35:
                    # MOVER: transfere char de uma etapa para outra
                    c = random.randint(0, num_chars - 1)
                    etapas_com  = [i for i in range(num_etapas) if c in estado_viz[i]]
                    etapas_sem  = [i for i in range(num_etapas) if c not in estado_viz[i]]
                    if not etapas_com or not etapas_sem:
                        continue
                    origem  = random.choice(etapas_com)
                    if len(estado_viz[origem]) <= 1:
                        continue  # não deixa a etapa vazia
                    destino = random.choice(etapas_sem)
                    estado_viz[origem].remove(c)
                    estado_viz[destino].append(c)
                    # usos_viz não muda (char apenas muda de etapa)

                elif tipo_mov < 0.70:
                    # TROCAR: permuta um char entre duas etapas
                    e1, e2 = random.sample(range(num_etapas), 2)
                    op_c1 = [c for c in estado_viz[e1] if c not in estado_viz[e2]]
                    op_c2 = [c for c in estado_viz[e2] if c not in estado_viz[e1]]
                    if not op_c1 or not op_c2:
                        continue
                    c1 = random.choice(op_c1)
                    c2 = random.choice(op_c2)
                    estado_viz[e1].remove(c1); estado_viz[e1].append(c2)
                    estado_viz[e2].remove(c2); estado_viz[e2].append(c1)
                    # usos_viz não muda (troca simétrica)

                elif tipo_mov < 0.85:
                    # ADICIONAR: insere um char em uma etapa (consome 1 slot)
                    c = random.randint(0, num_chars - 1)
                    if usos_viz[c] >= MAX_USOS_POR_PERSONAGEM:
                        continue
                    etapas_sem = [i for i in range(num_etapas) if c not in estado_viz[i]]
                    if not etapas_sem:
                        continue
                    etapa = random.choice(etapas_sem)
                    estado_viz[etapa].append(c)
                    usos_viz[c] += 1

                else:
                    # REMOVER: retira um char de uma etapa com mais de 1 participante
                    candidatas = [i for i in range(num_etapas) if len(estado_viz[i]) > 1]
                    if not candidatas:
                        continue
                    etapa = random.choice(candidatas)
                    c = random.choice(estado_viz[etapa])
                    estado_viz[etapa].remove(c)
                    usos_viz[c] -= 1

                tempo_viz = calcular_tempo_etapas(estado_viz, dificuldades, personagens)
                delta = tempo_viz - tempo_atual

                # Critério de aceitação de Metropolis
                if delta < 0 or random.random() < math.exp(-delta / temperatura):
                    estado     = estado_viz
                    usos       = usos_viz
                    tempo_atual = tempo_viz
                    if tempo_atual < melhor_local_tempo:
                        melhor_local_tempo  = tempo_atual
                        melhor_local_estado = [list(e) for e in estado]
                        if melhor_local_tempo < melhor_global_tempo:
                            melhor_global_tempo  = melhor_local_tempo
                            melhor_global_estado = [list(e) for e in estado]

            temperatura *= FATOR_RESFR

        print(f"  Tentativa {tentativa + 1}/{NUM_TENTATIVAS}: "
              f"{melhor_local_tempo:.6f} min  "
              f"(melhor global: {melhor_global_tempo:.6f} min)")

    return melhor_global_tempo, melhor_global_estado

# =====================================================================
# 5. SAÍDA DE RESULTADOS NO TERMINAL
# =====================================================================

def exibir_resultado_etapas(esquema: list, personagens: list, dificuldades: list):
    """Imprime a tabela de atribuição de personagens por etapa."""
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
                           indices_checkpoints: dict, custo_final: float):
    """
    Loop principal do Pygame.
    Anima o avatar percorrendo a rota_completa passo a passo,
    pausa brevemente ao atingir cada checkpoint, e exibe um HUD com
    o contador de checkpoints e o custo total.
    """
    pygame.init()
    fonte_titulo = pygame.font.SysFont('Arial', 20, bold=True)
    fonte_info   = pygame.font.SysFont('Arial', 16)

    linhas_mapa  = len(mapa)
    colunas_mapa = len(mapa[0])
    largura_tela = colunas_mapa * TAMANHO_CELULA
    altura_tela  = linhas_mapa  * TAMANHO_CELULA

    tela = pygame.display.set_mode((largura_tela, altura_tela))
    pygame.display.set_caption(f"Jornada de Aang — Custo Total: {custo_final:.6f} min")

    # Superfície estática do mapa (só renderizada uma vez)
    sup_mapa = pre_renderizar_mapa(mapa)

    # Superfície do rastro com suporte a transparência (alpha)
    sup_rastro = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
    sup_rastro.fill((0, 0, 0, 0))

    relogio           = pygame.time.Clock()
    rodando           = True
    passo_atual       = 0
    total_passos      = len(rota_completa)
    ckpts_visitados   = set()
    etapas_concluidas = 0

    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

        chegou_em_checkpoint = False

        if passo_atual < total_passos:
            i_pos, j_pos = rota_completa[passo_atual]

            # Pinta a célula atual no rastro persistente
            pygame.draw.rect(
                sup_rastro,
                (*CORES['CAMINHO'], 210),
                pygame.Rect(j_pos * TAMANHO_CELULA, i_pos * TAMANHO_CELULA,
                            TAMANHO_CELULA, TAMANHO_CELULA)
            )

            # Verifica se chegou em algum checkpoint neste passo
            for char, idx in indices_checkpoints.items():
                if passo_atual == idx and char not in ckpts_visitados:
                    ckpts_visitados.add(char)
                    etapas_concluidas += 1
                    chegou_em_checkpoint = True

            passo_atual += 1

        # --- Composição das camadas ---
        tela.blit(sup_mapa,   (0, 0))
        tela.blit(sup_rastro, (0, 0))

        # Avatar na posição atual
        if passo_atual > 0:
            idx_atual = min(passo_atual - 1, total_passos - 1)
            i_av, j_av = rota_completa[idx_atual]
            cx = j_av * TAMANHO_CELULA + TAMANHO_CELULA // 2
            cy = i_av * TAMANHO_CELULA + TAMANHO_CELULA // 2
            cor_av = (CORES['CHECKPOINT_ATINGIDO']
                      if chegou_em_checkpoint else CORES['AVATAR'])
            pygame.draw.circle(tela, cor_av, (cx, cy), TAMANHO_CELULA + 1)

        # --- HUD ---
        txt_etapas = fonte_titulo.render(
            f"Checkpoints: {etapas_concluidas} / 31", True, (255, 255, 255)
        )
        txt_custo = fonte_info.render(
            f"Custo total: {custo_final:.6f} min", True, (210, 210, 210)
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
            pygame.time.delay(300)  # pausa breve ao atingir um checkpoint

        relogio.tick(60)

    pygame.quit()

# =====================================================================
# 7. EXECUÇÃO PRINCIPAL
# =====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("       Jornada de Aang — Agente Inteligente (INF1771)")
    print("=" * 60)

    # ------------------------------------------------------------------
    # Fase 1: Carregar mapa
    # ------------------------------------------------------------------
    print("\n[1/3] Carregando mapa...")
    mapa, checkpoints = carregar_mapa("MAPA_LENDA-AANG.txt")
    print(f"      Dimensões: {len(mapa)} x {len(mapa[0])}  |  "
          f"Checkpoints encontrados: {len(checkpoints)}")

    # ------------------------------------------------------------------
    # Fase 2: A* entre checkpoints consecutivos
    # ------------------------------------------------------------------
    print("\n[2/3] Executando A* entre checkpoints...")
    tempo_viagem_total = 0
    rota_completa      = []
    # Mapeia char do checkpoint → índice exato na rota_completa
    # (usado para detectar chegadas durante a animação)
    indices_checkpoints = {}

    for i in range(len(CHECKPOINTS_ORDEM) - 1):
        origem_char  = CHECKPOINTS_ORDEM[i]
        destino_char = CHECKPOINTS_ORDEM[i + 1]

        custo, rota = a_star(mapa, checkpoints[origem_char], checkpoints[destino_char])
        tempo_viagem_total += custo

        # Concatena as rotas evitando duplicar o ponto de junção
        if i == 0:
            rota_completa.extend(rota)
        else:
            rota_completa.extend(rota[1:])

        # O checkpoint destino está sempre na última posição adicionada
        indices_checkpoints[destino_char] = len(rota_completa) - 1

        print(f"      {origem_char} → {destino_char}: {custo} min")

    print(f"\n      Tempo total de viagem (A*): {tempo_viagem_total} minutos")

    # ------------------------------------------------------------------
    # Fase 3: Simulated Annealing para atribuição de personagens
    # ------------------------------------------------------------------
    print("\n[3/3] Otimizando atribuição de personagens (Simulated Annealing)...")
    tempo_etapas, esquema = resolver_etapas_simulated_annealing(DIFICULDADES, PERSONAGENS)
    exibir_resultado_etapas(esquema, PERSONAGENS, DIFICULDADES)

    custo_final = tempo_viagem_total + tempo_etapas

    print("\n" + "=" * 60)
    print("                   RESULTADO FINAL")
    print("=" * 60)
    print(f"  Tempo de viagem  (A*) :  {tempo_viagem_total:>10} minutos")
    print(f"  Tempo das etapas (SA) :  {tempo_etapas:>16.6f} minutos")
    print(f"  CUSTO FINAL DO AGENTE:   {custo_final:>16.6f} minutos")
    print("=" * 60)
    print("\nAbrindo visualização gráfica... (feche a janela para encerrar)\n")

    # ------------------------------------------------------------------
    # Fase 4: Visualização com Pygame
    # ------------------------------------------------------------------
    executar_visualizacao(mapa, rota_completa, indices_checkpoints, custo_final)
