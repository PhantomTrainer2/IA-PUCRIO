# INF1771 - Trabalho Final - Desafio dos Drones

Agente em Python para o servidor TCP/IP do trabalho final da disciplina INF1771.
O enunciado pede conexao via socket na porta `8888`, uso de uma tecnica de IA e
log em tela das acoes realizadas.

## Tecnica de IA usada

O agente combina:

- Maquina de estados: defesa (fuga de dano), combate, coleta, caca de tesouro,
  exploracao e desempate local.
- Representacao logica do conhecimento: celulas visitadas, seguras, bloqueadas,
  possiveis pocos, possiveis teleportes, possiveis inimigos e itens percebidos.
- Busca ponderada por risco: a fronteira mais promissora e escolhida tratando
  celulas com brisa/flash como bloqueio absoluto (poco encerra a partida, teleporte e imprevisivel).
- Busca dirigida (A*) a tesouros/powerups memorizados e ainda nao coletados.

Essa politica respeita a restricao de nao acessar o mapa real. O agente usa
apenas sensores e comandos disponibilizados pelo protocolo.

Comportamentos adicionais:

- Reage ao sensor `damage`: recua para sair da linha de tiro.
- Limita tiros seguidos sem `hit` para nao gastar pontos atirando no vazio.
- Le energia (comando `q`) periodicamente e fica defensivo quando baixa,
  priorizando powerups.
- Detecta teletransporte (salto grande de posicao) e descarta tesouros
  memorizados que ficaram distantes.

Quando o servidor informa a posicao com `p`, o agente sincroniza a coordenada
real. Se um movimento bem-sucedido muda a coordenada em uma casa, a orientacao
tambem e inferida automaticamente, evitando depender de uma direcao inicial fixa.

## Como executar

```bash
python agent.py --host atari.icad.puc-rio.br --port 8888 --name BrenoIA --color 0 180 255
```

Opcoes uteis:

```bash
python agent.py --max-steps 200
python agent.py --verbose
python agent.py --crlf
```

Use `--crlf` se o servidor/devkit exigir comandos terminados por `\r\n`.

## Comandos do protocolo usados

- `w`, `s`, `a`, `d`: movimentacao e rotacao.
- `t`: pegar item quando houver `redLight`, `blueLight` ou `weaklight`.
- `e`: atirar quando o sensor `enemy#xx` indicar inimigo na mira.
- `o`: observar sensores.
- `g`, `p`: sincronizar estado do jogo e posicao.
- `name`, `color`: configurar o agente ao conectar.
- `quit`: desconectar ao finalizar.

## Validacao local

Os testes cobrem parser de observacoes, parser de posicao/energia, atualizacao
do mapa mental, decisoes prioritarias do agente e regressao dos bugs corrigidos
(acumulo de risco, bloqueio de poco/teleporte, fuga por dano, caca de tesouro,
deteccao de teleporte). Sao 25 testes no total:

```bash
python -m unittest discover -s . -p "test_*.py"
```

Nao ha dependencias externas alem da biblioteca padrao do Python.

## Como executar

Veja `HowToRun.md` para o passo a passo completo (pre-requisitos, opcoes de
linha de comando, leitura do log e troubleshooting). Resumo:

```bash
python agent.py                  # servidor oficial (atari.icad.puc-rio.br:8888)
python agent.py --verbose --max-steps 200
```

## Alterando taticas

Veja `HowToChange.md` para exemplos de como testar camping por tesouro, scout do
mapa, foco em combate, coletor ganancioso e modo conservador.

## Fluxo de Pensamento / Heurística do Agente

O agente atual opera com uma **heurística balanceada de exploração e coleta segura**, com mecanismos avançados de autodefesa. O seu fluxo de decisão (avaliado a cada passo) segue a seguinte ordem estrita de prioridades:

1. **Defesa e Sobrevivência (Fuga)**: Se o agente sofreu dano recentemente e não está vendo quem atirou (inimigo fora da mira), ele aborta qualquer plano e prioriza sair da linha de tiro (geralmente movendo-se de ré ou rotacionando).
2. **Combate Estratégico**: Se um inimigo é detectado na linha de tiro (sensor de mira), o agente prioriza atacar. No entanto, ele evita combates desnecessários se a sua energia estiver baixa (priorizando fugir/buscar power-ups) ou se já atirou várias vezes seguidas sem confirmar acerto (evitando desperdiçar pontos atirando no vazio).
3. **Coleta de Itens Imediata**: Se o agente pisa em uma célula com item brilhante útil (tesouro, power-up ou luz fraca desconhecida), ele executa a ação de coleta. Luz verde (veneno) é ignorada.
4. **Caça Direcionada (Busca de Tesouros/Itens)**: O agente possui uma memória espacial. Se ele avistar luzes de tesouros ou power-ups próximos durante a exploração, ele traça uma rota segura (A*) até lá para coletá-los. Se a energia estiver crítica (abaixo do limiar), ele inverte a prioridade e vai caçar os power-ups primeiro.
5. **Scout do Mapa (Exploração por Fronteiras)**: Se não há ameaças imediatas nem tesouros na memória, o agente tenta mapear o labirinto de forma otimizada. Ele usa uma busca em largura para a "fronteira" (célula desconhecida) mais próxima, navegando apenas por caminhos seguros e contornando estritamente qualquer evidência de poços ou teletransportes.
6. **Fallback de Sobrevivência**: Se o agente estiver totalmente encurralado (todas as frentes distantes bloqueadas por alto risco), ele avalia apenas o entorno imediato e escolhe a ação de "menor dano possível" para se manter vivo ou tentar se desvencilhar do bloqueio.
