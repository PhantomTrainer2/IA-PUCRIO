# HowToRun - Como executar o agente

Passo a passo para rodar o agente do Desafio dos Drones contra o servidor.

## 1. Pre-requisitos

- Python 3.10 ou superior.
- Conexao com a internet (o servidor fica em `atari.icad.puc-rio.br`).
- O agente so usa a biblioteca padrao do Python. **Nao precisa instalar nada.**

Confirme a versao do Python:

```bash
python --version
```

## 2. Arquivos do projeto

- `agent.py` - programa principal (conecta, decide e age).
- `test_agent.py` - testes automaticos.
- `README.md` - visao geral e tecnica de IA.
- `HowToChange.md` - como ajustar taticas.
- `HowToRun.md` - este arquivo.

## 3. Validar antes de executar (opcional, mas recomendado)

Rode os testes para garantir que nada quebrou:

```bash
python -B -m unittest discover -s . -p "test_*.py"
```

Esperado: `OK` com 25 testes passando.

## 4. Executar contra o servidor

### 4.1. Modo padrao (servidor oficial)

Na pasta `trab4`:

```bash
python agent.py
```

Por padrao o agente ja conecta em:

- host: `atari.icad.puc-rio.br`
- porta: `8888`
- nome: `BrenoIA`
- cor: `0 180 255` (ciano)

### 4.2. Com log detalhado

Use `--verbose` (ou `-v`) para ver as respostas brutas do servidor:

```bash
python agent.py --verbose
```

### 4.3. Com limite de passos (bom para testar rapido)

Roda 200 passos e para:

```bash
python agent.py --max-steps 200
```

## 5. Opcoes de linha de comando

| Opcao | Default |Descricao |
|-------|---------|----------|
| `--host HOST` | `atari.icad.puc-rio.br` | Host do servidor |
| `--port PORT` | `8888` | Porta TCP |
| `--name NAME` | `BrenoIA` | Nome do agente no jogo |
| `--color R G B` | `0 180 255` | Cor RGB (0-255 cada) |
| `--timeout SEG` | `1.5` | Timeout do socket em segundos |
| `--delay SEG` | `0.05` | Pausa entre acoes |
| `--max-steps N` | (ilimitado) | Limite local de passos |
| `--crlf` | desligado | Envia comandos com `\r\n` em vez de `\n` |
| `-v`, `--verbose` | desligado | Log detalhado |

Veja todas as opcoes a qualquer momento:

```bash
python agent.py --help
```

## 6. Exemplos completos

Trocar o nome e a cor:

```bash
python agent.py --name MeuDrone --color 255 0 0
```

Testar contra outro servidor/devkit local na mesma maquina:

```bash
python agent.py --host 127.0.0.1 --port 8888 --max-steps 100 --verbose
```

Alguns devkits exigem comandos terminados com `\r\n`. Se o servidor nao
responder corretamente, tente:

```bash
python agent.py --crlf --verbose
```

## 7. Como ler o log

Cada linha mostra o que aconteceu num passo:

```text
12:30:01 INFO passo=007 acao=mover_para_frente motivo=exploracao: risco <= 10 pos=(10, 7) dir=E energia=100 obs=['breeze'] mapa=[visitadas=7 seguras=12 bloqueadas=1 risco=0]
```

- `passo` - numero do turno.
- `acao` - o que o agente fez (`mover_para_frente`, `virar_a_esquerda`,
  `pegar_objeto`, `atirar`, `mover_para_tras`, etc.).
- `motivo` - por que decidiu isso:
  - `defesa: fugindo de dano` - levou dano e esta recuando.
  - `combate: inimigo na mira` - detectou inimigo e atirou.
  - `coleta: treasure` / `coleta: powerup` - pegou um item.
  - `cacada: treasure avistado` - indo ate um tesouro memorizado.
  - `exploracao: risco <= N` - explorando a fronteira mais barata.
  - `fallback: menor risco local` - sem rota planejada, escolhe o menor risco.
- `pos` - posicao atual `(x, y)`.
- `dir` - direcao que olha (`N`, `E`, `S`, `W`).
- `energia` - energia conhecida (lida periodicamente via `q`).
- `obs` - sensores do turno (`breeze`, `flash`, `steps`, `enemy`, `damage`,
  `hit`, `blueLight`, `redLight`, `greenLight`, `weaklight`, `blocked`).
- `mapa` - resumo do mapa mental.

## 8. Interpretar os sensores

| Sensor | O que significa |
|--------|-----------------|
| `breeze` | Buraco/poco adjacente (1 passo). Cair = -1000 e fim de jogo. |
| `flash` | Teletransporte adjacente (1 passo). Pisar = posicao aleatoria. |
| `steps` | Inimigo a ate 2 passos (Manhattan). |
| `enemy#NN` | Inimigo a `NN` passos na direcao que olha (ate 10). |
| `blueLight` | Tesouro na celula atual. |
| `redLight` | Powerup na celula atual. |
| `weakLight` | Item indefinido (pode ser tesouro, powerup ou outro). |
| `greenLight` | Veneno (nao aparece nos mapas do trabalho). |
| `blocked` | Ultimo movimento nao ocorreu (parede/obstaculo). |
| `damage` | O agente levou um tiro. |
| `hit` | O agente acertou um tiro num inimigo. |

## 9. Encerrar

- `Ctrl+C` desconecta o agente (envia `quit` e fecha o socket).
- Com `--max-steps`, ele para sozinho ao atingir o limite.

## 10. Troubleshooting

- **O agente conecta mas nada acontece / fica em "Estado ready"**: o servidor
  esta na fase de preparacao (30s) ou entre partidas. E normal; ele aguarda.
- **Nenhuma resposta do servidor / timeout**: confira host, porta e se a rede
  permite conexao TCP na porta 8888. Tente `--timeout 3` e `--crlf`.
- **A posicao aparece como `(0, 0)` / `dir=N` sempre**: o servidor nao informou
  a posicao inicial; o agente usa a origem local e se corrige assim que o
  primeiro movimento e sincronizado.
- **Muita saida na tela**: rode sem `--verbose`.

## 11. Como Visualizar o Jogo Graficamente

O código do agente (`agent.py`) roda via terminal e não possui interface gráfica própria (conforme as regras do trabalho). No entanto, você pode assistir à partida do seu agente rodando no mapa visual através do aplicativo do **GameServer** fornecido pelo professor.

Para abrir o visualizador e acompanhar o seu agente:

1. Vá até a pasta `Server Trab4` (onde estão os arquivos compilados `.pyc` do servidor).
2. Dê um duplo clique no arquivo **`visualizar.bat`** (ou execute `py -3.11 main.pyc` se precisou instalar o Python 3.11).
   - *Isso abrirá a janela gráfica do "INF1771 GameServer" que atua como um espectador da partida.*
3. Note que o visualizador se conecta automaticamente ao servidor remoto oficial da PUC (`atari.icad.puc-rio.br`).
4. **Com o visualizador já aberto**, abra outro terminal na pasta do seu agente (`trab4`) e execute-o **normalmente**, sem alterar o host:
   ```bash
   python agent.py
   ```
5. Pronto! O seu agente irá se conectar ao servidor oficial e, na janela do visualizador, você verá o seu drone (representado pela cor que você escolheu) surgir e começar a explorar o labirinto.
