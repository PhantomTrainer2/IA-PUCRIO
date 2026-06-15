#!/usr/bin/env python3
"""
INF1771 - Trabalho final: agente para o Desafio dos Drones.

O agente usa uma maquina de estados com mapa logico de risco e busca em largura
ponderada para explorar o labirinto sem acesso ao mapa real.
"""

from __future__ import annotations

import argparse
import enum
import heapq
import logging
import random
import re
import socket
import sys
import time
from dataclasses import dataclass, field
from typing import Iterable, Optional


DEFAULT_HOST = "atari.icad.puc-rio.br"
DEFAULT_PORT = 8888
MAP_WIDTH = 59
MAP_HEIGHT = 34

Position = tuple[int, int]

# Ajustes principais de tatica. O HowToChange.md explica como mexer neles.
RISK_BLOCKED = 10_000
RISK_PIT = 80
RISK_TELEPORT = 35
RISK_ENEMY = 8
RISK_UNKNOWN = 2
RISK_LOCAL_TURN_PENALTY = 5
RISK_VISIT_PENALTY_CAP = 5
EXPLORATION_RISK_BANDS = (0, 10, 45, 90)
SHOOT_COOLDOWN_STEPS = 1
ENEMY_SENSOR_RADIUS = 2
ENEMY_IN_SIGHT_WEIGHT = 5
PICK_WEAKLIGHT = True
PICK_GREENLIGHT = False


class Action(enum.Enum):
    FORWARD = ("w", "mover_para_frente")
    BACKWARD = ("s", "mover_para_tras")
    TURN_LEFT = ("a", "virar_a_esquerda")
    TURN_RIGHT = ("d", "virar_a_direita")
    GET_ITEM = ("t", "pegar_objeto")
    SHOOT = ("e", "atirar")
    OBSERVE = ("o", "observar")
    STATUS = ("g", "status_jogo")
    USER = ("q", "status_usuario")
    POSITION = ("p", "posicao")
    SCOREBOARD = ("u", "scoreboard")
    QUIT = ("quit", "sair")

    @property
    def wire(self) -> str:
        return self.value[0]

    @property
    def label(self) -> str:
        return self.value[1]


class Direction(enum.IntEnum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3

    @property
    def delta(self) -> Position:
        return {
            Direction.NORTH: (0, -1),
            Direction.EAST: (1, 0),
            Direction.SOUTH: (0, 1),
            Direction.WEST: (-1, 0),
        }[self]

    @property
    def label(self) -> str:
        return {
            Direction.NORTH: "N",
            Direction.EAST: "E",
            Direction.SOUTH: "S",
            Direction.WEST: "W",
        }[self]

    def left(self) -> "Direction":
        return Direction((int(self) - 1) % 4)

    def right(self) -> "Direction":
        return Direction((int(self) + 1) % 4)

    def back(self) -> "Direction":
        return Direction((int(self) + 2) % 4)

    @staticmethod
    def from_delta(delta: Position) -> "Direction":
        mapping = {
            (0, -1): Direction.NORTH,
            (1, 0): Direction.EAST,
            (0, 1): Direction.SOUTH,
            (-1, 0): Direction.WEST,
        }
        return mapping[delta]


def add_pos(a: Position, b: Position) -> Position:
    return a[0] + b[0], a[1] + b[1]


def manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


@dataclass
class Observation:
    raw: str
    tokens: set[str] = field(default_factory=set)
    enemy_distance: Optional[int] = None

    @classmethod
    def parse(cls, raw: str) -> "Observation":
        clean = raw.replace("\x00", " ")
        tokens: set[str] = set()
        enemy_distance: Optional[int] = None

        known = {
            "blocked",
            "steps",
            "breeze",
            "flash",
            "bluelight",
            "redlight",
            "greenlight",
            "weaklight",
            "damage",
            "hit",
        }

        parts = re.split(r"[;,\s]+", clean)
        for part in parts:
            token = part.strip().strip(".:").lower()
            if not token:
                continue
            token = token.replace("enemy#", "enemy#").replace("eneny#", "enemy#")
            if token.startswith("enemy") or token.startswith("eneny"):
                tokens.add("enemy")
                match = re.search(r"(\d+)", token)
                if match:
                    enemy_distance = int(match.group(1))
                continue
            if token in known:
                tokens.add(token)

        lower = clean.lower()
        for token in known:
            if token in lower:
                tokens.add(token)
        enemy_match = re.search(r"en[ea]my\s*#?\s*(\d+)", lower)
        if enemy_match:
            tokens.add("enemy")
            enemy_distance = int(enemy_match.group(1))

        return cls(raw=raw, tokens=tokens, enemy_distance=enemy_distance)

    def has(self, token: str) -> bool:
        return token.lower() in self.tokens

    @property
    def has_light(self) -> bool:
        return any(
            self.has(token)
            for token in ("bluelight", "redlight", "greenlight", "weaklight")
        )

    @property
    def item_kind(self) -> Optional[str]:
        if self.has("bluelight"):
            return "treasure"
        if self.has("redlight"):
            return "powerup"
        if self.has("greenlight"):
            return "poison"
        if self.has("weaklight"):
            return "unknown"
        return None

    def __bool__(self) -> bool:
        return bool(self.tokens)


@dataclass
class Cell:
    visited: bool = False
    blocked: bool = False
    safe: bool = False
    safe_from_pit: bool = False
    safe_from_teleport: bool = False
    possible_pit: int = 0
    possible_teleport: int = 0
    possible_enemy: int = 0
    item: Optional[str] = None
    visits: int = 0

    def risk(self) -> int:
        if self.blocked:
            return RISK_BLOCKED
        if self.visited:
            return 0
        pit = 0 if self.safe_from_pit else self.possible_pit * RISK_PIT
        teleport = (
            0 if self.safe_from_teleport else self.possible_teleport * RISK_TELEPORT
        )
        enemy = self.possible_enemy * RISK_ENEMY
        unknown = RISK_UNKNOWN if not self.safe else 0
        return pit + teleport + enemy + unknown


class KnowledgeMap:
    def __init__(
        self,
        width: int = MAP_WIDTH,
        height: int = MAP_HEIGHT,
        start: Position = (0, 0),
        heading: Direction = Direction.NORTH,
        bounded: bool = False,
    ) -> None:
        self.width = width
        self.height = height
        self.pos = start
        self.heading = heading
        self.bounded = bounded
        self.cells: dict[Position, Cell] = {}
        self.pending_action: Optional[Action] = None
        self.pending_from: Optional[Position] = None
        self.pending_to: Optional[Position] = None
        self.cell(start).safe = True
        self.cell(start).safe_from_pit = True
        self.cell(start).safe_from_teleport = True

    def cell(self, pos: Position) -> Cell:
        if pos not in self.cells:
            self.cells[pos] = Cell()
        return self.cells[pos]

    def in_bounds(self, pos: Position) -> bool:
        if not self.bounded:
            return True
        x, y = pos
        return 0 <= x < self.width and 0 <= y < self.height

    def neighbors(self, pos: Position) -> list[Position]:
        result = []
        for direction in Direction:
            nxt = add_pos(pos, direction.delta)
            if self.in_bounds(nxt):
                result.append(nxt)
        return result

    def cells_within_manhattan(self, pos: Position, radius: int) -> Iterable[Position]:
        for dx in range(-radius, radius + 1):
            for dy in range(-radius, radius + 1):
                if abs(dx) + abs(dy) == 0 or abs(dx) + abs(dy) > radius:
                    continue
                nxt = (pos[0] + dx, pos[1] + dy)
                if self.in_bounds(nxt):
                    yield nxt

    def mark_safe(self, pos: Position) -> None:
        cell = self.cell(pos)
        cell.safe = True
        cell.safe_from_pit = True
        cell.safe_from_teleport = True
        cell.possible_pit = 0
        cell.possible_teleport = 0

    def mark_wall(self, pos: Position) -> None:
        cell = self.cell(pos)
        cell.blocked = True
        cell.safe = False
        cell.item = None

    def prepare_action(self, action: Action) -> None:
        self.pending_action = action
        self.pending_from = self.pos
        self.pending_to = None
        if action == Action.FORWARD:
            self.pending_to = add_pos(self.pos, self.heading.delta)
        elif action == Action.BACKWARD:
            self.pending_to = add_pos(self.pos, self.heading.back().delta)
        elif action == Action.TURN_LEFT:
            self.heading = self.heading.left()
        elif action == Action.TURN_RIGHT:
            self.heading = self.heading.right()

    def resolve_action(self, obs: Observation, synced_pos: Optional[Position]) -> None:
        action = self.pending_action
        old_pos = self.pending_from
        target = self.pending_to

        if action in (Action.FORWARD, Action.BACKWARD) and old_pos and target:
            if obs.has("blocked"):
                self.pos = old_pos
                self.mark_wall(target)
            elif synced_pos is not None:
                self._infer_heading_from_move(action, old_pos, synced_pos)
                self.pos = synced_pos
                self.bounded = True
                self.mark_safe(synced_pos)
            else:
                self.pos = target
                self.mark_safe(target)
        elif synced_pos is not None:
            self.pos = synced_pos
            self.bounded = True

        if action == Action.GET_ITEM:
            self.cell(self.pos).item = None

        self.pending_action = None
        self.pending_from = None
        self.pending_to = None

    def _infer_heading_from_move(
        self, action: Action, old_pos: Position, new_pos: Position
    ) -> None:
        if manhattan(old_pos, new_pos) != 1:
            return

        dx = new_pos[0] - old_pos[0]
        dy = new_pos[1] - old_pos[1]
        moved = Direction.from_delta((dx, dy))
        if action == Action.FORWARD:
            self.heading = moved
        elif action == Action.BACKWARD:
            self.heading = moved.back()

    def update_from_observation(self, obs: Observation) -> None:
        current = self.cell(self.pos)
        current.visited = True
        current.visits += 1
        current.safe = True
        current.safe_from_pit = True
        current.safe_from_teleport = True
        current.possible_pit = 0
        current.possible_teleport = 0
        current.item = obs.item_kind

        adjacent = self.neighbors(self.pos)

        if obs.has("breeze"):
            for pos in adjacent:
                cell = self.cell(pos)
                if not cell.visited and not cell.safe_from_pit and not cell.blocked:
                    cell.possible_pit += 1
        else:
            for pos in adjacent:
                cell = self.cell(pos)
                cell.safe_from_pit = True
                cell.possible_pit = 0

        if obs.has("flash"):
            for pos in adjacent:
                cell = self.cell(pos)
                if (
                    not cell.visited
                    and not cell.safe_from_teleport
                    and not cell.blocked
                ):
                    cell.possible_teleport += 1
        else:
            for pos in adjacent:
                cell = self.cell(pos)
                cell.safe_from_teleport = True
                cell.possible_teleport = 0

        for pos in adjacent:
            cell = self.cell(pos)
            if cell.safe_from_pit and cell.safe_from_teleport and not cell.blocked:
                cell.safe = True

        if obs.has("steps"):
            for pos in self.cells_within_manhattan(self.pos, ENEMY_SENSOR_RADIUS):
                cell = self.cell(pos)
                if not cell.visited and not cell.blocked:
                    cell.possible_enemy += 1
        else:
            for pos in self.cells_within_manhattan(self.pos, ENEMY_SENSOR_RADIUS):
                self.cell(pos).possible_enemy = 0

        if obs.has("enemy") and obs.enemy_distance:
            enemy_pos = self.pos
            for _ in range(obs.enemy_distance):
                enemy_pos = add_pos(enemy_pos, self.heading.delta)
            if self.in_bounds(enemy_pos):
                self.cell(enemy_pos).possible_enemy += ENEMY_IN_SIGHT_WEIGHT

    def movement_risk(self, pos: Position) -> int:
        if not self.in_bounds(pos):
            return 10_000
        return self.cell(pos).risk()

    def passable_for_planning(self, pos: Position, max_risk: int) -> bool:
        return self.in_bounds(pos) and self.movement_risk(pos) <= max_risk

    def plan_to_frontier(self, max_risk: int) -> list[Position]:
        """Return a path from current position to a useful unvisited cell."""

        start = self.pos
        frontier: list[tuple[int, int, Position]] = [(0, 0, start)]
        came_from: dict[Position, Optional[Position]] = {start: None}
        best_cost: dict[Position, int] = {start: 0}
        counter = 0

        while frontier:
            cost, _, pos = heapq.heappop(frontier)
            if cost > best_cost[pos]:
                continue

            cell = self.cell(pos)
            if pos != start and not cell.visited and self.passable_for_planning(
                pos, max_risk
            ):
                return self._reconstruct_path(came_from, pos)

            if pos != start and not (cell.visited or cell.safe):
                continue

            for nxt in self.neighbors(pos):
                if not self.passable_for_planning(nxt, max_risk):
                    continue
                nxt_cell = self.cell(nxt)
                step_cost = 1 + nxt_cell.risk() + min(
                    nxt_cell.visits, RISK_VISIT_PENALTY_CAP
                )
                new_cost = cost + step_cost
                if new_cost < best_cost.get(nxt, 10_000_000):
                    best_cost[nxt] = new_cost
                    came_from[nxt] = pos
                    counter += 1
                    priority = new_cost + (0 if not nxt_cell.visited else 3)
                    heapq.heappush(frontier, (priority, counter, nxt))

        return []

    def _reconstruct_path(
        self, came_from: dict[Position, Optional[Position]], goal: Position
    ) -> list[Position]:
        path = [goal]
        while came_from[path[-1]] is not None:
            parent = came_from[path[-1]]
            if parent is None:
                break
            path.append(parent)
        path.reverse()
        return path

    def action_for_path(self, path: list[Position]) -> Optional[Action]:
        if len(path) < 2:
            return None

        nxt = path[1]
        dx = nxt[0] - self.pos[0]
        dy = nxt[1] - self.pos[1]
        desired = Direction.from_delta((dx, dy))

        if desired == self.heading:
            return Action.FORWARD
        if desired == self.heading.back():
            return Action.BACKWARD
        if desired == self.heading.left():
            return Action.TURN_LEFT
        return Action.TURN_RIGHT

    def least_bad_local_action(self) -> Action:
        candidates = [
            (self.heading, Action.FORWARD),
            (self.heading.back(), Action.BACKWARD),
            (self.heading.left(), Action.TURN_LEFT),
            (self.heading.right(), Action.TURN_RIGHT),
        ]
        scored: list[tuple[int, float, Action]] = []
        for direction, action in candidates:
            target = add_pos(self.pos, direction.delta)
            risk = self.movement_risk(target)
            visits = self.cell(target).visits if self.in_bounds(target) else 999
            if action in (Action.TURN_LEFT, Action.TURN_RIGHT):
                risk += RISK_LOCAL_TURN_PENALTY
            scored.append((risk + visits, random.random(), action))
        scored.sort(key=lambda item: (item[0], item[1]))
        return scored[0][2]

    def known_summary(self) -> str:
        visited = sum(1 for cell in self.cells.values() if cell.visited)
        safe = sum(1 for cell in self.cells.values() if cell.safe and not cell.visited)
        walls = sum(1 for cell in self.cells.values() if cell.blocked)
        danger = sum(
            1
            for cell in self.cells.values()
            if not cell.blocked
            and (cell.possible_pit or cell.possible_teleport or cell.possible_enemy)
        )
        return f"visitadas={visited} seguras={safe} bloqueadas={walls} risco={danger}"


class DroneBrain:
    """State machine that chooses actions from observations and the knowledge map."""

    def __init__(self, world: KnowledgeMap) -> None:
        self.world = world
        self.last_shot_step = -999
        self.step_count = 0
        self.last_reason = "inicio"

    def decide(self, obs: Observation) -> Action:
        self.step_count += 1

        if (
            obs.has("enemy")
            and self.step_count - self.last_shot_step >= SHOOT_COOLDOWN_STEPS
        ):
            self.last_shot_step = self.step_count
            self.last_reason = "combate: inimigo na mira"
            return Action.SHOOT

        if self.should_pick_item(obs):
            self.last_reason = f"coleta: {obs.item_kind}"
            return Action.GET_ITEM

        for max_risk in EXPLORATION_RISK_BANDS:
            path = self.world.plan_to_frontier(max_risk=max_risk)
            action = self.world.action_for_path(path)
            if action is not None:
                self.last_reason = f"exploracao: risco <= {max_risk}"
                return action

        self.last_reason = "fallback: menor risco local"
        return self.world.least_bad_local_action()

    def should_pick_item(self, obs: Observation) -> bool:
        if not obs.has_light:
            return False
        if obs.item_kind == "poison":
            return PICK_GREENLIGHT
        if obs.item_kind == "unknown":
            return PICK_WEAKLIGHT
        return obs.item_kind in {"treasure", "powerup"}


class DroneProtocol:
    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 1.5,
        line_ending: str = "\n",
    ) -> None:
        self.host = host
        self.port = port
        self.timeout = timeout
        self.line_ending = line_ending
        self.sock: Optional[socket.socket] = None

    def connect(self) -> None:
        self.sock = socket.create_connection((self.host, self.port), timeout=self.timeout)
        self.sock.settimeout(self.timeout)

    def close(self) -> None:
        if self.sock is None:
            return
        try:
            self.request(Action.QUIT.wire)
        except OSError:
            pass
        try:
            self.sock.close()
        finally:
            self.sock = None

    def request(self, command: str, *params: object) -> str:
        if self.sock is None:
            raise RuntimeError("socket nao conectado")

        payload = self._format_command(command, params)
        self.sock.sendall(payload.encode("utf-8", errors="replace"))
        return self._recv_response()

    def _format_command(self, command: str, params: tuple[object, ...]) -> str:
        if params:
            text = ";".join([command, *[str(param) for param in params]])
        else:
            text = command
        return text + self.line_ending

    def _recv_response(self) -> str:
        assert self.sock is not None
        chunks: list[bytes] = []
        while True:
            try:
                chunk = self.sock.recv(4096)
            except socket.timeout:
                break
            if not chunk:
                break
            chunks.append(chunk)
            if b"\n" in chunk:
                break
        return b"".join(chunks).decode("utf-8", errors="replace").strip()


def parse_position(raw: str) -> Optional[Position]:
    lower = raw.lower()
    labeled = re.search(
        r"x\s*[:=]\s*(-?\d+).*?y\s*[:=]\s*(-?\d+)", lower, flags=re.DOTALL
    )
    if labeled:
        return int(labeled.group(1)), int(labeled.group(2))

    parens = re.search(r"\(\s*(-?\d+)\s*[,;]\s*(-?\d+)\s*\)", raw)
    if parens:
        return int(parens.group(1)), int(parens.group(2))

    ints = [int(value) for value in re.findall(r"-?\d+", raw)]
    if len(ints) >= 2:
        return ints[0], ints[1]
    return None


def parse_game_state(raw: str) -> str:
    lower = raw.lower()
    if "gameover" in lower or "game over" in lower:
        return "gameover"
    if "ready" in lower:
        return "ready"
    if "game" in lower:
        return "game"
    return "unknown"


class DroneAgent:
    def __init__(self, client: DroneProtocol, name: str, color: tuple[int, int, int]) -> None:
        self.client = client
        self.name = name
        self.color = color
        self.world = KnowledgeMap()
        self.brain = DroneBrain(self.world)
        self.logger = logging.getLogger("agent")

    def setup(self) -> None:
        self.logger.info("Conectado. Configurando nome e cor.")
        self._safe_request("name", self.name)
        self._safe_request("color", *self.color)
        raw_pos = self._safe_request(Action.POSITION.wire)
        pos = parse_position(raw_pos)
        if pos is not None:
            self.world.pos = pos
            self.world.bounded = True
            self.world.mark_safe(pos)
            self.logger.info("Posicao inicial sincronizada: %s", pos)
        else:
            self.logger.info("Servidor nao informou posicao inicial; usando origem local.")

    def play(self, max_steps: Optional[int], delay: float) -> None:
        step = 0
        while max_steps is None or step < max_steps:
            state = parse_game_state(self._safe_request(Action.STATUS.wire))
            if state in {"ready", "gameover"}:
                self.logger.info("Estado %s: aguardando comandos do jogo.", state)
                time.sleep(max(delay, 1.0))
                continue

            raw_obs = self._safe_request(Action.OBSERVE.wire)
            obs = Observation.parse(raw_obs)
            self.world.update_from_observation(obs)

            action = self.brain.decide(obs)
            self.world.prepare_action(action)
            raw_action = self._safe_request(action.wire)
            raw_after = self._safe_request(Action.OBSERVE.wire)
            combined_obs = Observation.parse(";".join([raw_action, raw_after]))
            synced_pos = parse_position(self._safe_request(Action.POSITION.wire))
            self.world.resolve_action(combined_obs, synced_pos)
            self.world.update_from_observation(combined_obs)

            step += 1
            self.logger.info(
                "passo=%03d acao=%s motivo=%s pos=%s dir=%s obs=%s mapa=[%s]",
                step,
                action.label,
                self.brain.last_reason,
                self.world.pos,
                self.world.heading.label,
                sorted(combined_obs.tokens) or "-",
                self.world.known_summary(),
            )
            time.sleep(delay)

    def _safe_request(self, command: str, *params: object) -> str:
        try:
            response = self.client.request(command, *params)
            if response:
                self.logger.debug("servidor %s -> %s", command, response)
            return response
        except (OSError, RuntimeError) as exc:
            self.logger.warning("falha no comando %s: %s", command, exc)
            return ""


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Agente INF1771 - Desafio dos Drones")
    parser.add_argument("--host", default=DEFAULT_HOST, help="host do servidor")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="porta TCP")
    parser.add_argument("--name", default="BrenoIA", help="nome do agente")
    parser.add_argument(
        "--color",
        type=int,
        nargs=3,
        metavar=("R", "G", "B"),
        default=(0, 180, 255),
        help="cor RGB do agente",
    )
    parser.add_argument("--timeout", type=float, default=1.5, help="timeout do socket")
    parser.add_argument("--delay", type=float, default=0.05, help="pausa entre acoes")
    parser.add_argument("--max-steps", type=int, default=None, help="limite local de passos")
    parser.add_argument(
        "--crlf",
        action="store_true",
        help="usa CRLF em vez de LF ao enviar comandos",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="log detalhado")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    configure_logging(args.verbose)

    line_ending = "\r\n" if args.crlf else "\n"
    client = DroneProtocol(
        host=args.host,
        port=args.port,
        timeout=args.timeout,
        line_ending=line_ending,
    )
    agent = DroneAgent(client, name=args.name, color=tuple(args.color))

    try:
        client.connect()
        agent.setup()
        agent.play(max_steps=args.max_steps, delay=args.delay)
    except KeyboardInterrupt:
        logging.getLogger("agent").info("Interrompido pelo usuario.")
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
