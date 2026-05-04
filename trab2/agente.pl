% Declaração de fatos dinâmicos (que mudam ao longo do tempo)
:- dynamic visitado/2.
:- dynamic tem_brisa/2.
:- dynamic tem_passos/2.
:- dynamic tem_flash/2.
:- dynamic brilho/2.
:- dynamic posicao_atual/2.

% Definição do tamanho do mapa (12x12)
limite(X) :- X >= 1, X =< 12.

% Regras de adjacência (cima, baixo, esquerda, direita)
adjacente(X, Y, X1, Y) :- X1 is X + 1, limite(X1).
adjacente(X, Y, X1, Y) :- X1 is X - 1, limite(X1).
adjacente(X, Y, X, Y1) :- Y1 is Y + 1, limite(Y1).
adjacente(X, Y, X, Y1) :- Y1 is Y - 1, limite(Y1).

% Uma sala é considerada perigosa se uma sala adjacente visitada indicou perigo
% e não temos certeza absoluta de que esta sala específica está limpa.
risco_poco(X, Y) :- adjacente(X, Y, XA, YA), visitado(XA, YA), tem_brisa(XA, YA).
risco_inimigo(X, Y) :- adjacente(X, Y, XA, YA), visitado(XA, YA), tem_passos(XA, YA).
risco_teletransporte(X, Y) :- adjacente(X, Y, XA, YA), visitado(XA, YA), tem_flash(XA, YA).

% Uma sala é 100% segura se já foi visitada
seguro(X, Y) :- visitado(X, Y).

% Ou se é adjacente a uma sala visitada e não há indícios de perigo nela
seguro(X, Y) :-
    limite(X), limite(Y),
    \+ risco_poco(X, Y),
    \+ risco_inimigo(X, Y),
    \+ risco_teletransporte(X, Y).

% --- TOMADA DE DECISÃO ---

% Prioridade 1: Se tem brilho onde estou, pegar o ouro.
decidir_acao(pegar) :- 
    posicao_atual(X, Y), 
    brilho(X, Y).

% Prioridade 2: Mover para uma sala adjacente segura e não visitada.
decidir_acao(mover_adjacente(X, Y)) :-
    posicao_atual(XA, YA),
    adjacente(XA, YA, X, Y),
    \+ visitado(X, Y),
    seguro(X, Y).

% Prioridade 3: Se não há salas adjacentes seguras não visitadas, 
% delegamos para o Python usar o A* para encontrar a sala segura não visitada mais próxima.
decidir_acao(usar_a_estrela) :-
    \+ decidir_acao(mover_adjacente(_, _)).