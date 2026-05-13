################################################
import pygame
import contextlib
import os
import sys, time, random

import pathlib

@contextlib.contextmanager
def silence_native_stderr():
    try:
        stderr_fd = sys.stderr.fileno()
        saved_stderr = os.dup(stderr_fd)
        devnull = os.open(os.devnull, os.O_WRONLY)
    except OSError:
        yield
        return

    try:
        os.dup2(devnull, stderr_fd)
        yield
    finally:
        os.dup2(saved_stderr, stderr_fd)
        os.close(saved_stderr)
        os.close(devnull)

with silence_native_stderr():
    from pyswip import Prolog

BASE_DIR = pathlib.Path(__file__).resolve().parent
os.chdir(BASE_DIR)
current_path = str(BASE_DIR)

elapsed_time = 0
auto_play_tempo = 0.5
auto_play = True
# Controls only the rendered map. Agent decisions continue using Prolog memory.
debug = False
LOW_ENERGY_LIMIT = 20
COMMON_ENEMY_MAX_DAMAGE = 50

scale = 60
size_x = 12
size_y = 12
width = size_x * scale
height = size_y * scale
footer_height = 60

player_pos = (1,1,'norte')
energia = 0
pontuacao = 0
game_over_reason = ""
ultimo_evento = ""

# Fila para armazenar as ações geradas pelo Algoritmo A*
actions_queue = []

mapa=[['' for _ in range(size_x)] for _ in range(size_y)]
visitados = []
certezas = []

pl_file = str(BASE_DIR / 'main.pl').replace('\\','/')
prolog = Prolog()
prolog.consult(pl_file)

def prolog_atom(value):
    return "'" + str(value).replace("\\", "/").replace("'", "''") + "'"

def run_prolog_goal(goal, description):
    try:
        result = list(prolog.query(goal))
    except Exception as exc:
        raise RuntimeError(f"Falha ao {description}: {exc}") from exc
    if not result:
        raise RuntimeError(f"Falha ao {description}.")
    return result

def wants_random_map(arg):
    return arg.lower() in ("aleatorio", "aleatoria", "random", "gerar")

def resolve_map_path(arg):
    aliases = {
        "facil": "mapa_facil.pl",
        "fácil": "mapa_facil.pl",
        "medio": "mapa_medio.pl",
        "médio": "mapa_medio.pl",
        "dificil": "mapa_dificil.pl",
        "difícil": "mapa_dificil.pl",
    }
    map_name = aliases.get(arg.lower(), arg)
    map_path = pathlib.Path(map_name)
    if not map_path.is_absolute():
        map_path = BASE_DIR / map_path
    return map_path.resolve()

def load_initial_map():
    if len(sys.argv) <= 1 or wants_random_map(sys.argv[1]):
        run_prolog_goal("gerar_mapa_aleatorio", "gerar mapa aleatorio")
        return
    map_path = resolve_map_path(sys.argv[1])
    run_prolog_goal(f"carregar_mapa_arquivo({prolog_atom(map_path)})", f"carregar mapa {map_path}")

load_initial_map()

last_action = ""

# --- ALGORITMO A* INTEGRADO ---
class Node:
    def __init__(self, x, y, parent=None):
        self.x = x
        self.y = y
        self.parent = parent
        self.g = 0
        self.h = 0
        self.f = 0
    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

def get_prolog_list(query_str, vars):
    try:
        q = list(prolog.query(query_str))
        return [tuple(res[v] for v in vars) for res in q]
    except Exception as e:
        return []

def get_prolog_value(query_str, var, default=None):
    try:
        q = list(prolog.query(query_str))
        if len(q) == 0:
            return default
        return q[0].get(var, default)
    except Exception:
        return default

def prolog_true(query_str):
    try:
        return len(list(prolog.query(query_str))) > 0
    except Exception:
        return False

def astar(start, target, traversable):
    open_list = []
    closed_list = set()
    
    start_node = Node(start[0], start[1])
    target_node = Node(target[0], target[1])
    open_list.append(start_node)
    
    while len(open_list) > 0:
        open_list.sort(key=lambda n: n.f)
        current_node = open_list.pop(0)
        closed_list.add((current_node.x, current_node.y))
        
        if current_node == target_node:
            path = []
            curr = current_node
            while curr is not None:
                path.append((curr.x, curr.y))
                curr = curr.parent
            return path[::-1] 
            
        children = []
        for new_position in [(0, -1), (0, 1), (-1, 0), (1, 0)]:
            node_position = (current_node.x + new_position[0], current_node.y + new_position[1])
            
            if node_position not in traversable and node_position != target:
                continue
            if node_position in closed_list:
                continue
                
            new_node = Node(node_position[0], node_position[1], current_node)
            children.append(new_node)
            
        for child in children:
            child.g = current_node.g + 1
            child.h = abs(child.x - target_node.x) + abs(child.y - target_node.y)
            child.f = child.g + child.h
            
            if any(open_node for open_node in open_list if child == open_node and child.g > open_node.g):
                continue
            open_list.append(child)
    return None

def path_to_actions(path, current_dir):
    actions = []
    def get_needed_dir(dx, dy):
        if dx == 1: return 'leste'
        if dx == -1: return 'oeste'
        if dy == 1: return 'norte'
        if dy == -1: return 'sul'
        
    def get_turns(curr, target):
        if curr == target: return []
        right_turns = {'norte': 'leste', 'leste': 'sul', 'sul': 'oeste', 'oeste': 'norte'}
        left_turns = {'norte': 'oeste', 'oeste': 'sul', 'sul': 'leste', 'leste': 'norte'}
        if right_turns[curr] == target: return ['virar_direita']
        if left_turns[curr] == target: return ['virar_esquerda']
        return ['virar_direita', 'virar_direita']
        
    c_dir = current_dir
    for i in range(1, len(path)):
        dx = path[i][0] - path[i-1][0]
        dy = path[i][1] - path[i-1][1]
        n_dir = get_needed_dir(dx, dy)
        
        turns = get_turns(c_dir, n_dir)
        actions.extend(turns)
        actions.append('andar')
        c_dir = n_dir
        
    return actions

def memory_snapshot():
    memory = {}
    for res in prolog.query("memory(X,Y,Obs)"):
        obs = set(str(item) for item in res["Obs"])
        memory[(res["X"], res["Y"])] = obs
    return memory

def frontier_from_visited(visited):
    frontier = set()
    for vx, vy in visited:
        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            nx, ny = vx + dx, vy + dy
            if 1 <= nx <= size_x and 1 <= ny <= size_y:
                if (nx, ny) not in visited:
                    frontier.add((nx, ny))
    return frontier

def frontier_risk(cell, memory):
    if cell not in memory:
        return 300

    obs = memory[cell]
    if len(obs) == 0:
        return 0

    risk = 0
    if 'brisa' in obs:
        risk += 1000
    if 'flash' in obs:
        risk += 500
    if 'passos' in obs:
        if energia > COMMON_ENEMY_MAX_DAMAGE:
            risk += 10
        else:
            risk += 700
    return risk

def choose_best_path(start, candidates, traversable, candidate_scores):
    best_path = None
    best_score = None
    for cand in candidates:
        path = astar(start, cand, traversable)
        if path:
            score = (candidate_scores.get(cand, 0), len(path))
            if best_path is None or score < best_score:
                best_path = path
                best_score = score
    return best_path, best_score

def plan_astar():
    global actions_queue
    curr_x, curr_y = player_pos[0], player_pos[1]
    curr_dir = player_pos[2]

    gold_left = get_prolog_value("ouro_restante(N)", "N", 0)
    should_return = gold_left == 0
    visited_raw = get_prolog_list("visitado(X,Y)", ['X', 'Y'])
    visited = set(visited_raw) if visited_raw else set()
    visited.add((curr_x, curr_y))
    traversable = set(visited)
    candidate_scores = {}
    memory = memory_snapshot()
    frontier = frontier_from_visited(visited)

    if should_return:
        seguras_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_segura(X, Y)", ['X', 'Y'])
        seguras = set(seguras_raw) if seguras_raw else set()
        traversable.update(seguras)
        candidates = {(1, 1)}
        candidate_scores = {(1, 1): 0}
        if (curr_x, curr_y) == (1, 1):
            actions_queue = ['sair']
            return
        print("A* voltando para a saida.")
    else:
        powerup_raw = get_prolog_list("alvo_powerup(X, Y)", ['X', 'Y'])
        powerups = set(powerup_raw) if powerup_raw else set()

        seguras_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_segura(X, Y)", ['X', 'Y'])
        seguras = set(seguras_raw) if seguras_raw else set()

        inimigo_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_inimigo_arriscavel(X, Y)", ['X', 'Y'])
        inimigo_arriscavel = set(inimigo_raw) if inimigo_raw else set()

        morcego_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_morcego_arriscado(X, Y)", ['X', 'Y'])
        morcego_arriscado = set(morcego_raw) if morcego_raw else set()

        safe_frontier = frontier.intersection(seguras)
        enemy_frontier = frontier.intersection(inimigo_arriscavel)
        bat_frontier = frontier.intersection(morcego_arriscado)

        if powerups:
            candidates = powerups
            candidate_scores = {cell: 0 for cell in candidates}
            print("A* buscando powerup conhecido para recuperar energia.")
        elif safe_frontier:
            candidates = safe_frontier
            candidate_scores = {cell: 0 for cell in candidates}
            print("A* buscando rota para uma fronteira segura.")
        elif enemy_frontier:
            candidates = enemy_frontier
            candidate_scores = {
                cell: frontier_risk(cell, memory)
                for cell in candidates
            }
            print("A* aceitando risco contra inimigo antes de morcego.")
        elif bat_frontier:
            candidates = bat_frontier
            candidate_scores = {
                cell: frontier_risk(cell, memory)
                for cell in candidates
            }
            if energia <= LOW_ENERGY_LIMIT:
                print("A* sem energia para inimigo comum: ultimo recurso no morcego.")
            else:
                print("A* sem rota segura ou inimigo sobrevivivel: ultimo recurso no morcego.")
        else:
            candidate_scores = {
                cell: frontier_risk(cell, memory)
                for cell in frontier
            }
            candidates = set(candidate_scores)
            if candidates:
                print("Sem fronteira segura: A* escolhendo a menor suspeita.")
            else:
                candidates = set()
                print("Sem fronteira viavel: aguardando nova informacao.")

    best_path, best_score = choose_best_path((curr_x, curr_y), candidates, traversable, candidate_scores)

    if should_return and best_path is None:
        seguras_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_segura(X, Y)", ['X', 'Y'])
        seguras = set(seguras_raw) if seguras_raw else set()
        safe_frontier = frontier.intersection(seguras)
        inimigo_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_inimigo_arriscavel(X, Y)", ['X', 'Y'])
        enemy_frontier = frontier.intersection(set(inimigo_raw) if inimigo_raw else set())
        morcego_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_morcego_arriscado(X, Y)", ['X', 'Y'])
        bat_frontier = frontier.intersection(set(morcego_raw) if morcego_raw else set())

        if safe_frontier:
            candidates = safe_frontier
            candidate_scores = {cell: 0 for cell in candidates}
        elif enemy_frontier:
            candidates = enemy_frontier
            candidate_scores = {cell: frontier_risk(cell, memory) for cell in candidates}
        elif bat_frontier:
            candidates = bat_frontier
            candidate_scores = {cell: frontier_risk(cell, memory) for cell in candidates}
        else:
            candidates = frontier
            candidate_scores = {cell: frontier_risk(cell, memory) for cell in candidates}
        best_path, best_score = choose_best_path((curr_x, curr_y), candidates, set(visited), candidate_scores)
        if best_path:
            print("A* sem rota segura para a saida: abrindo caminho pelo menor risco.")

    if best_path and len(best_path) > 1:
        actions_queue = path_to_actions(best_path, curr_dir)
    elif gold_left == 0 and best_path and best_path[-1] == (1, 1):
        actions_queue = ['sair']
    else:
        actions_queue = ['virar_direita']

# --- FIM ALGORITMO A* ---

def decisao():
    if game_over_reason != "":
        return ""
    acao = ""    
    acoes = list(prolog.query("executa_acao(X)"))
    if len(acoes) > 0:
        acao_raw = acoes[0]['X']
        if isinstance(acao_raw, bytes):
            acao = acao_raw.decode('utf-8')
        else:
            acao = str(acao_raw).strip()
    if acao == "nenhuma":
        return ""
    return acao

def exec_prolog(a):
    global last_action
    if a != "":
        list(prolog.query("retractall(ultimo_evento(_))"))
        list(prolog.query(a))
    last_action = a

def pos_event_requires_replan():
    return ultimo_evento in ("flash", "impacto") or game_over_reason != ""

def execute_action(a):
    global actions_queue
    exec_prolog(a)
    update_prolog()
    if pos_event_requires_replan():
        actions_queue.clear()

def update_prolog():
    global player_pos, mapa, energia, pontuacao, visitados, debug, game_over_reason, ultimo_evento
    run_prolog_goal("atualiza_obs, verifica_player", "atualizar estado do agente")

    visitados.clear()
    for res in prolog.query("visitado(X,Y)"):
        visitados.append((res["X"], res["Y"]))

    certezas.clear()
    for res in prolog.query("certeza(X,Y)"):
        certezas.append((res["X"], res["Y"]))

    for j in range(size_y):
        for i in range(size_x):
            mapa[j][i] = ''

    if debug:
        for res in prolog.query("tile(X,Y,Z)"):
            mapa[res["Y"] - 1][res["X"] - 1] = str(res["Z"])
    else:
        for res in prolog.query("memory(X,Y,Obs)"):
            x, y = res["X"], res["Y"]
            for s in res["Obs"]:
                if str(s) == 'brisa': mapa[y-1][x-1] += 'P'
                elif str(s) == 'flash': mapa[y-1][x-1] += 'T'
                elif str(s) == 'passos': mapa[y-1][x-1] += 'I'
                elif str(s) == 'reflexo': mapa[y-1][x-1] += 'U'
                elif str(s) == 'brilho': mapa[y-1][x-1] += 'O'

    posicoes = run_prolog_goal("posicao(X,Y,D)", "ler posicao do agente")
    pos = posicoes[0]
    player_pos = (pos["X"], pos["Y"], str(pos["D"]))

    energia = run_prolog_goal("energia(E)", "ler energia")[0]["E"]
    pontuacao = run_prolog_goal("pontuacao(P)", "ler pontuacao")[0]["P"]

    status = list(prolog.query("jogo_finalizado(R)"))
    if len(status) > 0:
        reason = status[0]['R']
        if isinstance(reason, bytes):
            game_over_reason = reason.decode('utf-8')
        else:
            game_over_reason = str(reason)
    else:
        game_over_reason = ""

    eventos = list(prolog.query("ultimo_evento(E)"))
    if len(eventos) > 0:
        evento = eventos[0]['E']
        if isinstance(evento, bytes):
            ultimo_evento = evento.decode('utf-8')
        else:
            ultimo_evento = str(evento)
    else:
        ultimo_evento = ""

def load_image(path):
    with silence_native_stderr():
        return pygame.image.load(path)

def make_enemy_unknown_image(left_img, right_img):
    tile_w, tile_h = left_img.get_size()
    half_w = tile_w // 2
    img = pygame.Surface((tile_w, tile_h), pygame.SRCALPHA)
    left = pygame.transform.smoothscale(left_img, (half_w, tile_h))
    right = pygame.transform.smoothscale(right_img, (tile_w - half_w, tile_h))
    img.blit(left, (0, 0))
    img.blit(right, (half_w, 0))
    return img

def load():
    global sys_font, clock, img_wall, img_grass, img_start, img_finish, img_path
    global img_gold,img_health, img_pit, img_bat, img_enemy1, img_enemy2, img_enemy_unknown, img_floor
    global bw_img_gold,bw_img_health, bw_img_pit, bw_img_bat, bw_img_enemy1, bw_img_enemy2, bw_img_enemy_unknown, bw_img_floor
    global img_player_up, img_player_down, img_player_left, img_player_right, img_tomb

    sys_font = pygame.font.Font(pygame.font.get_default_font(), 20)
    clock = pygame.time.Clock() 

    img_wall = load_image('wall.jpg')
    img_wall_size = (width/size_x, height/size_y)
    img_wall = pygame.transform.scale(img_wall, img_wall_size)

    img_player_up = load_image('player_up.png')
    img_player_up_size = (width/size_x, height/size_y)
    img_player_up = pygame.transform.scale(img_player_up, img_player_up_size)

    img_player_down = load_image('player_down.png')
    img_player_down_size = (width/size_x, height/size_y)
    img_player_down = pygame.transform.scale(img_player_down, img_player_down_size)

    img_player_left = load_image('player_left.png')
    img_player_left_size = (width/size_x, height/size_y)
    img_player_left = pygame.transform.scale(img_player_left, img_player_left_size)

    img_player_right = load_image('player_right.png')
    img_player_right_size = (width/size_x, height/size_y)
    img_player_right = pygame.transform.scale(img_player_right, img_player_right_size)

    img_tomb = load_image('tombstone.png')
    img_tomb_size = (width/size_x, height/size_y)
    img_tomb = pygame.transform.scale(img_tomb, img_tomb_size)

    img_grass = load_image('grass.jpg')
    img_grass_size = (width/size_x, height/size_y)
    img_grass = pygame.transform.scale(img_grass, img_grass_size)

    img_floor = load_image('floor.png')
    img_floor_size = (width/size_x, height/size_y)
    img_floor = pygame.transform.scale(img_floor, img_floor_size)

    img_gold = load_image('gold.png')
    img_gold_size = (width/size_x, height/size_y)
    img_gold = pygame.transform.scale(img_gold, img_gold_size)

    img_pit = load_image('pit.png')
    img_pit_size = (width/size_x, height/size_y)
    img_pit = pygame.transform.scale(img_pit, img_pit_size)

    img_enemy1 = load_image('enemy1.png')
    img_enemy1_size = (width/size_x, height/size_y)
    img_enemy1 = pygame.transform.scale(img_enemy1, img_enemy1_size)

    img_enemy2 = load_image('enemy2.png')
    img_enemy2_size = (width/size_x, height/size_y)
    img_enemy2 = pygame.transform.scale(img_enemy2, img_enemy2_size)

    img_enemy_unknown = make_enemy_unknown_image(img_enemy1, img_enemy2)

    img_bat = load_image('bat.png')
    img_bat_size = (width/size_x, height/size_y)
    img_bat = pygame.transform.scale(img_bat, img_bat_size)

    img_health = load_image('health.png')
    img_health_size = (width/size_x, height/size_y)
    img_health = pygame.transform.scale(img_health, img_health_size)    
    
    bw_img_floor = load_image('bw_floor.png')
    bw_img_floor_size = (width/size_x, height/size_y)
    bw_img_floor = pygame.transform.scale(bw_img_floor, bw_img_floor_size)

    bw_img_gold = load_image('bw_gold.png')
    bw_img_gold_size = (width/size_x, height/size_y)
    bw_img_gold = pygame.transform.scale(bw_img_gold, bw_img_gold_size)

    bw_img_pit = load_image('bw_pit.png')
    bw_img_pit_size = (width/size_x, height/size_y)
    bw_img_pit = pygame.transform.scale(bw_img_pit, bw_img_pit_size)

    bw_img_enemy1 = load_image('bw_enemy1.png')
    bw_img_enemy1_size = (width/size_x, height/size_y)
    bw_img_enemy1 = pygame.transform.scale(bw_img_enemy1, bw_img_enemy1_size)

    bw_img_enemy2 = load_image('bw_enemy2.png')
    bw_img_enemy2_size = (width/size_x, height/size_y)
    bw_img_enemy2 = pygame.transform.scale(bw_img_enemy2, bw_img_enemy2_size)

    bw_img_enemy_unknown = make_enemy_unknown_image(bw_img_enemy1, bw_img_enemy2)

    bw_img_bat = load_image('bw_bat.png')
    bw_img_bat_size = (width/size_x, height/size_y)
    bw_img_bat = pygame.transform.scale(bw_img_bat, bw_img_bat_size)

    bw_img_health = load_image('bw_health.png')
    bw_img_health_size = (width/size_x, height/size_y)
    bw_img_health = pygame.transform.scale(bw_img_health, bw_img_health_size)  

def update(dt, screen):
    global elapsed_time, actions_queue
    elapsed_time += dt
    
    if (elapsed_time / 1000) > auto_play_tempo:
        if auto_play and player_pos[2] != 'morto' and game_over_reason == "":
            if len(actions_queue) > 0:
                acao = actions_queue.pop(0)
                execute_action(acao)
            else:
                acao = decisao()
                if acao == 'a_estrela':
                    plan_astar()
                    if len(actions_queue) > 0:
                        acao = actions_queue.pop(0)
                        execute_action(acao)
                elif acao != "":
                    execute_action(acao)
        elapsed_time = 0   

def key_pressed(event):
    global debug
    if event.type == pygame.KEYDOWN:
        if not auto_play and player_pos[2] != 'morto' and game_over_reason == "":
            if event.key == pygame.K_LEFT: 
                execute_action("virar_esquerda")
            elif event.key == pygame.K_RIGHT: 
                execute_action("virar_direita")
            elif event.key == pygame.K_UP: 
                execute_action("andar")
            if event.key == pygame.K_SPACE:
                execute_action("pegar")
        if event.key == pygame.K_m:
            debug = not debug
            update_prolog()


def draw_screen(screen):
    screen.fill((0,0,0))
    y = 0
    for j in mapa:
        x = 0
        for i in j:
            coord = (x+1, size_y-y)
            confirmed = debug or coord in certezas

            if coord in visitados:
                screen.blit(img_floor, (x * img_floor.get_width(), y * img_floor.get_height()))
            else:
                screen.blit(bw_img_floor, (x * bw_img_floor.get_width(), y * bw_img_floor.get_height()))

            if mapa[size_y-1-y][x].find('P') > -1:
                if confirmed: screen.blit(img_pit, (x * img_pit.get_width(), y * img_pit.get_height()))                            
                else: screen.blit(bw_img_pit, (x * bw_img_pit.get_width(), y * bw_img_pit.get_height()))                            

            if mapa[size_y-1-y][x].find('T') > -1:
                if confirmed: screen.blit(img_bat, (x * img_bat.get_width(), y * img_bat.get_height()))
                else: screen.blit(bw_img_bat, (x * bw_img_bat.get_width(), y * bw_img_bat.get_height()))

            if mapa[size_y-1-y][x].find('D') > -1:
                if confirmed: screen.blit(img_enemy1, (x * img_enemy1.get_width(), y * img_enemy1.get_height()))                                               
                else: screen.blit(bw_img_enemy1, (x * bw_img_enemy1.get_width(), y * bw_img_enemy1.get_height()))                                               
                            
            if mapa[size_y-1-y][x].find('d') > -1:
                if confirmed: screen.blit(img_enemy2, (x * img_enemy2.get_width(), y * img_enemy2.get_height()))                                               
                else: screen.blit(bw_img_enemy2, (x * bw_img_enemy2.get_width(), y * bw_img_enemy2.get_height()))                                               

            if mapa[size_y-1-y][x].find('I') > -1:
                if confirmed: screen.blit(img_enemy_unknown, (x * img_enemy_unknown.get_width(), y * img_enemy_unknown.get_height()))
                else: screen.blit(bw_img_enemy_unknown, (x * bw_img_enemy_unknown.get_width(), y * bw_img_enemy_unknown.get_height()))

            if mapa[size_y-1-y][x].find('U') > -1:
                if confirmed: screen.blit(img_health, (x * img_health.get_width(), y * img_health.get_height()))                               
                else: screen.blit(bw_img_health, (x * bw_img_health.get_width(), y * bw_img_health.get_height()))                               

            if mapa[size_y-1-y][x].find('O') > -1:
                if confirmed: screen.blit(img_gold, (x * img_gold.get_width(), y * img_gold.get_height()))                
                else: screen.blit(bw_img_gold, (x * bw_img_gold.get_width(), y * bw_img_gold.get_height()))                
            
            if x == player_pos[0] - 1  and  y == size_y - player_pos[1]:
                if player_pos[2] == 'norte': screen.blit(img_player_up, (x * img_player_up.get_width(), y * img_player_up.get_height()))                                               
                elif player_pos[2] == 'sul': screen.blit(img_player_down, (x * img_player_down.get_width(), y * img_player_down.get_height()))                                               
                elif player_pos[2] == 'leste': screen.blit(img_player_right, (x * img_player_right.get_width(), y * img_player_right.get_height()))                                               
                elif player_pos[2] == 'oeste': screen.blit(img_player_left, (x * img_player_left.get_width(), y * img_player_left.get_height()))                                                                                                           
                else: screen.blit(img_tomb, (x * img_tomb.get_width(), y * img_tomb.get_height()))                                                                                                           
            x  += 1
        y +=  1

    t = sys_font.render("Pontuação: " + str(pontuacao), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=40))

    status_text = "Acao: " + (last_action if last_action else "-")
    if game_over_reason != "":
        status_text = "Fim: " + game_over_reason

    t = sys_font.render(status_text, False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width/2-40))
    
    t = sys_font.render("Energia: " + str(energia), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width-140))

    plano = " > ".join(str(a) for a in actions_queue[:8])
    if len(actions_queue) > 8:
        plano += " > ..."
    if plano == "":
        plano = "-"
    info_text = "Evento: " + (ultimo_evento if ultimo_evento else "-") + "    Plano: " + plano
    if len(info_text) > 92:
        info_text = info_text[:89] + "..."
    t = sys_font.render(info_text, False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 32, left=40))

def main_loop(screen):  
    global clock
    running = True
    
    while running:
        for e in pygame.event.get(): 
            if e.type == pygame.QUIT:
                running = False
                break
            key_pressed(e)
            
        dt = clock.tick()
        update(dt, screen)
        draw_screen(screen)
        pygame.display.update() 

def main():
    update_prolog()
    pygame.init()
    pygame.display.set_caption('INF1771 Trabalho 2 - Agente Logico Pitfall')
    screen = pygame.display.set_mode((width, height+footer_height))
    load()
    main_loop(screen)
    pygame.quit()

update_prolog()

if __name__ == "__main__":
    main()
