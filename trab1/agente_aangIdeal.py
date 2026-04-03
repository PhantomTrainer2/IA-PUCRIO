import heapq
import sys
import itertools

# Tratamento de bibliotecas externas
try:
    import pygame
except ImportError:
    print("ERRO: A biblioteca 'pygame' não está instalada.")
    print("Por favor, abra o terminal e digite: pip install pygame")
    sys.exit(1)

try:
    import pulp
except ImportError:
    print("ERRO: A biblioteca 'pulp' não está instalada.")
    print("O Pulp é necessário para a Programação Linear Inteira.")
    print("Por favor, abra o terminal e digite: pip install pulp")
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
    '.': (240, 240, 240),         
    'R': (139, 137, 137),         
    'F': (34,  139, 34),          
    'V': (34,  139, 34),          
    'A': (30,  144, 255),         
    'M': (139, 69,  19),          
    'CHECKPOINT':         (255, 80,  80),   
    'CAMINHO':            (255, 215, 0),    
    'AVATAR':             (255, 50,  50),   
    'CHECKPOINT_ATINGIDO':(100, 255, 120),  
}

# =====================================================================
# 2. CARREGAMENTO DO MAPA E BUSCA A*
# =====================================================================

def carregar_mapa(caminho_arquivo: str):
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

def distancia_manhattan(p1: tuple, p2: tuple) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

def a_star(mapa: list, inicio: tuple, objetivo: tuple):
    linhas, colunas = len(mapa), len(mapa[0])
    movimentos = [(-1, 0), (1, 0), (0, -1), (0, 1)] 
    fronteira = [(distancia_manhattan(inicio, objetivo), 0, inicio)]
    custo_ate = {inicio: 0}
    veio_de = {}

    while fronteira:
        _, g_atual, no_atual = heapq.heappop(fronteira)

        if no_atual == objetivo:
            caminho = []
            no = objetivo
            while no in veio_de:
                caminho.append(no)
                no = veio_de[no]
            caminho.append(inicio)
            return g_atual, caminho[::-1]

        if g_atual > custo_ate.get(no_atual, float('inf')):
            continue

        for dx, dy in movimentos:
            nx, ny = no_atual[0] + dx, no_atual[1] + dy
            if 0 <= nx < linhas and 0 <= ny < colunas:
                terreno = mapa[nx][ny]
                custo_movimento = CUSTOS_TERRENO.get(terreno, 1)
                novo_g = g_atual + custo_movimento

                if novo_g < custo_ate.get((nx, ny), float('inf')):
                    custo_ate[(nx, ny)] = novo_g
                    f = novo_g + distancia_manhattan((nx, ny), objetivo)
                    heapq.heappush(fronteira, (f, novo_g, (nx, ny)))
                    veio_de[(nx, ny)] = no_atual

    return float('inf'), [] 

# =====================================================================
# 3. SOLUÇÃO EXATA: PROGRAMAÇÃO LINEAR INTEIRA (ILP) COM PULP
# =====================================================================

def resolver_etapas_ilp(dificuldades: list, personagens: list):
    """
    Resolve o problema de alocação de personagens usando Programação Inteira.
    Garante matematicamente a solução ótima (Ótimo Global).
    """
    num_etapas = len(dificuldades)
    num_chars = len(personagens)
    max_total_usos = (num_chars * MAX_USOS_POR_PERSONAGEM) - 1 # Pelo menos um sobra

    # 1. Gerar todas as combinações possíveis de grupos de personagens (2^7 - 1 = 127 grupos)
    grupos = []
    for r in range(1, num_chars + 1):
        for combinacao in itertools.combinations(range(num_chars), r):
            soma_agilidade = sum(personagens[c][1] for c in combinacao)
            grupos.append((list(combinacao), soma_agilidade))

    # 2. Criar o modelo do problema (Minimização)
    prob = pulp.LpProblem("Otimizacao_Jornada_Aang_ILP", pulp.LpMinimize)

    # 3. Variáveis de Decisão (Binárias)
    # x[i][j] == 1 significa que a Etapa 'i' será realizada pelo Grupo 'j'
    x = pulp.LpVariable.dicts("x", 
                              ((i, j) for i in range(num_etapas) for j in range(len(grupos))), 
                              cat='Binary')

    # 4. Função Objetivo: Minimizar o tempo total (Dificuldade / Agilidade do Grupo)
    prob += pulp.lpSum( x[i, j] * (dificuldades[i] / grupos[j][1]) 
                        for i in range(num_etapas) 
                        for j in range(len(grupos)) )

    # 5. Restrição 1: Exatamente 1 grupo deve ser escolhido por etapa
    for i in range(num_etapas):
        prob += pulp.lpSum(x[i, j] for j in range(len(grupos))) == 1

    # 6. Restrição 2: Limite de usos por personagem (Máx 8 usos)
    for c in range(num_chars):
        prob += pulp.lpSum(x[i, j] 
                           for i in range(num_etapas) 
                           for j in range(len(grupos)) 
                           if c in grupos[j][0]) <= MAX_USOS_POR_PERSONAGEM

    # 7. Restrição 3: Limite global de usos (Soma total <= 55)
    prob += pulp.lpSum(len(grupos[j][0]) * x[i, j] 
                       for i in range(num_etapas) 
                       for j in range(len(grupos))) <= max_total_usos

    # 8. Resolver com o solver embutido do Pulp (Silencioso)
    print("  Modelando problema e chamando solver ILP (Pulp)...")
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    # Verificar se encontrou solução viável
    if pulp.LpStatus[prob.status] != 'Optimal':
        print(f"  AVISO: Solver retornou status: {pulp.LpStatus[prob.status]}")
        return float('inf'), []

    # 9. Extrair o esquema final baseado nas variáveis ativadas (onde x == 1)
    esquema = [[] for _ in range(num_etapas)]
    for i in range(num_etapas):
        for j in range(len(grupos)):
            if pulp.value(x[i, j]) == 1.0:
                esquema[i] = grupos[j][0]
                break

    tempo_total = pulp.value(prob.objective)
    return tempo_total, esquema

# =====================================================================
# 4. SAÍDA DE RESULTADOS NO TERMINAL E PYGAME
# =====================================================================

def exibir_resultado_etapas(esquema: list, personagens: list, dificuldades: list):
    print(f"\n  {'Etapa':>5} | {'Dif.':>4} | {'Personagens':<36} | {'Agil.':>5} | {'Tempo':>8}")
    print("  " + "-" * 72)
    usos_totais = {p[0]: 0 for p in personagens}
    for i, grupo in enumerate(esquema):
        num_etapa = i + 1  
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

def pre_renderizar_mapa(mapa: list) -> pygame.Surface:
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
                           tempos_por_etapa: list):
    pygame.init()
    fonte_titulo = pygame.font.SysFont('Arial', 20, bold=True)
    fonte_info   = pygame.font.SysFont('Arial', 16, bold=True)

    linhas_mapa  = len(mapa)
    colunas_mapa = len(mapa[0])
    largura_tela = colunas_mapa * TAMANHO_CELULA
    altura_tela  = linhas_mapa  * TAMANHO_CELULA

    tela = pygame.display.set_mode((largura_tela, altura_tela))
    pygame.display.set_caption(f"Jornada de Aang — Custo Total (Ótimo Global): {custo_final:.2f} min")

    sup_mapa = pre_renderizar_mapa(mapa)
    sup_rastro = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
    sup_rastro.fill((0, 0, 0, 0))

    relogio           = pygame.time.Clock()
    rodando           = True
    passo_atual       = 0
    total_passos      = len(rota_completa)
    ckpts_visitados   = set()
    etapas_concluidas = 0
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

            if passo_atual > 0:
                terreno = mapa[i_pos][j_pos]
                custo_passo = CUSTOS_TERRENO.get(terreno, 1)
                custo_acumulado += custo_passo

            for char, idx in indices_checkpoints.items():
                if passo_atual == idx and char not in ckpts_visitados:
                    ckpts_visitados.add(char)
                    
                    if etapas_concluidas < len(tempos_por_etapa):
                        custo_acumulado += tempos_por_etapa[etapas_concluidas]
                    
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
        
        if passo_atual < total_passos:
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
# 5. EXECUÇÃO PRINCIPAL
# =====================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("      Jornada de Aang — Agente Inteligente (INF1771)")
    print("      Solver: Programação Linear Inteira (ILP Ótimo)")
    print("=" * 60)

    print("\n[1/3] Carregando mapa...")
    mapa, checkpoints = carregar_mapa("MAPA_LENDA-AANG.txt")
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

    print(f"\n      Tempo total de viagem (A*): {tempo_viagem_total} minutos")

    print("\n[3/3] Otimizando atribuição de personagens (Programação Inteira - Pulp)...")
    # Chamando a nova função ILP em vez do Simulated Annealing
    tempo_etapas, esquema = resolver_etapas_ilp(DIFICULDADES, PERSONAGENS)
    exibir_resultado_etapas(esquema, PERSONAGENS, DIFICULDADES)

    tempos_por_etapa = []
    for i, grupo in enumerate(esquema):
        D = DIFICULDADES[i]
        A = sum(PERSONAGENS[c][1] for c in grupo)
        tempos_por_etapa.append(D / A)

    custo_final = tempo_viagem_total + tempo_etapas

    print("\n" + "=" * 60)
    print("                   RESULTADO FINAL")
    print("=" * 60)
    print(f"  Tempo de viagem  (A*) :  {tempo_viagem_total:>10} minutos")
    print(f"  Tempo das etapas (ILP):  {tempo_etapas:>16.6f} minutos")
    print(f"  CUSTO FINAL DO AGENTE:   {custo_final:>16.6f} minutos")
    print("=" * 60)
    print("\nAbrindo visualização gráfica... (feche a janela para encerrar)\n")

    executar_visualizacao(mapa, rota_completa, indices_checkpoints, custo_final, tempos_por_etapa)