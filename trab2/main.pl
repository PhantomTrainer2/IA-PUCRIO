%% Breno Pinheiro Gallo de Sá - 2110183
%% Felippe Petrasso Fonseca Hübner - 210870
%% Eduardo Vasques Zacour - 1611696

:- dynamic posicao/3.
:- dynamic memory/3.
:- dynamic visitado/2.
:- dynamic certeza/2.
:- dynamic energia/1.
:- dynamic pontuacao/1.
:- dynamic tile/3.
:- dynamic map_size/2.
:- dynamic ouro_restante/1.
:- dynamic jogo_finalizado/1.
:- dynamic ultimo_evento/1.
:- dynamic seed_aleatorio/1.
:- dynamic mapa_atual/1.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Mapa e estado inicial
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

reset_game :-
    mapa_atual(Arquivo), !,
    carregar_mapa_arquivo(Arquivo).
reset_game :-
    gerar_mapa_aleatorio.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Utilitarios locais
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

membro(X, [X|_]).
membro(X, [_|T]) :-
    membro(X, T).

tamanho([], 0).
tamanho([_|T], N) :-
    tamanho(T, N0),
    N is N0 + 1.

intersecao([], _, []).
intersecao([H|T], L, [H|R]) :-
    membro(H, L), !,
    intersecao(T, L, R).
intersecao([_|T], L, R) :-
    intersecao(T, L, R).

remove_membro(_, [], []).
remove_membro(X, [X|T], R) :-
    !,
    remove_membro(X, T, R).
remove_membro(X, [H|T], [H|R]) :-
    remove_membro(X, T, R).

unicos([], []).
unicos([H|T], R) :-
    membro(H, T), !,
    unicos(T, R).
unicos([H|T], [H|R]) :-
    unicos(T, R).

inicia_semente :-
    retractall(seed_aleatorio(_)),
    get_time(T),
    S0 is floor(T * 1000000) mod 2147483647,
    (S0 =:= 0 -> S = 1 ; S = S0),
    assertz(seed_aleatorio(S)).

proximo_aleatorio(R) :-
    seed_aleatorio(S0), !,
    R is (1103515245 * S0 + 12345) mod 2147483648,
    retractall(seed_aleatorio(_)),
    assertz(seed_aleatorio(R)).
proximo_aleatorio(R) :-
    inicia_semente,
    proximo_aleatorio(R).

rand_between(Min, Max, Valor) :-
    proximo_aleatorio(R),
    Faixa is Max - Min + 1,
    Valor is Min + (R mod Faixa).

reset_estado_agente :-
    retractall(memory(_,_,_)),
    retractall(visitado(_,_)),
    retractall(certeza(_,_)),
    retractall(energia(_)),
    retractall(pontuacao(_)),
    retractall(posicao(_,_,_)),
    retractall(ouro_restante(_)),
    retractall(jogo_finalizado(_)),
    retractall(ultimo_evento(_)),
    assertz(energia(100)),
    assertz(pontuacao(0)),
    conta_tile('O', Ouro),
    assertz(ouro_restante(Ouro)),
    assertz(posicao(1, 1, norte)),
    marca_visitado(1, 1),
    atualiza_obs.

substitui_tile(X, Y, Simbolo) :-
    retractall(tile(X, Y, _)),
    assertz(tile(X, Y, Simbolo)).

carregar_mapa_arquivo(Arquivo) :-
    retractall(tile(_,_,_)),
    retractall(map_size(_,_)),
    retractall(mapa_atual(_)),
    consult(Arquivo),
    assertz(mapa_atual(Arquivo)),
    inicia_semente,
    (map_size(_,_) -> true ; assertz(map_size(12, 12))),
    garante_mapa_completo,
    mapa_atende_pdf,
    reset_estado_agente.

gerar_mapa_aleatorio :-
    retractall(tile(_,_,_)),
    retractall(map_size(_,_)),
    retractall(mapa_atual(_)),
    inicia_semente,
    assertz(map_size(12, 12)),
    garante_mapa_completo,
    coloca_elementos_pdf,
    reset_estado_agente.

coloca_elementos_pdf :-
    coloca_n('P', 8),
    coloca_n('O', 3),
    coloca_n('U', 3),
    coloca_n('T', 4),
    coloca_n('D', 2),
    coloca_n('d', 2).

coloca_n(_, 0) :- !.
coloca_n(Simbolo, N) :-
    sorteia_casa_livre(X, Y),
    substitui_tile(X, Y, Simbolo),
    N1 is N - 1,
    coloca_n(Simbolo, N1).

sorteia_casa_livre(X, Y) :-
    findall((LX,LY), casa_livre_para_elemento(LX, LY), Livres),
    tamanho(Livres, Total),
    Total > 0,
    rand_between(1, Total, Indice),
    nth1(Indice, Livres, (X,Y)).

casa_livre_para_elemento(X, Y) :-
    tile(X, Y, ''),
    \+ (X = 1, Y = 1).

garante_mapa_completo :-
    map_size(MX, MY),
    forall((between(1, MX, X), between(1, MY, Y)), garante_tile(X, Y)).

garante_tile(X, Y) :-
    tile(X, Y, _), !.
garante_tile(X, Y) :-
    assertz(tile(X, Y, '')).

conta_tile(Simbolo, Quantidade) :-
    findall((X,Y), tile(X, Y, Simbolo), Casas),
    tamanho(Casas, Quantidade).

mapa_atende_pdf :-
    map_size(12, 12),
    conta_tile('P', 8),
    conta_tile('O', 3),
    conta_tile('U', 3),
    conta_tile('T', 4),
    conta_tile('D', 2),
    conta_tile('d', 2),
    tile(1, 1, '').

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Controle de status
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

atualiza_pontuacao(Delta) :-
    pontuacao(P),
    NP is P + Delta,
    retractall(pontuacao(_)),
    assertz(pontuacao(NP)), !.

atualiza_energia(Delta) :-
    energia(E),
    NE0 is E + Delta,
    ( NE0 =< 0 -> NE = 0
    ; NE0 > 100 -> NE = 100
    ; NE = NE0
    ),
    retractall(energia(_)),
    assertz(energia(NE)), !.

decrementa_ouro :-
    ouro_restante(N),
    N1 is N - 1,
    (N1 < 0 -> N2 = 0 ; N2 = N1),
    retractall(ouro_restante(_)),
    assertz(ouro_restante(N2)).

energia_para_powerup :-
    energia(E),
    E =< 20.

energia_sobrevive_inimigo_comum :-
    energia(E),
    E > 50.

registra_evento(Evento) :-
    retractall(ultimo_evento(_)),
    assertz(ultimo_evento(Evento)).

finaliza(Motivo) :-
    jogo_finalizado(_), !,
    registra_evento(Motivo).
finaliza(Motivo) :-
    assertz(jogo_finalizado(Motivo)),
    registra_evento(Motivo).

marca_morto :-
    posicao(X, Y, _),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, morto)).

marca_visitado(X, Y) :-
    (visitado(X, Y) -> true ; assertz(visitado(X, Y))),
    set_real(X, Y).

verifica_saida :-
    ouro_restante(0),
    posicao(1, 1, _),
    finaliza(saiu), !.
verifica_saida.

sair :-
    \+ jogo_finalizado(_),
    ouro_restante(0),
    posicao(1, 1, _),
    finaliza(saiu), !.
sair :-
    \+ jogo_finalizado(_),
    registra_evento(saida_bloqueada), !.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Eventos do ambiente
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

verifica_player :-
    jogo_finalizado(_), !.
verifica_player :-
    posicao(X, Y, _),
    tile(X, Y, 'P'),
    atualiza_energia(-1000),
    atualiza_pontuacao(-1000),
    marca_morto,
    finaliza(morto_poco), !.
verifica_player :-
    posicao(X, Y, _),
    tile(X, Y, 'D'),
    enfrenta_inimigo(X, Y, 50), !.
verifica_player :-
    posicao(X, Y, _),
    tile(X, Y, 'd'),
    enfrenta_inimigo(X, Y, 20), !.
verifica_player :-
    posicao(X, Y, _),
    tile(X, Y, 'T'),
    teletransporta, !.
verifica_player :-
    verifica_saida, !.

enfrenta_inimigo(X, Y, Dano) :-
    substitui_tile(X, Y, ''),
    set_real(X, Y),
    atualiza_energia(-Dano),
    atualiza_pontuacao(-Dano),
    energia(E),
    ( E =:= 0 ->
        atualiza_pontuacao(-1000),
        marca_morto,
        finaliza(morto_inimigo)
    ;   registra_evento(grito),
        verifica_saida
    ).

teletransporta :-
    registra_evento(flash),
    posicao(_, _, Dir),
    map_size(MX, MY),
    rand_between(1, MX, NX),
    rand_between(1, MY, NY),
    retractall(posicao(_,_,_)),
    assertz(posicao(NX, NY, Dir)),
    marca_visitado(NX, NY),
    atualiza_obs,
    verifica_player.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Comandos
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

virar_direita :-
    \+ jogo_finalizado(_),
    posicao(X, Y, norte),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, leste)),
    atualiza_pontuacao(-1), !.
virar_direita :-
    \+ jogo_finalizado(_),
    posicao(X, Y, leste),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, sul)),
    atualiza_pontuacao(-1), !.
virar_direita :-
    \+ jogo_finalizado(_),
    posicao(X, Y, sul),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, oeste)),
    atualiza_pontuacao(-1), !.
virar_direita :-
    \+ jogo_finalizado(_),
    posicao(X, Y, oeste),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, norte)),
    atualiza_pontuacao(-1), !.

virar_esquerda :-
    \+ jogo_finalizado(_),
    posicao(X, Y, norte),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, oeste)),
    atualiza_pontuacao(-1), !.
virar_esquerda :-
    \+ jogo_finalizado(_),
    posicao(X, Y, oeste),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, sul)),
    atualiza_pontuacao(-1), !.
virar_esquerda :-
    \+ jogo_finalizado(_),
    posicao(X, Y, sul),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, leste)),
    atualiza_pontuacao(-1), !.
virar_esquerda :-
    \+ jogo_finalizado(_),
    posicao(X, Y, leste),
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, norte)),
    atualiza_pontuacao(-1), !.

andar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, norte),
    map_size(_, MAX_Y),
    Y < MAX_Y,
    NY is Y + 1,
    move_para(X, NY, norte), !.
andar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, sul),
    Y > 1,
    NY is Y - 1,
    move_para(X, NY, sul), !.
andar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, leste),
    map_size(MAX_X, _),
    X < MAX_X,
    NX is X + 1,
    move_para(NX, Y, leste), !.
andar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, oeste),
    X > 1,
    NX is X - 1,
    move_para(NX, Y, oeste), !.
andar :-
    \+ jogo_finalizado(_),
    registra_evento(impacto),
    atualiza_pontuacao(-1), !.

move_para(X, Y, Dir) :-
    retractall(posicao(_,_,_)),
    assertz(posicao(X, Y, Dir)),
    atualiza_pontuacao(-1),
    marca_visitado(X, Y).

pegar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, _),
    tile(X, Y, 'O'),
    substitui_tile(X, Y, ''),
    atualiza_pontuacao(-1),
    atualiza_pontuacao(1000),
    decrementa_ouro,
    set_real(X, Y),
    verifica_saida, !.
pegar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, _),
    tile(X, Y, 'U'),
    energia_para_powerup,
    substitui_tile(X, Y, ''),
    atualiza_pontuacao(-1),
    atualiza_energia(20),
    set_real(X, Y), !.
pegar :-
    \+ jogo_finalizado(_),
    posicao(X, Y, _),
    tile(X, Y, 'U'),
    atualiza_pontuacao(-1),
    registra_evento(powerup_guardado), !.
pegar :-
    \+ jogo_finalizado(_),
    atualiza_pontuacao(-1),
    registra_evento(nada), !.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Navegacao e observacao
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

adjacente(X, Y) :-
    posicao(PX, Y, _),
    map_size(MAX_X, _),
    PX < MAX_X,
    X is PX + 1.
adjacente(X, Y) :-
    posicao(PX, Y, _),
    PX > 1,
    X is PX - 1.
adjacente(X, Y) :-
    posicao(X, PY, _),
    map_size(_, MAX_Y),
    PY < MAX_Y,
    Y is PY + 1.
adjacente(X, Y) :-
    posicao(X, PY, _),
    PY > 1,
    Y is PY - 1.

adjacentes(L) :-
    findall(Z, (adjacente(X, Y), tile(X, Y, Z)), L).

observacao_loc(brilho, L) :- membro('O', L).
observacao_loc(reflexo, L) :- membro('U', L).

observacao_adj(brisa, L) :- membro('P', L).
observacao_adj(flash, L) :- membro('T', L).
observacao_adj(passos, L) :- membro('D', L).
observacao_adj(passos, L) :- membro('d', L).

atualiza_obs :-
    adj_cand_obs(LP),
    observacoes(LO),
    iter_pos_list(LP, LO),
    observacao_certeza,
    observacao_explicada,
    observacao_vazia.

adj_cand_obs(L) :-
    findall((X,Y), (adjacente(X, Y), \+ visitado(X,Y)), L).

observacoes(Obs) :-
    adjacentes(L),
    findall(Y, observacao_adj(Y, L), Raw),
    unicos(Raw, Obs).

iter_pos_list([], _) :- !.
iter_pos_list([H|T], LO) :-
    H = (X,Y),
    ( corrige_observacoes_antigas(X, Y, LO), !
    ; adiciona_observacoes(X, Y, LO)
    ),
    iter_pos_list(T, LO).

corrige_observacoes_antigas(X, Y, []) :-
    \+ certeza(X,Y),
    memory(X,Y,[]).
corrige_observacoes_antigas(X, Y, LO) :-
    \+ certeza(X,Y),
    \+ memory(X,Y,[]),
    memory(X, Y, LM),
    intersecao(LO, LM, L),
    retractall(memory(X, Y, _)),
    assertz(memory(X, Y, L)).

adiciona_observacoes(X, Y, _) :-
    certeza(X,Y), !.
adiciona_observacoes(X, Y, LO) :-
    \+ certeza(X,Y),
    \+ memory(X,Y,_),
    assertz(memory(X, Y, LO)).

observacao_certeza :-
    observacao_certeza(brisa),
    observacao_certeza(flash),
    observacao_certeza(passos).

observacao_certeza(Z) :-
    findall((X,Y),
        ( adjacente(X, Y),
          ((\+ visitado(X,Y), \+ certeza(X,Y)); (certeza(X,Y), memory(X,Y,[Z]))),
          memory(X,Y,[Z])
        ),
        L),
    ( tamanho(L, 1),
      L = [(XX,YY)],
      assertz(certeza(XX,YY)), !
    ; true
    ).

perigo_confirmado_adjacente(Z, X, Y) :-
    adjacente(X, Y),
    certeza(X, Y),
    memory(X, Y, Obs),
    membro(Z, Obs).

observacao_explicada :-
    observacoes(LO),
    observacao_explicada(LO).
observacao_explicada([]) :- !.
observacao_explicada([Z|T]) :-
    remove_observacao_explicada(Z),
    observacao_explicada(T).

remove_observacao_explicada(Z) :-
    perigo_confirmado_adjacente(Z, _, _), !,
    forall(
        ( adjacente(X, Y),
          \+ visitado(X, Y),
          \+ perigo_confirmado_adjacente(Z, X, Y),
          memory(X, Y, Obs),
          membro(Z, Obs)
        ),
        ( remove_membro(Z, Obs, NovoObs),
          retractall(memory(X, Y, _)),
          assertz(memory(X, Y, NovoObs))
        )
    ).
remove_observacao_explicada(_).

observacao_vazia :-
    adj_cand_obs(LP),
    observacao_vazia(LP).
observacao_vazia([]) :- !.
observacao_vazia([H|T]) :-
    H = (X,Y),
    ( memory(X,Y,[]),
      \+ certeza(X,Y),
      assertz(certeza(X,Y)), !
    ; true
    ),
    observacao_vazia(T).

set_real(X, Y) :-
    retractall(certeza(X,Y)),
    assertz(certeza(X,Y)),
    set_real2(X,Y), !.
set_real2(X, Y) :-
    tile(X,Y,'P'),
    retractall(memory(X,Y,_)),
    assertz(memory(X,Y,[brisa])), !.
set_real2(X, Y) :-
    tile(X,Y,'O'),
    retractall(memory(X,Y,_)),
    assertz(memory(X,Y,[brilho])), !.
set_real2(X, Y) :-
    tile(X,Y,'T'),
    retractall(memory(X,Y,_)),
    assertz(memory(X,Y,[flash])), !.
set_real2(X, Y) :-
    (tile(X,Y,'D'); tile(X,Y,'d')),
    retractall(memory(X,Y,_)),
    assertz(memory(X,Y,[passos])), !.
set_real2(X, Y) :-
    tile(X,Y,'U'),
    retractall(memory(X,Y,_)),
    assertz(memory(X,Y,[reflexo])), !.
set_real2(X, Y) :-
    tile(X,Y,''),
    retractall(memory(X,Y,_)),
    assertz(memory(X,Y,[])), !.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Mostra mapa real e mapa conhecido
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

show_player(X,Y) :- posicao(X,Y, norte), write('^'), !.
show_player(X,Y) :- posicao(X,Y, oeste), write('<'), !.
show_player(X,Y) :- posicao(X,Y, leste), write('>'), !.
show_player(X,Y) :- posicao(X,Y, sul), write('v'), !.
show_player(X,Y) :- posicao(X,Y, morto), write('+'), !.

show_position(X,Y) :-
    (show_player(X,Y); write(' ')),
    tile(X,Y,Z),
    ((Z = '', write(' ')); write(Z)), !.

show_map :-
    map_size(_, MAX_Y),
    show_map(1, MAX_Y), !.
show_map(X,Y) :-
    Y >= 1,
    map_size(MAX_X, _),
    X =< MAX_X,
    show_position(X,Y),
    write(' | '),
    XX is X + 1,
    show_map(XX, Y), !.
show_map(X,Y) :-
    Y >= 1,
    map_size(X, _),
    YY is Y - 1,
    write(Y), nl,
    show_map(1, YY), !.
show_map(_,0) :-
    energia(E),
    pontuacao(P),
    write('E: '), write(E),
    write('   P: '), write(P), !.

show_mem_info(X,Y) :-
    memory(X,Y,Z),
    ((visitado(X,Y), write('.'), !); (\+ certeza(X,Y), write('?'), !); (certeza(X,Y), write('!'))),
    ((membro(brisa, Z), write('P')); write(' ')),
    ((membro(flash, Z), write('T')); write(' ')),
    ((membro(brilho, Z), write('O')); write(' ')),
    ((membro(passos, Z), write('D')); write(' ')),
    ((membro(reflexo, Z), write('U')); write(' ')), !.

show_mem_info(X,Y) :-
    \+ memory(X,Y,[]),
    ((visitado(X,Y), write('.'), !); (\+ certeza(X,Y), write('?'), !); (certeza(X,Y), write('!'))),
    write('     '), !.

show_mem_position(X,Y) :-
    posicao(X,Y,_),
    ((visitado(X,Y), write('.'), !); (certeza(X,Y), write('!'), !); write(' ')),
    write(' '),
    show_player(X,Y),
    (( memory(X,Y,Z),
       ((membro(brilho, Z), write('O')); write(' ')),
       ((membro(passos, Z), write('D')); write(' ')),
       ((membro(reflexo, Z), write('U')); write(' ')), !
     )
    ; (write('   '), !)
    ).

show_mem_position(X,Y) :-
    show_mem_info(X,Y), !.

show_mem :-
    map_size(_, MAX_Y),
    show_mem(1, MAX_Y), !.
show_mem(X,Y) :-
    Y >= 1,
    map_size(MAX_X, _),
    X =< MAX_X,
    show_mem_position(X,Y),
    write('|'),
    XX is X + 1,
    show_mem(XX, Y), !.
show_mem(X,Y) :-
    Y >= 1,
    map_size(X, _),
    YY is Y - 1,
    write(Y), nl,
    show_mem(1, YY), !.
show_mem(_,0) :-
    energia(E),
    pontuacao(P),
    write('E: '), write(E),
    write('   P: '), write(P), !.

%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%
%% Tomada de decisao do agente
%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%

adjacente_coord(X, Y, NX, Y) :-
    NX is X + 1,
    map_size(MX, _),
    NX =< MX.
adjacente_coord(X, Y, NX, Y) :-
    NX is X - 1,
    NX >= 1.
adjacente_coord(X, Y, X, NY) :-
    NY is Y + 1,
    map_size(_, MY),
    NY =< MY.
adjacente_coord(X, Y, X, NY) :-
    NY is Y - 1,
    NY >= 1.

sala_segura(X, Y) :-
    map_size(MX, MY),
    between(1, MX, X),
    between(1, MY, Y),
    ( visitado(X, Y)
    ; \+ visitado(X, Y),
      memory(X, Y, Obs),
      \+ membro(brisa, Obs),
      \+ membro(passos, Obs),
      \+ membro(flash, Obs)
    ).

sala_risco_controlado(X, Y) :-
    sala_inimigo_arriscavel(X, Y).

sala_inimigo_arriscavel(X, Y) :-
    map_size(MX, MY),
    between(1, MX, X),
    between(1, MY, Y),
    \+ visitado(X, Y),
    memory(X, Y, Obs),
    \+ membro(brisa, Obs),
    \+ membro(flash, Obs),
    membro(passos, Obs),
    energia_sobrevive_inimigo_comum.

existe_alvo_inimigo_arriscavel :-
    sala_inimigo_arriscavel(_, _), !.

teletransporte_ultimo_recurso :-
    energia_para_powerup, !.
teletransporte_ultimo_recurso :-
    \+ existe_alvo_seguro,
    \+ existe_alvo_inimigo_arriscavel.

sala_morcego_arriscado(X, Y) :-
    map_size(MX, MY),
    between(1, MX, X),
    between(1, MY, Y),
    \+ visitado(X, Y),
    memory(X, Y, Obs),
    \+ membro(brisa, Obs),
    \+ membro(passos, Obs),
    membro(flash, Obs),
    teletransporte_ultimo_recurso.

alvo_seguro(X, Y) :-
    sala_segura(X, Y),
    \+ visitado(X, Y).

existe_alvo_seguro :-
    alvo_seguro(_, _), !.

alvo_powerup(X, Y) :-
    energia_para_powerup,
    visitado(X, Y),
    memory(X, Y, Obs),
    membro(reflexo, Obs).

existe_alvo_powerup :-
    alvo_powerup(_, _), !.

alvo_exploracao(X, Y) :-
    alvo_seguro(X, Y).
alvo_exploracao(X, Y) :-
    sala_risco_controlado(X, Y).
alvo_exploracao(X, Y) :-
    sala_inimigo_arriscavel(X, Y).
alvo_exploracao(X, Y) :-
    sala_morcego_arriscado(X, Y).

existe_alvo_exploracao :-
    alvo_exploracao(_, _), !.

fronteira(X, Y) :-
    visitado(VX, VY),
    adjacente_coord(VX, VY, X, Y),
    \+ visitado(X, Y).

poco_confirmado(X, Y) :-
    certeza(X, Y),
    memory(X, Y, Obs),
    membro(brisa, Obs).

inimigo_mortal_confirmado(X, Y) :-
    certeza(X, Y),
    memory(X, Y, Obs),
    membro(passos, Obs),
    energia(E),
    E =< 50.

bloqueio_confirmado(X, Y) :-
    poco_confirmado(X, Y).
bloqueio_confirmado(X, Y) :-
    inimigo_mortal_confirmado(X, Y).

fronteira_aberta(X, Y) :-
    fronteira(X, Y),
    \+ bloqueio_confirmado(X, Y).

impossibilidade_confirmada :-
    ouro_restante(N),
    N > 0,
    \+ existe_alvo_exploracao,
    fronteira(_, _),
    \+ fronteira_aberta(_, _).

impossibilidade_confirmada :-
    ouro_restante(N),
    N > 0,
    \+ existe_alvo_exploracao,
    \+ fronteira(_, _).

deve_sair :-
    ouro_restante(0), !.

dir_necessaria(X, Y, NX, Y, leste) :- NX > X.
dir_necessaria(X, Y, NX, Y, oeste) :- NX < X.
dir_necessaria(X, Y, X, NY, norte) :- NY > Y.
dir_necessaria(X, Y, X, NY, sul) :- NY < Y.

acao_virar(Atual, Alvo, virar_direita) :-
    (Atual = norte, Alvo = leste);
    (Atual = leste, Alvo = sul);
    (Atual = sul, Alvo = oeste);
    (Atual = oeste, Alvo = norte).
acao_virar(Atual, Alvo, virar_esquerda) :-
    (Atual = norte, Alvo = oeste);
    (Atual = oeste, Alvo = sul);
    (Atual = sul, Alvo = leste);
    (Atual = leste, Alvo = norte).
acao_virar(Atual, Alvo, virar_direita) :-
    (Atual = norte, Alvo = sul);
    (Atual = sul, Alvo = norte);
    (Atual = leste, Alvo = oeste);
    (Atual = oeste, Alvo = leste).

executa_acao(nenhuma) :-
    jogo_finalizado(_), !.
executa_acao(pegar) :-
    posicao(X, Y, _),
    memory(X, Y, Obs),
    membro(brilho, Obs), !.
executa_acao(pegar) :-
    posicao(X, Y, _),
    memory(X, Y, Obs),
    membro(reflexo, Obs),
    energia_para_powerup, !.
executa_acao(sair) :-
    posicao(1, 1, _),
    deve_sair, !.
executa_acao(a_estrela) :-
    deve_sair, !.
executa_acao(a_estrela) :-
    existe_alvo_powerup, !.
executa_acao(Acao) :-
    posicao(X, Y, DirAtual),
    adjacente_coord(X, Y, NX, NY),
    \+ visitado(NX, NY),
    sala_segura(NX, NY),
    dir_necessaria(X, Y, NX, NY, DirAlvo),
    (DirAtual = DirAlvo -> Acao = andar ; acao_virar(DirAtual, DirAlvo, Acao)), !.
executa_acao(a_estrela) :-
    existe_alvo_seguro, !.
executa_acao(Acao) :-
    posicao(X, Y, DirAtual),
    adjacente_coord(X, Y, NX, NY),
    \+ visitado(NX, NY),
    sala_risco_controlado(NX, NY),
    dir_necessaria(X, Y, NX, NY, DirAlvo),
    (DirAtual = DirAlvo -> Acao = andar ; acao_virar(DirAtual, DirAlvo, Acao)), !.
executa_acao(Acao) :-
    posicao(X, Y, DirAtual),
    adjacente_coord(X, Y, NX, NY),
    \+ visitado(NX, NY),
    sala_inimigo_arriscavel(NX, NY),
    dir_necessaria(X, Y, NX, NY, DirAlvo),
    (DirAtual = DirAlvo -> Acao = andar ; acao_virar(DirAtual, DirAlvo, Acao)), !.
executa_acao(a_estrela) :-
    existe_alvo_exploracao, !.
executa_acao(nenhuma) :-
    ouro_restante(N),
    N > 0,
    \+ existe_alvo_powerup,
    \+ existe_alvo_exploracao, !.
executa_acao(a_estrela).
