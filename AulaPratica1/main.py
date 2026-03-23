from queue import PriorityQueue

y = 0
x = 0

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


def printMap(lines, actual):

    print()
    print()
    print()
            
    #print("\033[%d;%dH" % (0, 0)) # y, x

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


mapa, start, end = read_file('mapa10.txt')


def busca_largura(mapa):
    # Fronteira agora é uma lista normal do Python
    fronteira = []
    fronteira.append((start, [start])) 
    
    # set() é nativo do Python, não precisa importar nada!
    visitados = set()
    visitados.add(start)
    
    # loop do
    while len(fronteira) > 0:
        
        # Remove o primeiro elemento da lista (índice 0)
        atual, caminho = fronteira.pop(0)
        
        # Checa se chegamos no final
        if atual == end:
            return caminho
            
        # Expande a fronteira buscando os vizinhos
        vizinhos = get_neighborhood(mapa, atual)
        
        for vizinho in vizinhos:
            # Se ainda não pisamos neste vizinho...
            if vizinho not in visitados:
                visitados.add(vizinho) # Marca como visitado
                
                # Cria a nova rota
                novo_caminho = caminho + [vizinho]
                
                # Coloca o vizinho no final da lista
                fronteira.append((vizinho, novo_caminho))
                
    return None

def busca_profundidade(mapa):
	pass 

def manhattan_distance(_from, to):
    # |x2 - x1| + |y2 - y1|
    return abs(to[0] - _from[0]) + abs(to[1] - _from[1])

def busca_a_estrela(mapa):
	pass

def print_resultado(mapa, caminho):
    print("\n=== Resultado da Busca em Largura ===\n")
    
    # Transformamos a lista em um 'set' (conjunto) para a verificação ficar mais rápida
    caminho_set = set(caminho)
    
    for j in range(y):
        for i in range(x):
            # Se a coordenada atual faz parte do caminho que o algoritmo encontrou...
            if (i, j) in caminho_set:
                # Se for Início (I) ou Fim (F), mantemos a letra original 
                if mapa[j][i] == 'I' or mapa[j][i] == 'F':
                    print(mapa[j][i], end='')
                else:
                    # Desenhamos o caminho com um bloco (ou troque por '*' se preferir)
                    print('█', end='')
            else:
                # Se não faz parte do caminho, imprime o caractere original do mapa
                print(mapa[j][i], end='')
        print() # Quebra de linha ao final de cada linha do mapa

caminho_encontrado = busca_largura(mapa)

#busca_profundidade(mapa)
#busca_a_estrela(mapa)

print_resultado(mapa, caminho_encontrado)

