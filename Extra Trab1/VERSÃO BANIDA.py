import heapq
import itertools
import math
import sys
from functools import lru_cache
from pathlib import Path

try:
    import pygame
except ImportError:
    print("ERRO: a biblioteca 'pygame' nao esta instalada.")
    print("Por favor, abra o terminal e digite: pip install pygame")
    sys.exit(1)

try:
    import pulp
    PULP_DISPONIVEL = True
except ImportError:
    pulp = None
    PULP_DISPONIVEL = False


# Custo de cada tile
CUSTOS_TERRENO = {
    ".": 1,
    "R": 5,
    "F": 10,
    "V": 10,
    "A": 15,
    "M": 200,
}

# Personagem e agilidade
PERSONAGENS = [
    ("Aang", 1.8),
    ("Zuko", 1.6),
    ("Toph", 1.6),
    ("Katara", 1.6),
    ("Sokka", 1.4),
    ("Appa", 0.9),
    ("Momo", 0.7),
]

# Checkpoints de onde as etapas são realizadas no mapa
CHECKPOINTS_ORDEM = [
    "0", "1", "2", "3", "4", "5", "6", "7", "8", "9",
    "B", "C", "D", "E", "G", "H", "I", "J", "K", "L",
    "N", "O", "P", "Q", "S", "T", "U", "V", "W", "X", "Y", "Z",
]

# Dificuldade de cada Etapa
DIFICULDADES = [
     10,  20,  30,  40,  50,  60,  70,  80,  90, 100,
    110, 120, 130, 140, 150, 160, 170, 180, 190, 200,
    210, 220, 230, 240, 250, 260, 270, 280, 290, 300,
    310,
]


MAX_USOS_POR_PERSONAGEM = 8
NUM_ETAPAS_ATIVAS = len(DIFICULDADES)

# Configuração pygame
TAMANHO_CELULA = 4

CORES = {
    ".": (240, 240, 240),
    "R": (139, 137, 137),
    "F": (34, 139, 34),
    "V": (34, 139, 34),
    "A": (30, 144, 255),
    "M": (139, 69, 19),
    "CHECKPOINT": (255, 80, 80),
    "CAMINHO": (255, 215, 0),
    "AVATAR": (255, 50, 50),
    "CHECKPOINT_ATINGIDO": (100, 255, 120),
}

MOVIMENTOS_CARDINAIS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
MAPA_ARQUIVO = Path(__file__).resolve().with_name("MAPA_LENDA-AANG.txt")



# Carregar o mapa
def carregar_mapa(caminho_arquivo: str | Path):
    with open(caminho_arquivo, "r", encoding="utf-8") as arquivo:
        linhas = arquivo.read().splitlines()

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



# Cálculo da menor distância possível.
def distancia_manhattan(p1: tuple[int, int], p2: tuple[int, int]) -> int:
    return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1])

# Busca A*
def a_star(mapa: list, inicio: tuple[int, int], objetivo: tuple[int, int]):
    linhas, colunas = len(mapa), len(mapa[0])
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

        if g_atual > custo_ate.get(no_atual, float("inf")):
            continue

        for dx, dy in MOVIMENTOS_CARDINAIS:
            nx, ny = no_atual[0] + dx, no_atual[1] + dy
            if 0 <= nx < linhas and 0 <= ny < colunas:
                terreno = mapa[nx][ny]
                custo_movimento = CUSTOS_TERRENO.get(terreno, 1)
                novo_g = g_atual + custo_movimento

                if novo_g < custo_ate.get((nx, ny), float("inf")):
                    custo_ate[(nx, ny)] = novo_g
                    f = novo_g + distancia_manhattan((nx, ny), objetivo)
                    heapq.heappush(fronteira, (f, novo_g, (nx, ny)))
                    veio_de[(nx, ny)] = no_atual

    return float("inf"), []

# Uso de Djikstra para comparação em relação a heuristica.
def dijkstra_custo(mapa: list, inicio: tuple[int, int], objetivo: tuple[int, int]) -> float:
    linhas, colunas = len(mapa), len(mapa[0])
    distancias = {inicio: 0}
    fronteira = [(0, inicio)]

    while fronteira:
        g_atual, no_atual = heapq.heappop(fronteira)

        if g_atual > distancias.get(no_atual, float("inf")):
            continue

        if no_atual == objetivo:
            return g_atual

        for dx, dy in MOVIMENTOS_CARDINAIS:
            nx, ny = no_atual[0] + dx, no_atual[1] + dy
            if 0 <= nx < linhas and 0 <= ny < colunas:
                custo_movimento = CUSTOS_TERRENO.get(mapa[nx][ny], 1)
                novo_g = g_atual + custo_movimento
                if novo_g < distancias.get((nx, ny), float("inf")):
                    distancias[(nx, ny)] = novo_g
                    heapq.heappush(fronteira, (novo_g, (nx, ny)))

    return float("inf")

# Impressão de um relatório para verificar se a rota encontrada pelo A* é de fato ótima. 
def verificar_otimalidade_rota(mapa: list, checkpoints: dict):
    relatorio = []
    custo_total_a_star = 0
    custo_total_dijkstra = 0
    rota_completa = []
    indices_checkpoints = {}

    for i in range(len(CHECKPOINTS_ORDEM) - 1):
        origem_char = CHECKPOINTS_ORDEM[i]
        destino_char = CHECKPOINTS_ORDEM[i + 1]

        custo_a_star, rota = a_star(mapa, checkpoints[origem_char], checkpoints[destino_char])
        custo_dijkstra = dijkstra_custo(mapa, checkpoints[origem_char], checkpoints[destino_char])

        custo_total_a_star += custo_a_star
        custo_total_dijkstra += custo_dijkstra

        if i == 0:
            rota_completa.extend(rota)
        else:
            rota_completa.extend(rota[1:])

        indices_checkpoints[destino_char] = len(rota_completa) - 1
        relatorio.append((origem_char, destino_char, custo_a_star, custo_dijkstra, math.isclose(custo_a_star, custo_dijkstra)))

    return {
        "relatorio": relatorio,
        "custo_total_a_star": custo_total_a_star,
        "custo_total_dijkstra": custo_total_dijkstra,
        "rota_completa": rota_completa,
        "indices_checkpoints": indices_checkpoints,
        "rota_otima": all(item[4] for item in relatorio),
    }


# Cálculo das Etapas

def calcular_tempo_etapas(estado: list, dificuldades: list, personagens: list) -> float:
    tempo_total = 0.0
    for i, grupo in enumerate(estado):
        soma_agilidade = sum(personagens[c][1] for c in grupo)
        if soma_agilidade == 0:
            return float("inf")
        tempo_total += dificuldades[i] / soma_agilidade
    return tempo_total


def gerar_grupos_concretos(personagens: list):
    grupos = []
    for r in range(1, len(personagens) + 1):
        for combinacao in itertools.combinations(range(len(personagens)), r):
            soma_agilidade = sum(personagens[c][1] for c in combinacao)
            grupos.append((list(combinacao), soma_agilidade))
    return grupos


def resolver_etapas_ilp_pulp(dificuldades: list, personagens: list):
    grupos = gerar_grupos_concretos(personagens)
    num_etapas = len(dificuldades)
    max_total_usos = (len(personagens) * MAX_USOS_POR_PERSONAGEM)

    problema = pulp.LpProblem("Otimizacao_Jornada_Aang_ILP", pulp.LpMinimize)
    x = pulp.LpVariable.dicts(
        "x",
        ((i, j) for i in range(num_etapas) for j in range(len(grupos))),
        cat="Binary",
    )

    problema += pulp.lpSum(
        x[i, j] * (dificuldades[i] / grupos[j][1])
        for i in range(num_etapas)
        for j in range(len(grupos))
    )

    for i in range(num_etapas):
        problema += pulp.lpSum(x[i, j] for j in range(len(grupos))) == 1

    for c in range(len(personagens)):
        problema += pulp.lpSum(
            x[i, j]
            for i in range(num_etapas)
            for j in range(len(grupos))
            if c in grupos[j][0]
        ) <= MAX_USOS_POR_PERSONAGEM

    problema += pulp.lpSum(
        len(grupos[j][0]) * x[i, j]
        for i in range(num_etapas)
        for j in range(len(grupos))
    ) <= max_total_usos

    problema.solve(pulp.PULP_CBC_CMD(msg=False))

    if pulp.LpStatus[problema.status] != "Optimal":
        raise RuntimeError(f"Solver ILP nao encontrou otimo. Status: {pulp.LpStatus[problema.status]}")

    esquema = [[] for _ in range(num_etapas)]
    for i in range(num_etapas):
        for j in range(len(grupos)):
            if pulp.value(x[i, j]) == 1.0:
                esquema[i] = grupos[j][0]
                break

    return pulp.value(problema.objective), esquema, "ILP (PuLP/CBC)"


def gerar_perfis_tipos():
    perfis = []
    for usa_aang in (0, 1):
        for qtd_trio in range(4):
            for usa_sokka in (0, 1):
                for usa_appa in (0, 1):
                    for usa_momo in (0, 1):
                        total = usa_aang + qtd_trio + usa_sokka + usa_appa + usa_momo
                        if total == 0:
                            continue

                        agilidade = (
                            usa_aang * 1.8 +
                            qtd_trio * 1.6 +
                            usa_sokka * 1.4 +
                            usa_appa * 0.9 +
                            usa_momo * 0.7
                        )
                        perfis.append((
                            usa_aang, qtd_trio, usa_sokka, usa_appa, usa_momo,
                            agilidade, 1.0 / agilidade,
                        ))

    perfis.sort(key=lambda perfil: perfil[5], reverse=True)
    return perfis


def expandir_trio_indices(qtd_trio_por_etapa: list[int]):
    usos_trio = {1: 0, 2: 0, 3: 0}
    alocacao = []

    for qtd in qtd_trio_por_etapa:
        disponiveis = sorted(usos_trio, key=lambda idx: (usos_trio[idx], idx))
        escolhidos = []
        for idx in disponiveis:
            if usos_trio[idx] < MAX_USOS_POR_PERSONAGEM and len(escolhidos) < qtd:
                escolhidos.append(idx)
        if len(escolhidos) != qtd:
            raise RuntimeError("Falha ao reconstruir os personagens equivalentes do trio 1.6.")
        for idx in escolhidos:
            usos_trio[idx] += 1
        alocacao.append(escolhidos)

    return alocacao


def reconstruir_estado_concreto(perfis_escolhidos_desc: list[tuple]):
    qtd_trio_por_etapa = [perfil[1] for perfil in perfis_escolhidos_desc]
    trio_por_etapa = expandir_trio_indices(qtd_trio_por_etapa)

    estado_desc = []
    for perfil, trio_indices in zip(perfis_escolhidos_desc, trio_por_etapa):
        usa_aang, _, usa_sokka, usa_appa, usa_momo, _, _ = perfil
        grupo = []
        if usa_aang:
            grupo.append(0)
        grupo.extend(trio_indices)
        if usa_sokka:
            grupo.append(4)
        if usa_appa:
            grupo.append(5)
        if usa_momo:
            grupo.append(6)
        estado_desc.append(sorted(grupo))

    return list(reversed(estado_desc))


def resolver_etapas_dp_exata(dificuldades: list, personagens: list):
    dificuldades_desc = list(reversed(dificuldades))
    perfis = gerar_perfis_tipos()
    capacidades = (8, 24, 8, 8, 8)
    num_etapas = len(dificuldades_desc)
    limite_total_usos = (len(personagens) * MAX_USOS_POR_PERSONAGEM) - 1

    @lru_cache(maxsize=None)
    def dp(i, uso_aang, uso_trio, uso_sokka, uso_appa, uso_momo):
        usos = (uso_aang, uso_trio, uso_sokka, uso_appa, uso_momo)
        total_usos = sum(usos)
        if total_usos > limite_total_usos:
            return float("inf")

        if i == num_etapas:
            return 0.0

        etapas_restantes = num_etapas - i
        capacidade_restante = sum(cap - uso for cap, uso in zip(capacidades, usos))
        if capacidade_restante < etapas_restantes:
            return float("inf")

        dificuldade = dificuldades_desc[i]
        melhor = float("inf")

        for perfil in perfis:
            delta_aang, delta_trio, delta_sokka, delta_appa, delta_momo, _, inv_agilidade = perfil
            novos_usos = (
                uso_aang + delta_aang,
                uso_trio + delta_trio,
                uso_sokka + delta_sokka,
                uso_appa + delta_appa,
                uso_momo + delta_momo,
            )

            if any(novo > cap for novo, cap in zip(novos_usos, capacidades)):
                continue

            if sum(novos_usos) > limite_total_usos:
                continue

            capacidade_restante_depois = sum(cap - uso for cap, uso in zip(capacidades, novos_usos))
            if capacidade_restante_depois < (etapas_restantes - 1):
                continue

            candidato = dificuldade * inv_agilidade + dp(i + 1, *novos_usos)
            if candidato < melhor:
                melhor = candidato

        return melhor

    melhor_tempo = dp(0, 0, 0, 0, 0, 0)
    estado = (0, 0, 0, 0, 0)
    perfis_escolhidos_desc = []

    for i, dificuldade in enumerate(dificuldades_desc):
        alvo = dp(i, *estado)
        for perfil in perfis:
            delta_aang, delta_trio, delta_sokka, delta_appa, delta_momo, _, inv_agilidade = perfil
            novos_usos = (
                estado[0] + delta_aang,
                estado[1] + delta_trio,
                estado[2] + delta_sokka,
                estado[3] + delta_appa,
                estado[4] + delta_momo,
            )

            if any(novo > cap for novo, cap in zip(novos_usos, capacidades)):
                continue
            if sum(novos_usos) > limite_total_usos:
                continue

            etapas_restantes = num_etapas - i
            capacidade_restante_depois = sum(cap - uso for cap, uso in zip(capacidades, novos_usos))
            if capacidade_restante_depois < (etapas_restantes - 1):
                continue

            candidato = dificuldade * inv_agilidade + dp(i + 1, *novos_usos)
            if math.isclose(candidato, alvo, rel_tol=0.0, abs_tol=1e-9):
                perfis_escolhidos_desc.append(perfil)
                estado = novos_usos
                break

    esquema = reconstruir_estado_concreto(perfis_escolhidos_desc)
    return melhor_tempo, esquema, "DP exata (fallback sem PuLP)"


def resolver_etapas_exatas(dificuldades: list, personagens: list):
    if PULP_DISPONIVEL:
        return resolver_etapas_ilp_pulp(dificuldades, personagens)
    return resolver_etapas_dp_exata(dificuldades, personagens)


# =====================================================================
# 5. SAIDA DE RESULTADOS
# =====================================================================

def exibir_resultado_etapas(esquema: list, personagens: list, dificuldades: list):
    print(f"\n  {'Etapa':>5} | {'Dif.':>4} | {'Personagens':<36} | {'Agil.':>5} | {'Tempo':>8}")
    print("  " + "-" * 72)
    usos_totais = {p[0]: 0 for p in personagens}

    for i, grupo in enumerate(esquema):
        num_etapa = i + 1
        dificuldade = dificuldades[i]
        soma_agilidade = sum(personagens[c][1] for c in grupo)
        tempo = dificuldade / soma_agilidade
        nomes = ", ".join(personagens[c][0] for c in sorted(grupo))
        for c in grupo:
            usos_totais[personagens[c][0]] += 1
        print(f"  {num_etapa:>5} | {dificuldade:>4} | {nomes:<36} | {soma_agilidade:>5.2f} | {tempo:>13.6f}")

    print("\n  Usos por personagem:")
    for nome, cnt in usos_totais.items():
        barra = "#" * cnt + "-" * (MAX_USOS_POR_PERSONAGEM - cnt)
        print(f"    {nome:<8}: [{barra}] {cnt}/{MAX_USOS_POR_PERSONAGEM}")


# =====================================================================
# 6. INTERFACE GRAFICA
# =====================================================================

def pre_renderizar_mapa(mapa: list) -> pygame.Surface:
    linhas = len(mapa)
    colunas = len(mapa[0])
    largura = colunas * TAMANHO_CELULA
    altura = linhas * TAMANHO_CELULA
    superficie = pygame.Surface((largura, altura))

    chars_ckpt = set(CHECKPOINTS_ORDEM)
    for i, linha in enumerate(mapa):
        for j, char in enumerate(linha):
            cor = CORES["CHECKPOINT"] if char in chars_ckpt else CORES.get(char, CORES["."])
            pygame.draw.rect(
                superficie,
                cor,
                pygame.Rect(
                    j * TAMANHO_CELULA,
                    i * TAMANHO_CELULA,
                    TAMANHO_CELULA,
                    TAMANHO_CELULA,
                ),
            )
    return superficie


def executar_visualizacao(
    mapa: list,
    rota_completa: list,
    indices_checkpoints: dict,
    custo_final: float,
    tempos_por_etapa: list,
    rotulo_solver: str,
):
    pygame.init()
    fonte_titulo = pygame.font.SysFont("Arial", 20, bold=True)
    fonte_info = pygame.font.SysFont("Arial", 16, bold=True)

    linhas_mapa = len(mapa)
    colunas_mapa = len(mapa[0])
    largura_tela = colunas_mapa * TAMANHO_CELULA
    altura_tela = linhas_mapa * TAMANHO_CELULA

    tela = pygame.display.set_mode((largura_tela, altura_tela))
    pygame.display.set_caption(f"Jornada de Aang - {rotulo_solver} - Custo Total: {custo_final:.2f} min")

    sup_mapa = pre_renderizar_mapa(mapa)
    sup_rastro = pygame.Surface((largura_tela, altura_tela), pygame.SRCALPHA)
    sup_rastro.fill((0, 0, 0, 0))

    relogio = pygame.time.Clock()
    rodando = True
    passo_atual = 0
    total_passos = len(rota_completa)
    ckpts_visitados = set()
    etapas_concluidas = 0
    custo_acumulado = 0.0

    while rodando:
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                rodando = False

        chegou_em_checkpoint = False

        if passo_atual < total_passos:
            i_pos, j_pos = rota_completa[passo_atual]

            pygame.draw.rect(
                sup_rastro,
                (*CORES["CAMINHO"], 210),
                pygame.Rect(
                    j_pos * TAMANHO_CELULA,
                    i_pos * TAMANHO_CELULA,
                    TAMANHO_CELULA,
                    TAMANHO_CELULA,
                ),
            )

            if passo_atual > 0:
                terreno = mapa[i_pos][j_pos]
                custo_acumulado += CUSTOS_TERRENO.get(terreno, 1)

            for char, idx in indices_checkpoints.items():
                if passo_atual == idx and char not in ckpts_visitados:
                    ckpts_visitados.add(char)
                    if etapas_concluidas < len(tempos_por_etapa):
                        custo_acumulado += tempos_por_etapa[etapas_concluidas]
                    etapas_concluidas += 1
                    chegou_em_checkpoint = True

            passo_atual += 1

        tela.blit(sup_mapa, (0, 0))
        tela.blit(sup_rastro, (0, 0))

        if passo_atual > 0:
            idx_atual = min(passo_atual - 1, total_passos - 1)
            i_av, j_av = rota_completa[idx_atual]
            cx = j_av * TAMANHO_CELULA + TAMANHO_CELULA // 2
            cy = i_av * TAMANHO_CELULA + TAMANHO_CELULA // 2
            cor_avatar = CORES["CHECKPOINT_ATINGIDO"] if chegou_em_checkpoint else CORES["AVATAR"]
            pygame.draw.circle(tela, cor_avatar, (cx, cy), TAMANHO_CELULA + 1)

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
        hud = pygame.Surface((hud_w, hud_h))
        hud.fill((0, 0, 0))
        hud.set_alpha(180)

        tela.blit(hud, (10, 10))
        tela.blit(txt_etapas, (22, 15))
        tela.blit(txt_custo, (22, 15 + txt_etapas.get_height() + 5))

        pygame.display.flip()

        if chegou_em_checkpoint:
            pygame.time.delay(300)

        relogio.tick(60)

    pygame.quit()


# =====================================================================
# 7. EXECUCAO PRINCIPAL
# =====================================================================

if __name__ == "__main__":
    print("=" * 68)
    print("      Jornada de Aang - Agente Inteligente (INF1771)")
    print("      Solver exato para as etapas + validacao da rota")
    print("=" * 68)

    print("\n[1/4] Carregando mapa...")
    mapa, checkpoints = carregar_mapa(MAPA_ARQUIVO)
    print(
        f"      Dimensoes: {len(mapa)} x {len(mapa[0])}  |  "
        f"Checkpoints encontrados: {len(checkpoints)}"
    )

    print("\n[2/4] Validando rota A* entre checkpoints...")
    validacao = verificar_otimalidade_rota(mapa, checkpoints)
    for origem, destino, custo_a_star, custo_dijkstra, ok in validacao["relatorio"]:
        status = "OK" if ok else "DIVERGIU"
        print(f"      {origem} -> {destino}: A*={custo_a_star} | Dijkstra={custo_dijkstra} | {status}")

    if validacao["rota_otima"]:
        print("\n      Confirmacao: cada trecho encontrado pelo A* tem custo minimo.")
        print("      Como a ordem dos checkpoints e fixa, a soma desses trechos tambem e minima.")
    else:
        print("\n      AVISO: pelo menos um trecho do A* divergiu do custo minimo.")

    tempo_viagem_total = validacao["custo_total_a_star"]
    rota_completa = validacao["rota_completa"]
    indices_checkpoints = validacao["indices_checkpoints"]
    print(f"\n      Tempo total de viagem validado: {tempo_viagem_total} minutos")

    print("\n[3/4] Otimizando atribuicao de personagens com solver exato...")
    tempo_etapas, esquema, solver_usado = resolver_etapas_exatas(DIFICULDADES, PERSONAGENS)
    print(f"      Solver usado: {solver_usado}")
    exibir_resultado_etapas(esquema, PERSONAGENS, DIFICULDADES)

    tempos_por_etapa = []
    for i, grupo in enumerate(esquema):
        dificuldade = DIFICULDADES[i]
        soma_agilidade = sum(PERSONAGENS[c][1] for c in grupo)
        tempos_por_etapa.append(dificuldade / soma_agilidade)

    custo_final = tempo_viagem_total + tempo_etapas

    print("\n[4/4] Resultado final")
    print("=" * 68)
    print(f"  Tempo de viagem  (A*)           : {tempo_viagem_total:>12.6f} minutos")
    print(f"  Tempo das etapas ({solver_usado}): {tempo_etapas:>12.6f} minutos")
    print(f"  CUSTO FINAL DO AGENTE           : {custo_final:>12.6f} minutos")
    print("=" * 68)
    print("\nAbrindo visualizacao grafica... (feche a janela para encerrar)\n")

    executar_visualizacao(
        mapa,
        rota_completa,
        indices_checkpoints,
        custo_final,
        tempos_por_etapa,
        solver_usado,
    )
