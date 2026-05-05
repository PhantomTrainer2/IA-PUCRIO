# INF1771_Wumpus_Prolog_Python

Warning - swipl module is currently compatible with swi-prolog 8.4.3 download here  https://www.swi-prolog.org/download/stable/bin/swipl-8.4.3-1.x64.exe.envelope

## Execucao

Por padrao, o programa gera um labirinto aleatorio 12x12 com as quantidades exigidas no enunciado:

- 8 pocos/obstaculos
- 3 ouros
- 3 powerups de energia
- 4 inimigos de teletransporte
- 2 inimigos de dano 50
- 2 inimigos de dano 20

```bash
python gmap.py
```

Tambem e possivel carregar manualmente um mapa pronto:

```bash
python gmap.py mapa_facil.pl
python gmap.py mapa_medio.pl
python gmap.py mapa_dificil.pl
```

A tecla `M` alterna apenas a visualizacao: com `debug = True` mostra o mapa real completo; com `debug = False` mostra a interpretacao do agente. Isso nao altera a tomada de decisao.

Mapa Fácil
![Mapa Fácil](mapa-facil.png)

Mapa Médio
![Mapa Médio](mapa-medio.png)

Mapa Difícil
![Mapa Difícil](mapa-dificil.png)
