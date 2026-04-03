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
# 4. BUSCA LOCAL: ALGORITMOS GENÉTICOS (AG)
# =====================================================================

def calcular_fitness_com_penalidade(estado: list, dificuldades: list, personagens: list) -> float:
    """
    Avalia a qualidade de um indivíduo (cromossomo). 
    Retorna o tempo calculado. Aplica penalidades severas se violar regras.
    """
    tempo = 0.0
    usos = [0] * len(personagens)
    
    for i, grupo in enumerate(estado):
        if not grupo: return float('inf') # Etapa não pode estar vazia
        soma_agilidade = sum(personagens[c][1] for c in grupo)
        if soma_agilidade == 0: return float('inf')
        tempo += dificuldades[i] / soma_agilidade
        for c in grupo:
            usos[c] += 1

    penalidade = 0
    # Regra 1: Máximo de 8 usos por personagem
    for u in usos:
        if u > MAX_USOS_POR_PERSONAGEM:
            penalidade += (u - MAX_USOS_POR_PERSONAGEM) * 500 # Penalidade muito alta
            
    # Regra 2: Alguém precisa sobreviver no final
    limite_global = (len(personagens) * MAX_USOS_POR_PERSONAGEM) - 1
    if sum(usos) > limite_global:
        penalidade += 1000
        
    return tempo + penalidade

def inicializar_estado_guloso(num_etapas, num_chars, personagens, dificuldades):
    """Cria um indivíduo semente (válido) de altíssima qualidade"""
    estado = [[] for _ in range(num_etapas)]
    usos = [0] * num_chars
    max_total_usos = (num_chars * MAX_USOS_POR_PERSONAGEM) - 1

    ordem_dificuldade = sorted(range(num_etapas), key=lambda i: -dificuldades[i])
    for i in ordem_dificuldade:
        disponiveis = sorted([c for c in range(num_chars) if usos[c] < MAX_USOS_POR_PERSONAGEM], key=lambda c: -personagens[c][1])
        if disponiveis:
            c_melhor = disponiveis[0]
            estado[i].append(c_melhor)
            usos[c_melhor] += 1

    def beneficio_marginal(i, c):
        D = dificuldades[i]
        A = sum(personagens[x][1] for x in estado[i])
        if A == 0: return float('inf')
        return D / A - D / (A + personagens[c][1])

    heap_bm = []
    for i in range(num_etapas):
        for c in range(num_chars):
            if c not in estado[i] and usos[c] < MAX_USOS_POR_PERSONAGEM:
                heapq.heappush(heap_bm, (-beneficio_marginal(i, c), i, c))

    while heap_bm and sum(usos) < max_total_usos:
        neg_b, i, c = heapq.heappop(heap_bm)
        if c in estado[i] or usos[c] >= MAX_USOS_POR_PERSONAGEM: continue
        estado[i].append(c)
        usos[c] += 1
        for c2 in range(num_chars):
            if c2 not in estado[i] and usos[c2] < MAX_USOS_POR_PERSONAGEM:
                heapq.heappush(heap_bm, (-beneficio_marginal(i, c2), i, c2))
    return estado

def aplicar_mutacao_ag(estado, num_chars, num_etapas):
    """Mutação in-place para alterar os genes do indivíduo"""
    tipo = random.random()
    if tipo < 0.25: # ADICIONAR
        etapa = random.randint(0, num_etapas - 1)
        c = random.randint(0, num_chars - 1)
        if c not in estado[etapa]: estado[etapa].append(c)
    elif tipo < 0.50: # REMOVER
        etapa = random.randint(0, num_etapas - 1)
        if len(estado[etapa]) > 1:
            c = random.choice(estado[etapa])
            estado[etapa].remove(c)
    elif tipo < 0.75: # TROCAR (SWAP)
        e1, e2 = random.sample(range(num_etapas), 2)
        if estado[e1] and estado[e2]:
            c1, c2 = random.choice(estado[e1]), random.choice(estado[e2])
            if c1 not in estado[e2] and c2 not in estado[e1]:
                estado[e1].remove(c1); estado[e1].append(c2)
                estado[e2].remove(c2); estado[e2].append(c1)
    else: # MOVER
        e1, e2 = random.sample(range(num_etapas), 2)
        if len(estado[e1]) > 1:
            c = random.choice(estado[e1])
            if c not in estado[e2]:
                estado[e1].remove(c)
                estado[e2].append(c)

def crossover(pai1, pai2):
    """Uniform Crossover: Sorteia etapa a etapa de quem o filho herda a atribuição"""
    filho = []
    for i in range(len(pai1)):
        if random.random() < 0.5:
            filho.append(list(pai1[i]))
        else:
            filho.append(list(pai2[i]))
    return filho

def eh_totalmente_valido(estado, num_chars):
    """Verifica se não há nenhuma violação de regra para oficializarmos o recorde"""
    usos = [0] * num_chars
    for g in estado:
        if not g: return False
        for c in g: usos[c] += 1
    if any(u > MAX_USOS_POR_PERSONAGEM for u in usos): return False
    if sum(usos) > (num_chars * MAX_USOS_POR_PERSONAGEM) - 1: return False
    return True

def resolver_etapas_algoritmo_genetico(dificuldades: list, personagens: list):
    """
    Controlador Principal do Algoritmo Genético
    """
    num_etapas = len(dificuldades)
    num_chars  = len(personagens)

    # Hiperparâmetros do AG
    TAM_POPULACAO = 100
    GERACOES = 200
    TAXA_MUTACAO = 0.40
    ELITISMO = int(TAM_POPULACAO * 0.05) # Mantém os 5% melhores intactos

    melhor_global_tempo = float('inf')
    melhor_global_estado = None

    # 1. Inicializar População (Semeada com base no estado Guloso)
    populacao = []
    guloso = inicializar_estado_guloso(num_etapas, num_chars, personagens, dificuldades)
    populacao.append(guloso)
    
    for _ in range(TAM_POPULACAO - 1):
        novo = [list(e) for e in guloso]
        for _ in range(random.randint(2, 10)): # Causa pequenas perturbações genéticas
            aplicar_mutacao_ag(novo, num_chars, num_etapas)
        populacao.append(novo)

    # 2. Ciclo de Evolução
    for geracao in range(GERACOES):
        # Avalia a aptidão (fitness) de toda a população
        pop_com_fitness = []
        for ind in populacao:
            fit = calcular_fitness_com_penalidade(ind, dificuldades, personagens)
            pop_com_fitness.append((fit, ind))
            
        # Ordena do melhor (menor tempo) para o pior
        pop_com_fitness.sort(key=lambda x: x[0])

        # Verifica e salva o melhor global SE ele for estritamente válido
        melhor_da_geracao_fit, melhor_da_geracao_ind = pop_com_fitness[0]
        if melhor_da_geracao_fit < melhor_global_tempo and eh_totalmente_valido(melhor_da_geracao_ind, num_chars):
            melhor_global_tempo = melhor_da_geracao_fit
            melhor_global_estado = [list(e) for e in melhor_da_geracao_ind]

        # Inicia a nova geração garantindo a sobrevivência dos melhores (Elitismo)
        nova_populacao = [list(ind) for fit, ind in pop_com_fitness[:ELITISMO]]

        # Reprodução (Seleção por Torneio + Crossover + Mutação)
        while len(nova_populacao) < TAM_POPULACAO:
            # Torneio: Escolhe 3 aleatórios e pega o melhor deles para ser Pai/Mãe
            pai1 = min(random.sample(pop_com_fitness, 3), key=lambda x: x[0])[1]
            pai2 = min(random.sample(pop_com_fitness, 3), key=lambda x: x[0])[1]
            
            # Cruzamento
            filho = crossover(pai1, pai2)
            
            # Mutação
            if random.random() < TAXA_MUTACAO:
                aplicar_mutacao_ag(filho, num_chars, num_etapas)
                
            nova_populacao.append(filho)

        populacao = nova_populacao

        if (geracao + 1) % 40 == 0 or geracao == 0:
            print(f"  AG Geração {geracao + 1:>3}/{GERACOES}: Melhor da População = {melhor_da_geracao_fit:.6f} min")

    return melhor_global_tempo, melhor_global_estado

# =====================================================================
# 5. SAÍDA DE RESULTADOS NO TERMINAL
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

# =====================================================================
# 6. INTERFACE GRÁFICA (PYGAME)
# =====================================================================

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
    pygame.display.set_caption(f"Jornada de Aang — Custo Total (AG): {custo_final:.2f} min")

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

        txt_etapas = fonte_titulo.render(f"Checkpoints: {etapas_concluidas} / 31", True, (255, 255, 255))
        
        if passo_atual < total_passos:
            txt_custo = fonte_info.render(f"Custo Acumulado: {custo_acumulado:.2f} min", True, (255, 255, 255))
        else:
            txt_custo = fonte_info.render(f"CUSTO FINAL: {custo_final:.2f} min", True, (100, 255, 120))

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
    print("      Solver: Algoritmos Genéticos (AG)")
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

        if i == 0: rota_completa.extend(rota)
        else: rota_completa.extend(rota[1:])

        indices_checkpoints[destino_char] = len(rota_completa) - 1

    print(f"\n      Tempo total de viagem (A*): {tempo_viagem_total} minutos")

    print("\n[3/3] Otimizando atribuição de personagens (Algoritmos Genéticos)...")
    tempo_etapas, esquema = resolver_etapas_algoritmo_genetico(DIFICULDADES, PERSONAGENS)
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
    print(f"  Tempo das etapas (AG) :  {tempo_etapas:>16.6f} minutos")
    print(f"  CUSTO FINAL DO AGENTE:   {custo_final:>16.6f} minutos")
    print("=" * 60)
    print("\nAbrindo visualização gráfica... (feche a janela para encerrar)\n")

    executar_visualizacao(mapa, rota_completa, indices_checkpoints, custo_final, tempos_por_etapa)