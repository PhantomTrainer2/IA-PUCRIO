# INF1771 - Trabalho Final - Desafio dos Drones

Agente em Python para o servidor TCP/IP do trabalho final da disciplina INF1771.
O enunciado pede conexao via socket na porta `8888`, uso de uma tecnica de IA e
log em tela das acoes realizadas.

## Tecnica de IA usada

O agente combina:

- Maquina de estados: coleta item, combate, exploracao e desempate local.
- Representacao logica do conhecimento: celulas visitadas, seguras, bloqueadas,
  possiveis pocos, possiveis teleportes, possiveis inimigos e itens percebidos.
- Busca em largura ponderada por risco: a fronteira mais promissora e escolhida
  evitando celulas com brisa/flash quando existe alternativa segura.

Essa politica respeita a restricao de nao acessar o mapa real. O agente usa
apenas sensores e comandos disponibilizados pelo protocolo.

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

Os testes cobrem parser de observacoes, parser de posicao, atualizacao do mapa
mental e decisoes prioritarias do agente:

```bash
python -m unittest discover -s . -p "test_*.py"
```

Nao ha dependencias externas alem da biblioteca padrao do Python.

## Alterando taticas

Veja `HowToChange.md` para exemplos de como testar camping por tesouro, scout do
mapa, foco em combate, coletor ganancioso e modo conservador.
