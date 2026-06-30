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
