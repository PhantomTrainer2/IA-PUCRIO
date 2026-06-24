# HowToChange - Como testar taticas diferentes

Este arquivo mostra onde alterar manualmente o agente sem quebrar as
restricoes do trabalho.

## Antes de mexer

Mantenha estes pontos do PDF:

- O agente deve continuar usando Socket TCP/IP com o servidor na porta `8888`.
- O agente nao pode acessar o mapa real do labirinto.
- O agente deve decidir usando uma tecnica de IA. Hoje ele usa maquina de
  estados, mapa logico de risco e busca ponderada.
- O agente deve exibir log em tela das acoes realizadas.
- Os comandos validos continuam sendo `w`, `s`, `a`, `d`, `t`, `e`, `o`,
  `g`, `q`, `p`, `u`, `name`, `say`, `color` e `quit`.

Depois de qualquer alteracao, rode:

```bash
python -B -m unittest discover -s . -p "test_*.py"
```

Para testar contra o servidor com mais log:

```bash
python agent.py --verbose --max-steps 200
```

## Mapa rapido do codigo

Arquivo principal: `agent.py`.

- Bloco de constantes no topo: pesos de risco, bloqueio duro de poco/teleporte,
  cooldown de tiro, reacao a dano, limite de energia e tolerancia a perigo.
- `Observation.parse`: interpreta sensores recebidos do servidor.
- `KnowledgeMap.update_from_observation`: atualiza o mapa mental com breeze,
  flash, steps, enemy e luzes. Tem o parametro `persist` (volatil x permanente).
- `KnowledgeMap.is_hard_avoided`: bloqueio absoluto de celulas suspeitas de
  poco/teleporte (cair encerra a partida).
- `KnowledgeMap.plan_to_frontier`: escolhe uma fronteira para explorar.
- `KnowledgeMap.plan_to_target`: busca A* dirigida a um tesouro memorizado.
- `DroneBrain.decide`: ordem de prioridade da tatica.
- `DroneBrain.observe_combat_signals`: atualiza contadores de combate (dano,
  tiros sem acerto) a cada observacao.
- `DroneBrain.should_pick_item`: decide se deve pegar redLight, blueLight,
  weaklight ou greenLight.
- `parse_energy`: le a energia do user status (comando `q`).
- `DroneAgent.play`: ciclo principal de observar, decidir, agir, sincronizar e
  registrar log.

## Ajustes simples por constantes

No topo do `agent.py`, altere estes valores:

```python
RISK_PIT = 80
RISK_TELEPORT = 35
RISK_ENEMY = 8
RISK_UNKNOWN = 2
EXPLORATION_RISK_BANDS = (0, 10, 20)
SHOOT_COOLDOWN_STEPS = 1
PICK_WEAKLIGHT = True
PICK_GREENLIGHT = False
HARD_AVOID_PIT = True
HARD_AVOID_TELEPORT = True
REACT_TO_DAMAGE = True
DAMAGE_FLEE_TURNS = 2
MAX_SHOTS_WITHOUT_HIT = 3
LOW_ENERGY_THRESHOLD = 35
TREASURE_MEMORY_RADIUS = 6
ENERGY_CHECK_EVERY = 5
```

Efeitos comuns:

- Mais cauteloso: aumente `RISK_PIT`, `RISK_TELEPORT` e remova os maiores
  valores de `EXPLORATION_RISK_BANDS`.
- Mais agressivo: diminua `RISK_PIT`, `RISK_TELEPORT` e aumente
  `EXPLORATION_RISK_BANDS`.
- Mais focado em combate: diminua `RISK_ENEMY` e `SHOOT_COOLDOWN_STEPS`.
- Mais conservador com itens incertos: mude `PICK_WEAKLIGHT = False`.
- Nunca pegar veneno: deixe `PICK_GREENLIGHT = False`.
- Permitir arriscar possivel poco/teleporte (NAO recomendado, cair encerra a
  partida): mude `HARD_AVOID_PIT = False` / `HARD_AVOID_TELEPORT = False`.
- Desligar a fuga apos dano: mude `REACT_TO_DAMAGE = False`.
- Cacar tesouros mais longe: aumente `TREASURE_MEMORY_RADIUS`.

IMPORTANTE: as bandas de `EXPLORATION_RISK_BANDS` agora controlam apenas risco
de incerteza/inimigo. Risco de poco/teleporte e tratado como bloqueio absoluto
por `HARD_AVOID_*`, porque cair nesses encerra a partida (PDF pag.3). Por isso
as bandas ficaram menores que o risco de poco.

## Como mudar a prioridade geral

A ordem principal fica em `DroneBrain.decide`.

Padrao atual:

1. Foge (re) se levou dano recentemente e nao tem inimigo na mira.
2. Atira se ha inimigo na mira, respeitando cooldown, limite de tiros sem
   acerto e energia suficiente.
3. Pega item bom ou incerto da celula atual.
4. Caca o tesouro/powerup memorizado mais proximo (busca dirigida).
5. Explora fronteira segura ou de risco tolerado.
6. Usa menor risco local como fallback.

Para testar outra tatica, reordene os blocos desse metodo. Evite alterar o
protocolo em `DroneProtocol`, porque ele e a parte que conversa com o servidor.

## Tatica 1: ficar esperando ouro spawnar

Nao existe comando explicito de "esperar" no PDF. O mais proximo e observar,
que mantem o agente parado e atualiza sensores.

Em `DroneBrain.decide`, coloque este bloco logo depois de `self.step_count += 1`:

```python
if obs.item_kind == "treasure":
    self.last_reason = "camp: ouro encontrado"
    return Action.GET_ITEM

if self.step_count % 8 != 0:
    self.last_reason = "camp: observando spawn"
    return Action.OBSERVE
```

Com isso, o agente fica observando por 7 turnos e so executa a politica normal
no oitavo. Para fazer ele girar e escanear inimigos enquanto espera, troque
`Action.OBSERVE` por `Action.TURN_RIGHT`.

Risco: cada acao pode custar ponto no servidor, entao camping pode perder score
se nenhum tesouro aparecer perto.

## Tatica 2: fazer scout do mapa ao maximo

Objetivo: visitar muitas celulas, evitando ficar preso em loops.

No topo do arquivo, tente:

```python
RISK_VISIT_PENALTY_CAP = 20
EXPLORATION_RISK_BANDS = (0, 10, 45, 90, 160)
```

Depois, em `DroneBrain.decide`, deixe coleta depois da exploracao se voce quiser
mapear antes de pegar itens:

```python
for max_risk in EXPLORATION_RISK_BANDS:
    path = self.world.plan_to_frontier(max_risk=max_risk)
    action = self.world.action_for_path(path)
    if action is not None:
        self.last_reason = f"scout: risco <= {max_risk}"
        return action

if self.should_pick_item(obs):
    self.last_reason = f"coleta tardia: {obs.item_kind}"
    return Action.GET_ITEM
```

Risco: explorar areas com `breeze` ou `flash` aumenta chance de cair em poco ou
ser teletransportado. (Nota: com `HARD_AVOID_PIT`/`HARD_AVOID_TELEPORT` ligados,
o agente nunca pisa em celulas suspeitas; bandas altas em
`EXPLORATION_RISK_BANDS` so aumentam a tolerancia a celulas incertas, nao a
pocos. Para arriscar poco mesmo, desligue os `HARD_AVOID_*`.)

## Tatica 3: focar em atirar em players

Objetivo: procurar combate e aproveitar o sensor `enemy#xx`.

No topo do arquivo:

```python
RISK_ENEMY = 0
SHOOT_COOLDOWN_STEPS = 0
EXPLORATION_RISK_BANDS = (0, 10, 45, 90, 160)
```

Em `DroneBrain.decide`, coloque antes da exploracao:

```python
if obs.has("enemy"):
    self.last_shot_step = self.step_count
    self.last_reason = "hunter: inimigo na mira"
    return Action.SHOOT

if obs.has("steps"):
    self.last_reason = "hunter: procurando inimigo pelos passos"
    return Action.TURN_RIGHT
```

Isso faz o agente girar quando ouve passos e atirar quando encontra inimigo na
mira. Se ele girar demais, mude para:

```python
if obs.has("steps") and self.step_count % 3 != 0:
    self.last_reason = "hunter: varredura curta"
    return Action.TURN_RIGHT
```

Risco: combate custa energia se outros agentes atirarem primeiro, e `steps` nao
informa a posicao exata. (Nota: o exemplo acima substitui o bloco de combate
padrao, que por seguranca so atira com energia acima de `LOW_ENERGY_THRESHOLD` e
ate `MAX_SHOTS_WITHOUT_HIT` tiros sem `hit`. Ao usar a tatica hunter, voce abre
mao dessa protecao e pode gastar -10 por tiro no vazio.)

## Tatica 4: coletor ganancioso

Objetivo: pegar qualquer item util assim que aparecer e aceitar mais risco para
achar tesouros.

Use:

```python
PICK_WEAKLIGHT = True
PICK_GREENLIGHT = False
RISK_PIT = 45
RISK_TELEPORT = 20
EXPLORATION_RISK_BANDS = (0, 10, 45, 90, 140)
```

Mantenha o bloco de coleta antes da exploracao em `DroneBrain.decide`.

## Tatica 5: sobrevivente conservador

Objetivo: evitar morte por poco, parede e teletransporte.

Use:

```python
RISK_PIT = 200
RISK_TELEPORT = 120
RISK_ENEMY = 30
EXPLORATION_RISK_BANDS = (0, 10)
PICK_WEAKLIGHT = False
```

Essa versao explora menos, mas tende a morrer menos.

## Como confirmar qual tatica esta rodando

O log mostra o motivo da decisao:

```text
passo=012 acao=mover_para_frente motivo=exploracao: risco <= 0 ...
```

Ao criar uma tatica nova, sempre atualize `self.last_reason` no bloco novo. Isso
facilita comparar partidas.

## Como adicionar um modo novo sem apagar o padrao

Crie um novo metodo em `DroneBrain`, por exemplo:

```python
def decide_hunter(self, obs: Observation) -> Action:
    if obs.has("enemy"):
        self.last_reason = "hunter: tiro"
        return Action.SHOOT
    if obs.has("steps"):
        self.last_reason = "hunter: giro"
        return Action.TURN_RIGHT

    for max_risk in EXPLORATION_RISK_BANDS:
        path = self.world.plan_to_frontier(max_risk=max_risk)
        action = self.world.action_for_path(path)
        if action is not None:
            self.last_reason = f"hunter: exploracao risco <= {max_risk}"
            return action

    self.last_reason = "hunter: fallback local"
    return self.world.least_bad_local_action()
```

Depois, em `DroneBrain.decide`, chame esse metodo quando quiser testar. Para uma
solucao mais organizada, da para adicionar um argumento `--strategy` no
`parse_args` e passar o valor ate o `DroneBrain`, mas para testes rapidos a
troca manual no metodo `decide` e suficiente.

## Checklist antes de entregar

- `python -B -m unittest discover -s . -p "test_*.py"` passa.
- `python agent.py --help` abre sem erro.
- O log continua exibindo acao, motivo, posicao, direcao, observacoes e resumo
  do mapa mental.
- Nenhuma tatica usa mapa real ou informacao externa ao protocolo.
- O agente ainda conecta no host/porta do enunciado ou nos parametros passados
  via linha de comando.
