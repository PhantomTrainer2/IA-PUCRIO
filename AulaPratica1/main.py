import colorama
import time
from queue import PriorityQueue
from TreeNode import TreeNode

colorama.init()

y = 0
x = 0

def clear_screen():
    print("\033[2J")


def read_file(filename):

    global x, y
    lines = None    
    start = (0,0)
    end = (0,0)

    with open(filename) as file:
        lines = file.readlines()

        j = 0
        for line in lines:
            lines[j] = line.strip('\n')
            
            if line.find('F') > -1:
                end = (line.find('F'), j)
            if line.find('I') > -1:
                start = (line.find('I'), j)
            j += 1

    x = len(lines[0])
    y = len(lines)

    return lines, start, end


def print_map(lines, actual):

    print()
    print()
    print()
            
    print("\033[%d;%dH" % (1, 1)) # y, x

    for j in range(y):
        for i in range(x):
            if actual[0] == i and actual[1] == j:
                print('█', end='')
            else:
                print(lines[j][i], end='')

        print()



def get_value(c):
    
    v = -1

    if c == '.' or c == 'I' or c == 'F':
        v = 1
    elif c == 'X':
        v = -1

    return v

def get_char_from_map(mapa, coord):
    return mapa[coord[1]][coord[0]]

def get_value_from_map(mapa, coord):
    return get_value(get_char_from_map(mapa, coord))


def add_valid_pos(nb, mapa, coord):        
    if get_value_from_map(mapa, coord) > -1:
        nb.append(coord)

def get_neighborhood(mapa, coord):
    
    nb = []
    if coord[0] == 0:
        add_valid_pos(nb, mapa, (coord[0] + 1, coord[1]))
    
    elif coord[0] == x - 1:
        add_valid_pos(nb, mapa, (coord[0] - 1, coord[1]))
    
    else:    
        add_valid_pos(nb, mapa, (coord[0] + 1, coord[1]))
        add_valid_pos(nb, mapa, (coord[0] - 1, coord[1]))
    

    if coord[1] == 0:
        add_valid_pos(nb, mapa, (coord[0], coord[1] + 1))
    
    elif coord[1] == y - 1:
        add_valid_pos(nb, mapa, (coord[0], coord[1] - 1))
    
    else:    
        add_valid_pos(nb, mapa, (coord[0], coord[1] + 1))
        add_valid_pos(nb, mapa, (coord[0], coord[1] - 1))
    
    return nb


def busca_largura(mapa):
	pass

def busca_profundidade(mapa):
	pass 

def manhattan_distance(_from, to):
    # |x2 - x1| + |y2 - y1|
    return abs(to[0] - _from[0]) + abs(to[1] - _from[1])

def busca_a_estrela(mapa):
	pass

#busca_largura(mapa)
def busca_largura(mapa, start_position, end_position):
   
    num_iteracoes = 0
    
    visitados = []  
    fronteira = []  
    
    #fronteira ← InsereNaFila(FazNó(Problema[EstadoInicial]), fronteira)
    fronteira.append(TreeNode(start_position,  0, 0))
    
    #do loop
    while fronteira:
        num_iteracoes += 1
        #nó ← RemovePrimeiro(fronteira)
        no_front = fronteira.pop(0)
        distancia_atual = no_front.get_value_gx()
        posicao_atual = no_front.get_coord()
        visitados.append(posicao_atual)
        
        if exibe_mapa_execucao:
            print_map(mapa, posicao_atual)
            time.sleep(0.1)
        
        #if nó[Estado] for igual a Problema[EstadoFinal]:
        if posicao_atual == end_position:
            #return Solução(nó)
            return no_front, num_iteracoes
            
        for viz in get_neighborhood(mapa, posicao_atual):
            if viz not in visitados:
                g_x = distancia_atual + get_value_from_map(mapa, viz)
                #fronteira ← InsereNaFila(ExpandeFronteira(Problema, nó), fronteira)
                no_child = TreeNode(viz, g_x, g_x)
                no_child.set_parent(no_front)
                fronteira.append(no_child)

                
    return None


#busca_profundidade(mapa)
def busca_profundidade(mapa, start_position, end_position):
    
    num_iteracoes = 0
    visitados = []  
    fronteira = []  
    
    #fronteira ← InsereNaPilha(FazNó(Problema[EstadoInicial]), fronteira)
    fronteira.append(TreeNode(start_position, 0, 0))
    
    #do loop
    while fronteira:
        num_iteracoes += 1
        #nó ← RemovePrimeiro(fronteira)
        no_front = fronteira.pop()
        distancia_atual = no_front.get_value_gx()
        posicao_atual = no_front.get_coord()
        visitados.append(posicao_atual)
        
        if exibe_mapa_execucao:
            print_map(mapa, posicao_atual)
            time.sleep(0.1)
        
        #if nó[Estado] for igual a Problema[EstadoFinal]:
        if posicao_atual == end_position:
            #return Solução(nó)
            return no_front, num_iteracoes
            
        for viz in get_neighborhood(mapa, posicao_atual):
            if viz not in visitados:
                g_x = distancia_atual + get_value_from_map(mapa, viz)
                #fronteira ← InsereNaPilha(ExpandeFronteira(Problema, nó), fronteira)
                no_child = TreeNode(viz, g_x, g_x)
                no_child.set_parent(no_front)
                fronteira.append(no_child)
                
    return None

def busca_a_estrela(mapa, start_position, end_position):
       
    num_iteracoes = 0
    
    visitados = []  
    fronteira = PriorityQueue()
    
    #fronteira ← InsereNaFila(FazNó(Problema[EstadoInicial]), fronteira)
    fronteira.put(TreeNode(start, manhattan_distance(start_position, end_position), 0))
    
    
    #do loop
    while fronteira:
        num_iteracoes += 1
        #nó ← RemovePrimeiro(fronteira)
        no_front = fronteira.get()
        distancia_atual = no_front.get_value_gx()
        posicao_atual = no_front.get_coord()
        visitados.append(posicao_atual)
        
        if exibe_mapa_execucao:
            print_map(mapa, posicao_atual)
            time.sleep(0.1)
        
        #if nó[Estado] for igual a Problema[EstadoFinal]:
        if posicao_atual == end_position:
            #return Solução(nó)
            return no_front, num_iteracoes
            
        for viz in get_neighborhood(mapa, posicao_atual):
            if viz not in visitados:
                g_x = distancia_atual + get_value_from_map(mapa, viz)
                h_x = manhattan_distance(viz, end_position)
                f_x = g_x + h_x
                #fronteira ← InsereNaFila(ExpandeFronteira(Problema, nó), fronteira)
                no_child = TreeNode(viz, f_x, g_x)
                no_child.set_parent(no_front)
                fronteira.put(no_child)
                
    return None



def calc_solution_map(mapa, node):
        
    sol = []
    
    while node.get_parent() != None:           
        sol.append(node)
        node = node.get_parent()    
    sol.append(node)  # o inicio não tem pai mais precisa ser incluido

    while sol:
            
        no_arv = sol.pop() 
        coord = no_arv.get_coord()
        
        #substitui caracter nas coordenadas como se fosse mapa[coord[1]][coord[0]] = '█'
        mapa[coord[1]] = mapa[coord[1]][:coord[0]] + '█' + mapa[coord[1]][coord[0]+1:]
    return mapa

def print_solution_map(mapa, node):
    print_map(mapa, calc_solution_map(mapa, node))
    

#### COMECA AQUI

exibe_mapa_execucao = False #exibe mapa durante execucao
nome_mapa = 'mapa10.txt'
#nome_mapa = 'mapa20.txt'
#nome_mapa = 'mapa30.txt'

#Selecione Algoritmo
#alg = 0 # largura
#alg = 1 # profundidade
#alg = 2 # A Estrela
alg = 0

############################
clear_screen()

mapa, start, end = read_file(nome_mapa)

start_time = time.time()


if alg == 0:
    sol, num_iteracoes = busca_largura(mapa, start, end)
elif alg == 1:
    sol, num_iteracoes = busca_profundidade(mapa, start, end)
elif alg == 2:
    sol, num_iteracoes = busca_a_estrela(mapa, start, end)

end_time = time.time()

print_solution_map(mapa, sol)

if alg == 0:
    print("Busca em Largura")
elif alg == 1:
    print("Busca em Profundidade")
elif alg == 2:
    print("Busca A Estrela")

print(f"> Tempo de execução: {(end_time-start_time)*10**3:.03f}ms")
print(sol.get_coord(), sol.get_value_gx(), num_iteracoes)


