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
    from pyswip import Prolog, Functor, Variable, Query

BASE_DIR = pathlib.Path(__file__).resolve().parent
os.chdir(BASE_DIR)
current_path = str(BASE_DIR)

elapsed_time = 0
auto_play_tempo = 0.5
auto_play = True
show_map = False

scale = 60
size_x = 12
size_y = 12
width = size_x * scale
height = size_y * scale

player_pos = (1,1,'norte')
energia = 0
pontuacao = 0
game_over_reason = ""

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

def load_manual_map_from_args():
    if len(sys.argv) <= 1:
        return
    map_path = resolve_map_path(sys.argv[1])
    list(prolog.query(f"carregar_mapa_arquivo({prolog_atom(map_path)})"))

load_manual_map_from_args()

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

def frontier_risk(cell, memory):
    obs = memory.get(cell, set())
    risk = 3
    if 'brisa' in obs:
        risk += 10
    if 'flash' in obs:
        risk += 8
    if 'passos' in obs:
        risk += 1 if energia > 55 else 5
    if len(obs) == 0:
        risk = 2
    return risk

def plan_astar():
    global actions_queue
    curr_x, curr_y = player_pos[0], player_pos[1]
    curr_dir = player_pos[2]

    gold_left = get_prolog_value("ouro_restante(N)", "N", 0)
    visited_raw = get_prolog_list("visitado(X,Y)", ['X', 'Y'])
    visited = set(visited_raw) if visited_raw else set()
    visited.add((curr_x, curr_y))
    traversable = set(visited)
    candidate_scores = {}

    if gold_left == 0:
        candidates = {(1, 1)}
        candidate_scores = {(1, 1): 0}
        if (curr_x, curr_y) == (1, 1):
            actions_queue = ['sair']
            return
        print("A* voltando para a saida com todos os ouros coletados.")
    else:
        seguras_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_segura(X, Y)", ['X', 'Y'])
        seguras = set(seguras_raw) if seguras_raw else set()

        risco_raw = get_prolog_list("map_size(MX, MY), between(1, MX, X), between(1, MY, Y), sala_risco_controlado(X, Y)", ['X', 'Y'])
        risco_controlado = set(risco_raw) if risco_raw else set()

        frontier = set()
        for vx, vy in visited:
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = vx + dx, vy + dy
                if 1 <= nx <= size_x and 1 <= ny <= size_y:
                    if (nx, ny) not in visited:
                        frontier.add((nx, ny))

        safe_frontier = frontier.intersection(seguras)
        controlled_frontier = frontier.intersection(risco_controlado)

        if safe_frontier:
            candidates = safe_frontier
            candidate_scores = {cell: 0 for cell in candidates}
            print("A* buscando rota para uma fronteira segura.")
        elif controlled_frontier:
            candidates = controlled_frontier
            candidate_scores = {cell: 1 for cell in candidates}
            print("A* aceitando risco controlado contra inimigo.")
        else:
            memory = memory_snapshot()
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

    best_path = None
    best_score = None
    for cand in candidates:
        path = astar((curr_x, curr_y), cand, traversable)
        if path:
            score = (candidate_scores.get(cand, 0), len(path))
            if best_path is None or score < best_score:
                best_path = path
                best_score = score

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
        list(prolog.query(a))
    last_action = a

def update_prolog():
    global player_pos, mapa, energia, pontuacao, visitados, show_map, game_over_reason
    list(prolog.query("atualiza_obs, verifica_player"))

    x, y, z = Variable(), Variable(), Variable()
    visitado = Functor("visitado", 2)
    visitado_query = Query(visitado(x,y))
    visitados.clear()
    while visitado_query.nextSolution():
        visitados.append((x.value,y.value))
    visitado_query.closeQuery()

    certeza = Functor("certeza", 2)
    certeza_query = Query(certeza(x,y))
    certezas.clear()
    while certeza_query.nextSolution():
        certezas.append((x.value,y.value))
    certeza_query.closeQuery()
        
    if show_map:    
        tile = Functor("tile", 3)
        tile_query = Query(tile(x,y,z))
        while tile_query.nextSolution():
            mapa[y.get_value()-1][x.get_value()-1] = str(z.value)
        tile_query.closeQuery()
    else:
        for j in range(size_y):
            for i in range(size_x):
                mapa[j][i] = ''
        memory = Functor("memory", 3)
        memory_query = Query(memory(x,y,z))
        while memory_query.nextSolution():
            for s in z.value:
                if str(s) == 'brisa': mapa[y.get_value()-1][x.get_value()-1] += 'P'
                elif str(s) == 'flash': mapa[y.get_value()-1][x.get_value()-1] += 'T'
                elif str(s) == 'passos': mapa[y.get_value()-1][x.get_value()-1] += 'D'
                elif str(s) == 'reflexo': mapa[y.get_value()-1][x.get_value()-1] += 'U'
                elif str(s) == 'brilho': mapa[y.get_value()-1][x.get_value()-1] += 'O'
        memory_query.closeQuery()

    posicao = Functor("posicao", 3)
    position_query = Query(posicao(x,y,z))
    position_query.nextSolution()
    player_pos = (x.value,y.value,str(z.value))
    position_query.closeQuery()

    energia_func = Functor("energia", 1)
    energia_query = Query(energia_func(x))
    energia_query.nextSolution()
    energia = x.value
    energia_query.closeQuery()

    pontuacao_func = Functor("pontuacao", 1)
    pontuacao_query = Query(pontuacao_func(x))
    pontuacao_query.nextSolution()
    pontuacao = x.value
    pontuacao_query.closeQuery()

    status = list(prolog.query("jogo_finalizado(R)"))
    if len(status) > 0:
        reason = status[0]['R']
        if isinstance(reason, bytes):
            game_over_reason = reason.decode('utf-8')
        else:
            game_over_reason = str(reason)
    else:
        game_over_reason = ""

def load():
    global sys_font, clock, img_wall, img_grass, img_start, img_finish, img_path
    global img_gold,img_health, img_pit, img_bat, img_enemy1, img_enemy2,img_floor
    global bw_img_gold,bw_img_health, bw_img_pit, bw_img_bat, bw_img_enemy1, bw_img_enemy2,bw_img_floor
    global img_player_up, img_player_down, img_player_left, img_player_right, img_tomb

    sys_font = pygame.font.Font(pygame.font.get_default_font(), 20)
    clock = pygame.time.Clock() 

    img_wall = pygame.image.load('wall.jpg')
    img_wall_size = (width/size_x, height/size_y)
    img_wall = pygame.transform.scale(img_wall, img_wall_size)

    img_player_up = pygame.image.load('player_up.png')
    img_player_up_size = (width/size_x, height/size_y)
    img_player_up = pygame.transform.scale(img_player_up, img_player_up_size)

    img_player_down = pygame.image.load('player_down.png')
    img_player_down_size = (width/size_x, height/size_y)
    img_player_down = pygame.transform.scale(img_player_down, img_player_down_size)

    img_player_left = pygame.image.load('player_left.png')
    img_player_left_size = (width/size_x, height/size_y)
    img_player_left = pygame.transform.scale(img_player_left, img_player_left_size)

    img_player_right = pygame.image.load('player_right.png')
    img_player_right_size = (width/size_x, height/size_y)
    img_player_right = pygame.transform.scale(img_player_right, img_player_right_size)

    img_tomb = pygame.image.load('tombstone.png')
    img_tomb_size = (width/size_x, height/size_y)
    img_tomb = pygame.transform.scale(img_tomb, img_tomb_size)

    img_grass = pygame.image.load('grass.jpg')
    img_grass_size = (width/size_x, height/size_y)
    img_grass = pygame.transform.scale(img_grass, img_grass_size)

    img_floor = pygame.image.load('floor.png')
    img_floor_size = (width/size_x, height/size_y)
    img_floor = pygame.transform.scale(img_floor, img_floor_size)

    img_gold = pygame.image.load('gold.png')
    img_gold_size = (width/size_x, height/size_y)
    img_gold = pygame.transform.scale(img_gold, img_gold_size)

    img_pit = pygame.image.load('pit.png')
    img_pit_size = (width/size_x, height/size_y)
    img_pit = pygame.transform.scale(img_pit, img_pit_size)

    img_enemy1 = pygame.image.load('enemy1.png')
    img_enemy1_size = (width/size_x, height/size_y)
    img_enemy1 = pygame.transform.scale(img_enemy1, img_enemy1_size)

    img_enemy2 = pygame.image.load('enemy2.png')
    img_enemy2_size = (width/size_x, height/size_y)
    img_enemy2 = pygame.transform.scale(img_enemy2, img_enemy2_size)

    img_bat = pygame.image.load('bat.png')
    img_bat_size = (width/size_x, height/size_y)
    img_bat = pygame.transform.scale(img_bat, img_bat_size)

    img_health = pygame.image.load('health.png')
    img_health_size = (width/size_x, height/size_y)
    img_health = pygame.transform.scale(img_health, img_health_size)    
    
    bw_img_floor = pygame.image.load('bw_floor.png')
    bw_img_floor_size = (width/size_x, height/size_y)
    bw_img_floor = pygame.transform.scale(bw_img_floor, bw_img_floor_size)

    bw_img_gold = pygame.image.load('bw_gold.png')
    bw_img_gold_size = (width/size_x, height/size_y)
    bw_img_gold = pygame.transform.scale(bw_img_gold, bw_img_gold_size)

    bw_img_pit = pygame.image.load('bw_pit.png')
    bw_img_pit_size = (width/size_x, height/size_y)
    bw_img_pit = pygame.transform.scale(bw_img_pit, bw_img_pit_size)

    bw_img_enemy1 = pygame.image.load('bw_enemy1.png')
    bw_img_enemy1_size = (width/size_x, height/size_y)
    bw_img_enemy1 = pygame.transform.scale(bw_img_enemy1, bw_img_enemy1_size)

    bw_img_enemy2 = pygame.image.load('bw_enemy2.png')
    bw_img_enemy2_size = (width/size_x, height/size_y)
    bw_img_enemy2 = pygame.transform.scale(bw_img_enemy2, bw_img_enemy2_size)

    bw_img_bat = pygame.image.load('bw_bat.png')
    bw_img_bat_size = (width/size_x, height/size_y)
    bw_img_bat = pygame.transform.scale(bw_img_bat, bw_img_bat_size)

    bw_img_health = pygame.image.load('bw_health.png')
    bw_img_health_size = (width/size_x, height/size_y)
    bw_img_health = pygame.transform.scale(bw_img_health, bw_img_health_size)  

def update(dt, screen):
    global elapsed_time, actions_queue
    elapsed_time += dt
    
    if (elapsed_time / 1000) > auto_play_tempo:
        if auto_play and player_pos[2] != 'morto' and game_over_reason == "":
            if len(actions_queue) > 0:
                acao = actions_queue.pop(0)
                exec_prolog(acao)
                update_prolog()
            else:
                acao = decisao()
                if acao == 'a_estrela':
                    plan_astar()
                    if len(actions_queue) > 0:
                        acao = actions_queue.pop(0)
                        exec_prolog(acao)
                        update_prolog()
                elif acao != "":
                    exec_prolog(acao)
                    update_prolog()
        elapsed_time = 0   

def key_pressed(event):
    global show_map
    if event.type == pygame.KEYDOWN:
        if not auto_play and player_pos[2] != 'morto' and game_over_reason == "":
            if event.key == pygame.K_LEFT: 
                exec_prolog("virar_esquerda")
                update_prolog()
            elif event.key == pygame.K_RIGHT: 
                exec_prolog("virar_direita")
                update_prolog()
            elif event.key == pygame.K_UP: 
                exec_prolog("andar")
                update_prolog()
            if event.key == pygame.K_SPACE:
                exec_prolog("pegar")
                update_prolog()
        if event.key == pygame.K_m:
            show_map = not show_map
            update_prolog()


def draw_screen(screen):
    screen.fill((0,0,0))
    y = 0
    for j in mapa:
        x = 0
        for i in j:
            coord = (x+1, size_y-y)
            confirmed = show_map or coord in certezas

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

    status_text = last_action
    if game_over_reason != "":
        status_text = "Fim: " + game_over_reason

    t = sys_font.render(status_text, False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width/2-40))
    
    t = sys_font.render("Energia: " + str(energia), False, (255,255,255))
    screen.blit(t, t.get_rect(top = height + 5, left=width-140))

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
    screen = pygame.display.set_mode((width, height+30))
    load()
    main_loop(screen)
    pygame.quit()

update_prolog()

if __name__ == "__main__":
    main()
