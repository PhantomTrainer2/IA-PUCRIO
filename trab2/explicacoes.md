# Explicacoes do projeto `trab2`

Este arquivo explica, de forma didatica, como os principais arquivos do trabalho funcionam e como eles se conectam para implementar o agente logico do mundo de Pitfall/Wumpus.

O projeto usa duas linguagens:

- **Prolog**, no arquivo `main.pl`, para representar o conhecimento do agente, o estado do jogo e a tomada de decisao.
- **Python**, no arquivo `gmap.py`, para carregar o Prolog, controlar a interface grafica, desenhar o mapa com Pygame e calcular caminhos com A*.

A ideia geral e: o Prolog sabe "o que o agente acredita" e "qual tipo de acao faz sentido"; o Python pergunta isso ao Prolog, calcula uma rota quando necessario, executa a acao e atualiza a tela.

## Visao geral do jogo

O mundo e um labirinto 12 x 12. O agente sempre comeca na posicao `[1, 1]`, que tambem e a saida.

O objetivo e pegar os 3 ouros e depois voltar para `[1, 1]` para sair vivo.

O mapa pode conter:

| Simbolo | Significado | Efeito |
| --- | --- | --- |
| `''` | sala vazia | sala livre |
| `P` | poco/obstaculo | morte imediata |
| `O` | ouro | pode ser pego, vale pontos |
| `U` | powerup | recupera energia |
| `T` | teletransporte/morcego | joga o agente em uma posicao aleatoria |
| `D` | inimigo grande | causa 50 de dano |
| `d` | inimigo pequeno | causa 20 de dano |

O agente nao deve enxergar o mapa real inteiro. Ele constroi uma memoria a partir dos sensores:

| Percepcao | Causa |
| --- | --- |
| `brisa` | existe um poco em uma sala adjacente |
| `flash` | existe um teletransporte em uma sala adjacente |
| `passos` | existe um inimigo comum em uma sala adjacente |
| `brilho` | existe ouro na sala atual |
| `reflexo` | existe powerup na sala atual |
| `impacto` | o agente tentou andar contra uma parede |
| `grito` | um inimigo morreu |

Adjacente aqui significa apenas norte, sul, leste e oeste. Diagonal nao conta.

## Arquivo `main.pl`

Este e o arquivo mais importante do projeto. Ele contem as regras Prolog que definem:

- o estado do jogo;
- o mapa;
- a memoria do agente;
- as percepcoes;
- os efeitos das acoes;
- a politica de risco;
- a proxima acao que o agente deve tentar.

### Fatos dinamicos

No comeco do arquivo aparecem varios predicados declarados como `dynamic`.

Exemplos:

```prolog
:- dynamic posicao/3.
:- dynamic memory/3.
:- dynamic visitado/2.
:- dynamic certeza/2.
:- dynamic energia/1.
:- dynamic pontuacao/1.
:- dynamic tile/3.
:- dynamic map_size/2.
:- dynamic ouro_restante/1.
```

Em Prolog, um fato dinamico pode ser criado, removido ou alterado durante a execucao.

Isso e necessario porque o jogo muda o tempo todo. Por exemplo:

- a posicao do agente muda quando ele anda;
- a energia muda quando ele toma dano ou pega powerup;
- um ouro some do mapa depois de ser pego;
- um inimigo some depois de ser derrotado;
- novas informacoes entram na memoria do agente.

### Estado inicial

A inicializacao principal acontece em `reset_estado_agente`.

Esse predicado:

1. Limpa memoria antiga.
2. Remove posicao, energia, pontuacao e estado de fim de jogo anteriores.
3. Coloca a energia em `100`.
4. Coloca a pontuacao em `0`.
5. Conta quantos ouros existem no mapa.
6. Coloca o agente em `[1, 1]`, olhando para `norte`.
7. Marca `[1, 1]` como visitado.
8. Atualiza as observacoes iniciais.

Assim, sempre que um mapa e carregado ou gerado, o agente comeca de forma limpa.

### Carregamento e geracao de mapas

Existem dois caminhos principais para criar o mapa:

```prolog
carregar_mapa_arquivo(Arquivo)
gerar_mapa_aleatorio
```

`carregar_mapa_arquivo/1` carrega um mapa pronto, como:

- `mapa_facil.pl`
- `mapa_medio.pl`
- `mapa_dificil.pl`

`gerar_mapa_aleatorio/0` cria um mapa novo automaticamente com as quantidades exigidas pelo PDF:

- 8 pocos;
- 3 ouros;
- 3 powerups;
- 4 teletransportes;
- 2 inimigos de dano 50;
- 2 inimigos de dano 20.

O predicado `mapa_atende_pdf` verifica se o mapa esta dentro dessas regras principais:

```prolog
mapa_atende_pdf :-
    map_size(12, 12),
    conta_tile('P', 8),
    conta_tile('O', 3),
    conta_tile('U', 3),
    conta_tile('T', 4),
    conta_tile('D', 2),
    conta_tile('d', 2),
    tile(1, 1, '').
```

Ou seja, o mapa precisa ser 12 x 12, ter as quantidades corretas e deixar a posicao inicial vazia.

### Pontuacao e energia

A pontuacao e alterada por `atualiza_pontuacao/1`.

A energia e alterada por `atualiza_energia/1`.

O codigo limita energia entre `0` e `100`:

- se ficaria abaixo de `0`, vira `0`;
- se passaria de `100`, fica em `100`.

Isso evita energia negativa ou acima do maximo.

### Powerup

O predicado:

```prolog
energia_para_powerup :-
    energia(E),
    E =< 20.
```

define quando o agente realmente precisa pegar powerup.

Com isso, o agente nao desperdicara powerup quando ainda tem energia alta. Ele guarda o powerup e so busca/pega quando a energia esta em `20` ou menos.

### Eventos do ambiente

O predicado `verifica_player/0` verifica o que acontece na sala atual.

Ele testa, nesta ordem:

1. Se o jogo ja acabou.
2. Se o agente caiu em um poco.
3. Se entrou em inimigo de dano 50.
4. Se entrou em inimigo de dano 20.
5. Se entrou em teletransporte.
6. Se chegou na saida com todos os ouros.

#### Poco

Se a sala tem `P`, o agente:

- perde muita energia;
- recebe penalidade de pontuacao;
- fica com direcao `morto`;
- finaliza o jogo com motivo `morto_poco`.

#### Inimigo comum

Se a sala tem `D` ou `d`, o predicado `enfrenta_inimigo/3` e chamado.

Ele:

1. Remove o inimigo da sala.
2. Atualiza a memoria daquela sala como segura.
3. Desconta o dano da energia.
4. Desconta o dano da pontuacao.
5. Se a energia chegou a `0`, finaliza como `morto_inimigo`.
6. Caso contrario, registra o evento `grito`.

#### Teletransporte

Se a sala tem `T`, o predicado `teletransporta/0` sorteia uma nova posicao aleatoria dentro do mapa:

```prolog
rand_between(1, MX, NX),
rand_between(1, MY, NY)
```

Depois disso, o agente aparece nessa nova sala e `verifica_player` roda novamente.

Isso e importante porque o PDF diz que o teletransporte pode jogar o agente em qualquer lugar: sala segura, poco, inimigo ou outro teletransporte.

### Comandos do agente

O agente consegue executar:

- `virar_direita`;
- `virar_esquerda`;
- `andar`;
- `pegar`;
- `sair`.

Cada uma dessas acoes altera o estado e desconta pontuacao.

#### Virar

`virar_direita` e `virar_esquerda` mudam apenas a direcao do agente.

Exemplo:

- se esta olhando para `norte` e vira a direita, passa a olhar para `leste`;
- se esta olhando para `norte` e vira a esquerda, passa a olhar para `oeste`.

#### Andar

`andar` move o agente uma casa para frente, se nao houver parede.

Se o agente esta em uma borda e tenta andar para fora do mapa, ele nao muda de posicao e registra o evento `impacto`.

#### Pegar

`pegar` serve para ouro e powerup.

Se existe ouro na sala:

- remove o ouro;
- soma a recompensa;
- diminui `ouro_restante`;
- verifica se ja pode sair.

Se existe powerup:

- so consome o powerup se `energia_para_powerup` for verdadeiro;
- caso contrario, registra `powerup_guardado`.

### Memoria do agente

O agente nao usa diretamente o mapa real para decidir. Ele usa `memory/3`.

Um exemplo de memoria:

```prolog
memory(3, 4, [brisa, passos]).
```

Isso significa:

"Na sala `[3,4]`, o agente acredita que existem indicios relacionados a poco e inimigo."

Tambem existe `certeza/2`, que indica que o agente tem certeza sobre uma sala.

Exemplo:

```prolog
certeza(1, 1).
```

### Observacoes

As observacoes sao atualizadas por `atualiza_obs/0`.

O processo geral e:

1. Olhar as salas adjacentes ainda nao visitadas.
2. Coletar percepcoes geradas pelo mapa real ao redor.
3. Atualizar a memoria das casas candidatas.
4. Marcar certezas quando uma unica sala explica uma percepcao.
5. Remover suspeitas explicadas por outras certezas.
6. Marcar salas sem observacoes como seguras.

Os sensores principais sao definidos aqui:

```prolog
observacao_adj(brisa, L) :- membro('P', L).
observacao_adj(flash, L) :- membro('T', L).
observacao_adj(passos, L) :- membro('D', L).
observacao_adj(passos, L) :- membro('d', L).
```

Repare que tanto o inimigo grande quanto o pequeno geram `passos`. Por isso o agente nao sabe, antes de entrar, se o inimigo causa 20 ou 50 de dano.

### Politica de risco

Esta e uma das partes centrais do trabalho.

O agente classifica salas em categorias.

#### Sala segura

Uma sala e segura se:

- ja foi visitada; ou
- nao visitada, mas sua memoria nao tem `brisa`, `passos` nem `flash`.

Isso fica em `sala_segura/2`.

#### Inimigo arriscavel

Uma sala com `passos` so pode ser escolhida se:

- nao tiver suspeita de poco (`brisa`);
- nao tiver suspeita de teletransporte (`flash`);
- tiver `passos`;
- a energia for maior que `50`.

O limite `> 50` e proposital. Como o sensor `passos` nao diferencia inimigo de dano 20 e inimigo de dano 50, o agente so entra se conseguir sobreviver ao pior caso.

#### Teletransporte

O teletransporte e tratado como ultimo recurso.

Ele so e aceito quando:

- a energia esta critica (`<= 20`); ou
- nao existe alvo seguro; e
- nao existe inimigo comum sobrevivivel.

Isso evita o erro de preferir teletransporte quando ainda existe caminho seguro ou inimigo comum enfrentavel.

#### Poco

Poco e o pior risco, porque mata instantaneamente.

A politica evita poco sempre que houver qualquer outra possibilidade permitida.

### Escolha da proxima acao

O predicado principal da tomada de decisao e:

```prolog
executa_acao(Acao)
```

Ele segue uma ordem de prioridade:

1. Se o jogo acabou, retorna `nenhuma`.
2. Se ha ouro na sala atual, retorna `pegar`.
3. Se ha powerup na sala atual e a energia esta baixa, retorna `pegar`.
4. Se esta na saida e ja pegou todos os ouros, retorna `sair`.
5. Se precisa voltar para a saida, pede `a_estrela`.
6. Se existe powerup conhecido necessario, pede `a_estrela`.
7. Se existe sala segura adjacente, anda ou vira para ela.
8. Se existe sala segura mais longe, pede `a_estrela`.
9. Se existe inimigo adjacente sobrevivivel, anda ou vira para ele.
10. Se existe outro alvo permitido, pede `a_estrela`.
11. Se ainda ha ouro, mas nao ha alvo permitido, retorna `nenhuma`.

O item 11 e importante: ele impede o Python de improvisar uma rota para uma suspeita proibida.

## Arquivo `gmap.py`

Este arquivo e o lado Python do projeto. Ele faz a interface grafica, conversa com o Prolog e implementa o A*.

Ele usa principalmente:

- `pygame`, para janela, imagens e teclado;
- `pyswip`, para consultar e executar predicados Prolog.

### Inicializacao

Logo no inicio, o Python:

1. Define o diretorio base do projeto.
2. Cria uma instancia de `Prolog`.
3. Carrega `main.pl`.
4. Carrega um mapa.

Se nenhum mapa for passado pela linha de comando, ele gera um mapa aleatorio:

```bash
python gmap.py
```

Se um mapa for passado, ele carrega esse mapa:

```bash
python gmap.py mapa_medio.pl
```

### Comunicacao com Prolog

O Python usa chamadas como:

```python
list(prolog.query("executa_acao(X)"))
```

Isso pergunta ao Prolog qual acao o agente quer executar.

Existem funcoes auxiliares:

- `run_prolog_goal`: executa uma consulta e gera erro se ela falhar;
- `get_prolog_list`: busca uma lista de resultados Prolog;
- `get_prolog_value`: busca um valor unico;
- `prolog_true`: testa se uma consulta e verdadeira.

### A classe `Node`

Dentro de `gmap.py` existe uma classe `Node`, usada pelo A*.

Cada no guarda:

- coordenada `x`;
- coordenada `y`;
- pai do no;
- custo percorrido `g`;
- heuristica `h`;
- custo total `f`.

O A* usa isso para reconstruir o caminho do agente ate o alvo.

### Algoritmo A*

O A* esta implementado na funcao:

```python
astar(start, target, traversable)
```

Ele recebe:

- `start`: posicao atual;
- `target`: alvo;
- `traversable`: conjunto de casas pelas quais o caminho pode passar.

O caminho so atravessa casas ja visitadas ou conhecidas como seguras. A excecao e o proprio alvo, porque o alvo pode ser uma fronteira ainda nao visitada.

Depois que o caminho e calculado, `path_to_actions` transforma coordenadas em acoes:

- virar a direita;
- virar a esquerda;
- andar.

### Planejamento com A*

A funcao mais importante do planejamento em Python e:

```python
plan_astar()
```

Ela e chamada quando o Prolog retorna `a_estrela`.

O papel dela nao e inventar a politica do agente do zero. A politica vem do Prolog. O Python usa as categorias do Prolog para escolher candidatos de caminho.

A ordem usada e:

1. Se ja pegou os ouros, tentar voltar para `[1,1]`.
2. Se precisa de powerup conhecido, ir ate ele.
3. Procurar fronteira segura.
4. Procurar fronteira com inimigo comum sobrevivivel.
5. Procurar teletransporte como ultimo recurso.
6. Se nao existe fronteira permitida, nao gera acao.

Essa ultima regra e essencial. Antes, o A* podia escolher a "menor suspeita" mesmo se ela fosse proibida pela politica de risco. Agora, se nao existe candidato permitido, `actions_queue` fica vazia.

### Fila de acoes

O Python nao executa um caminho inteiro de uma vez.

Ele guarda as acoes em:

```python
actions_queue
```

Exemplo:

```python
['virar_direita', 'andar', 'andar']
```

A cada ciclo de jogo, ele executa uma acao da fila.

Se acontece um evento que muda muito o mundo, como `flash` ou `impacto`, a fila e limpa e o agente precisa planejar de novo.

### Atualizacao do estado

A funcao:

```python
update_prolog()
```

atualiza tudo que a interface precisa mostrar:

- posicao do agente;
- energia;
- pontuacao;
- mapa conhecido;
- casas visitadas;
- certezas;
- evento mais recente;
- motivo de fim de jogo.

Ela tambem chama no Prolog:

```prolog
atualiza_obs, verifica_player
```

Isso garante que, depois de cada acao, as percepcoes e os eventos sejam processados.

### Renderizacao

A funcao `draw_screen` desenha o jogo.

Ela usa:

- imagens coloridas para coisas confirmadas ou modo debug;
- imagens em preto e branco para suspeitas;
- icones diferentes para ouro, powerup, poco, inimigo e teletransporte;
- o personagem apontando para a direcao atual.

Tambem mostra no rodape:

- pontuacao;
- ultima acao;
- energia;
- evento atual;
- parte do plano em execucao.

### Modo debug

A tecla `M` alterna o modo debug.

Quando `debug = False`, a tela mostra a interpretacao do agente.

Quando `debug = True`, a tela mostra o mapa real completo.

Importante: o modo debug altera apenas a visualizacao. Ele nao altera a tomada de decisao do agente.

## Arquivos de mapa

Os arquivos:

- `mapa_facil.pl`
- `mapa_medio.pl`
- `mapa_dificil.pl`
- `mapa.pl`
- arquivos com nomes usando hifen, como `mapa-facil.pl`

guardam mapas escritos manualmente.

Um mapa e basicamente uma colecao de fatos Prolog:

```prolog
map_size(12,12).
tile(1,1,'').
tile(2,1,'T').
tile(3,1,'').
```

Cada `tile(X, Y, Simbolo)` define o conteudo de uma sala.

O sistema espera que o mapa manual tambem respeite as quantidades do PDF. Se nao respeitar, `mapa_atende_pdf` falha.

## Arquivo `requirements.txt`

Esse arquivo lista as dependencias Python:

```txt
pyswip
pygame
```

`pyswip` permite que o Python converse com o SWI-Prolog.

`pygame` cria a janela e desenha o jogo.

## Arquivo `TreeNode.py`

Esse arquivo define uma classe `TreeNode`, que parece vir do codigo base ou de uma versao anterior da busca.

Ela tem:

- coordenada;
- prioridade;
- custo acumulado;
- pai;
- filhos.

No estado atual do projeto, o A* principal usa a classe `Node` dentro de `gmap.py`, nao `TreeNode`.

Entao `TreeNode.py` funciona mais como codigo legado ou auxiliar. Ele pode ser mantido no projeto sem atrapalhar.

## Arquivos de imagem

Os arquivos `.png` e `.jpg` sao os recursos visuais usados pelo Pygame.

Exemplos:

- `player_up.png`, `player_down.png`, `player_left.png`, `player_right.png`: personagem;
- `gold.png`: ouro;
- `health.png`: powerup;
- `pit.png`: poco;
- `bat.png`: teletransporte;
- `enemy1.png` e `enemy2.png`: inimigos;
- arquivos com prefixo `bw_`: versoes em preto e branco para memoria/suspeita.

Esses arquivos nao mudam a logica do agente. Eles apenas definem como o estado aparece na tela.

## Fluxo completo de uma jogada

Uma rodada automatica acontece assim:

1. O Python chama `decisao()`.
2. `decisao()` consulta `executa_acao(X)` no Prolog.
3. O Prolog responde uma acao simples ou `a_estrela`.
4. Se for uma acao simples, o Python executa diretamente.
5. Se for `a_estrela`, o Python chama `plan_astar()`.
6. O A* calcula um caminho ate um alvo permitido.
7. O caminho vira uma fila de acoes.
8. O Python executa a primeira acao da fila.
9. O Prolog atualiza posicao, energia, pontuacao e memoria.
10. A interface redesenha o mapa.

Esse ciclo se repete ate:

- o agente sair com os ouros;
- o agente morrer;
- nao existir nenhuma acao permitida pela politica de risco.

## Politica final do agente

A politica final do agente ficou assim:

1. Pegar ouro sempre que estiver na sala.
2. Pegar powerup apenas quando a energia estiver em `20` ou menos.
3. Enquanto houver ouro, explorar primeiro salas sem ameaca conhecida.
4. Se nao houver sala segura, aceitar inimigo comum apenas com energia maior que `50`.
5. Evitar teletransporte porque ele pode jogar o agente em poco.
6. Usar teletransporte apenas como ultimo recurso.
7. Nunca preferir teletransporte a uma sala segura.
8. Nunca preferir teletransporte a um inimigo comum sobrevivivel.
9. Nunca entrar em suspeita de inimigo comum sem energia para sobreviver ao pior caso.
10. Tratar poco como pior risco, porque causa morte imediata.
11. Depois de pegar todos os ouros, voltar para `[1,1]` e sair.

Essa politica segue a interpretacao discutida com o professor: teletransporte so e melhor do que poco, pois teletransportar pode levar o agente diretamente para um poco.

## Como executar

Para rodar com mapa aleatorio:

```bash
python gmap.py
```

Para rodar com mapa pronto:

```bash
python gmap.py mapa_medio.pl
```

Tambem existem aliases no Python:

```bash
python gmap.py facil
python gmap.py medio
python gmap.py dificil
```

## Como ler o comportamento na tela

Na tela aparecem:

- o mapa conhecido pelo agente;
- o personagem;
- pontuacao;
- energia;
- ultima acao;
- ultimo evento;
- plano parcial.

Quando uma casa aparece em preto e branco, normalmente significa suspeita ou informacao ainda nao confirmada.

Quando aparece colorida, normalmente e algo confirmado ou mostrado pelo modo debug.

## Pontos importantes para apresentar

Se for apresentar o trabalho, vale destacar:

1. O agente nao usa o mapa real para decidir.
2. A memoria e atualizada por sensores locais.
3. O Prolog contem a tomada de decisao.
4. O Python so executa, desenha e calcula rotas A* entre alvos permitidos.
5. A politica de risco evita o erro de usar teletransporte cedo demais.
6. O agente so enfrenta inimigo quando consegue sobreviver ao pior dano possivel.
7. O agente so volta para a saida depois de pegar todos os ouros.

## Resumo em uma frase

O projeto implementa um agente logico que explora um labirinto parcialmente desconhecido, usa percepcoes para atualizar sua memoria, escolhe acoes com regras Prolog, usa A* em Python para chegar aos alvos permitidos e tenta coletar todos os ouros antes de voltar para a saida.
