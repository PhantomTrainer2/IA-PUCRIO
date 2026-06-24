import unittest

from agent import (
    EXPLORATION_RISK_BANDS,
    RISK_PIT,
    Action,
    Direction,
    DroneBrain,
    KnowledgeMap,
    Observation,
    parse_energy,
    parse_game_state,
    parse_position,
)


class ObservationTests(unittest.TestCase):
    def test_parse_mixed_observations(self):
        obs = Observation.parse("blocked;breeze, enemy#04 damage hit blueLight")

        self.assertTrue(obs.has("blocked"))
        self.assertTrue(obs.has("breeze"))
        self.assertTrue(obs.has("enemy"))
        self.assertTrue(obs.has("damage"))
        self.assertTrue(obs.has("hit"))
        self.assertEqual(obs.enemy_distance, 4)
        self.assertEqual(obs.item_kind, "treasure")

    def test_parse_position_variants(self):
        self.assertEqual(parse_position("(12, 7)"), (12, 7))
        self.assertEqual(parse_position("x=3;y=20;energia=90"), (3, 20))
        self.assertEqual(parse_position("3;20"), (3, 20))

    def test_parse_game_state_order(self):
        self.assertEqual(parse_game_state("Gameover"), "gameover")
        self.assertEqual(parse_game_state("Ready"), "ready")
        self.assertEqual(parse_game_state("Game"), "game")


class KnowledgeMapTests(unittest.TestCase):
    def test_no_breeze_or_flash_marks_neighbors_safe(self):
        world = KnowledgeMap(start=(10, 10), bounded=True)
        world.update_from_observation(Observation.parse(""))

        for pos in [(10, 9), (11, 10), (10, 11), (9, 10)]:
            self.assertTrue(world.cell(pos).safe)
            self.assertEqual(world.cell(pos).risk(), 0)

    def test_breeze_marks_possible_pits(self):
        world = KnowledgeMap(start=(10, 10), bounded=True)
        world.update_from_observation(Observation.parse("breeze"))

        risks = [world.cell(pos).possible_pit for pos in world.neighbors((10, 10))]
        self.assertTrue(all(value == 1 for value in risks))

    def test_blocked_forward_marks_wall_and_keeps_position(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.EAST, bounded=True)
        world.prepare_action(Action.FORWARD)
        world.resolve_action(Observation.parse("blocked"), synced_pos=None)

        self.assertEqual(world.pos, (10, 10))
        self.assertTrue(world.cell((11, 10)).blocked)

    def test_successful_synced_move_infers_heading(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        world.prepare_action(Action.FORWARD)
        world.resolve_action(Observation.parse(""), synced_pos=(11, 10))

        self.assertEqual(world.pos, (11, 10))
        self.assertEqual(world.heading, Direction.EAST)

    def test_plans_to_safe_frontier(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.EAST, bounded=True)
        world.update_from_observation(Observation.parse(""))

        path = world.plan_to_frontier(max_risk=0)

        self.assertGreaterEqual(len(path), 2)
        self.assertEqual(path[0], (10, 10))
        self.assertIn(path[1], [(10, 9), (11, 10), (10, 11), (9, 10)])


class BrainTests(unittest.TestCase):
    def test_shoots_when_enemy_in_sight(self):
        world = KnowledgeMap()
        brain = DroneBrain(world)
        obs = Observation.parse("enemy#03")
        world.update_from_observation(obs)

        self.assertEqual(brain.decide(obs), Action.SHOOT)

    def test_gets_non_poison_item_before_moving(self):
        world = KnowledgeMap()
        brain = DroneBrain(world)
        obs = Observation.parse("redLight")
        world.update_from_observation(obs)

        self.assertEqual(brain.decide(obs), Action.GET_ITEM)

    def test_does_not_pick_green_light(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.EAST, bounded=True)
        brain = DroneBrain(world)
        obs = Observation.parse("greenLight")
        world.update_from_observation(obs)

        self.assertNotEqual(brain.decide(obs), Action.GET_ITEM)


class RegressionTests(unittest.TestCase):
    """Testes de regressao para os bugs corrigidos e melhorias adicionadas."""

    # --- Bug 1: evidencia de risco nao acumula ao ficar parado ---
    def test_pit_evidence_does_not_accumulate_when_idle(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        for _ in range(8):
            world.update_from_observation(Observation.parse("breeze"))

        neighbor = world.cell((10, 9))
        # Evidencia fica estavel em 1 (nao cresce a cada observacao).
        self.assertEqual(neighbor.possible_pit, 1)
        # Risco fica estavel: poço + incerteza (celula nao marcada safe).
        stable_risk = RISK_PIT + 2  # RISK_UNKNOWN
        self.assertEqual(neighbor.risk(), stable_risk)
        # O essencial: apos muitos ciclos parado, ainda consegue planejar se
        # houver rota segura (antes do fix, o risco explodia e travava a busca).
        self.assertLessEqual(neighbor.risk(), stable_risk)

    def test_teleport_evidence_does_not_accumulate_when_idle(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        for _ in range(8):
            world.update_from_observation(Observation.parse("flash"))

        neighbor = world.cell((10, 9))
        self.assertLessEqual(neighbor.possible_teleport, 1)

    # --- Bug 2: observacao volatil nao grava risco permanente ---
    def test_volatile_update_does_not_mark_visited(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        current = world.cell((10, 10))
        self.assertEqual(current.visits, 0)

        world.update_from_observation(Observation.parse("breeze"), persist=False)
        # Volatil nao conta visita nem propaga brisa para os vizinhos.
        self.assertEqual(current.visits, 0)
        neighbor = world.cell((10, 9))
        self.assertEqual(neighbor.possible_pit, 0)

    def test_persistent_update_marks_visited_and_propagates(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        world.update_from_observation(Observation.parse("breeze"), persist=True)

        self.assertEqual(world.cell((10, 10)).visits, 1)
        self.assertEqual(world.cell((10, 9)).possible_pit, 1)

    # --- Bug 3: busca nunca planeja pisar em possivel poco/teleporte ---
    def test_search_never_targets_pit_suspect_cell(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        world.update_from_observation(Observation.parse("breeze"))

        self.assertTrue(world.is_hard_avoided((10, 9)))
        path = world.plan_to_frontier(max_risk=max(EXPLORATION_RISK_BANDS))
        for pos in path:
            self.assertFalse(world.is_hard_avoided(pos))

    def test_search_never_targets_teleport_suspect_cell(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        world.update_from_observation(Observation.parse("flash"))

        self.assertTrue(world.is_hard_avoided((10, 9)))
        path = world.plan_to_frontier(max_risk=max(EXPLORATION_RISK_BANDS))
        for pos in path:
            self.assertFalse(world.is_hard_avoided(pos))

    def test_search_prefers_safe_route_over_pit_suspect(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.EAST, bounded=True)
        # Norte suspeito de poco; leste/sul/oeste seguros.
        world.cell((10, 9)).possible_pit = 1
        for pos in [(11, 10), (10, 11), (9, 10)]:
            cell = world.cell(pos)
            cell.safe = True
            cell.safe_from_pit = True
            cell.safe_from_teleport = True

        path = world.plan_to_frontier(max_risk=max(EXPLORATION_RISK_BANDS))
        self.assertEqual(path[0], (10, 10))
        self.assertNotEqual(path[-1], (10, 9))

    # --- Melhoria: reacao a damage (fuga) ---
    def test_flees_after_taking_damage_without_enemy(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        brain = DroneBrain(world)
        obs = Observation.parse("damage")
        world.update_from_observation(obs)

        action = brain.decide(obs)
        self.assertEqual(action, Action.BACKWARD)

    def test_does_not_flee_when_enemy_in_sight(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        brain = DroneBrain(world)
        obs = Observation.parse("damage enemy#02")
        world.update_from_observation(obs)

        self.assertEqual(brain.decide(obs), Action.SHOOT)

    # --- Melhoria: busca dirigida a tesouro memorizado ---
    def test_seeks_memorized_treasure(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.EAST, bounded=True)
        for pos in [(11, 10), (12, 10)]:
            cell = world.cell(pos)
            cell.safe = True
            cell.safe_from_pit = True
            cell.safe_from_teleport = True
        world.spotted_items[(12, 10)] = "treasure"

        brain = DroneBrain(world)
        obs = Observation.parse("")
        world.update_from_observation(obs, persist=False)
        self.assertEqual(brain.decide(obs), Action.FORWARD)

    def test_forgetting_item_on_pickup(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        world.spotted_items[(10, 10)] = "treasure"
        world.prepare_action(Action.GET_ITEM)
        world.resolve_action(Observation.parse(""), synced_pos=(10, 10))
        self.assertNotIn((10, 10), world.spotted_items)

    # --- Melhoria: deteccao de teleporte limpa memoria distante ---
    def test_teleport_clears_distant_memorized_items(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        world.spotted_items[(40, 40)] = "treasure"
        world.spotted_items[(11, 10)] = "treasure"
        world.prepare_action(Action.FORWARD)
        # Posicao sincronizada muito longe do alvo (10,9) -> teleporte.
        world.resolve_action(Observation.parse(""), synced_pos=(30, 30))
        self.assertNotIn((40, 40), world.spotted_items)

    # --- Melhoria: parser de energia ---
    def test_parse_energy_variants(self):
        self.assertEqual(parse_energy("energy:75"), 75)
        self.assertEqual(parse_energy("energia=90"), 90)
        self.assertEqual(parse_energy("energy 42"), 42)
        self.assertIsNone(parse_energy("sem energia aqui"))

    # --- Limite de tiros sem acerto evita atirar no vazio ---
    def test_stops_shooting_after_many_shots_without_hit(self):
        world = KnowledgeMap(start=(10, 10), heading=Direction.NORTH, bounded=True)
        brain = DroneBrain(world)
        brain.shots_without_hit = 100  # ja gastou muitos tiros sem confirmar
        obs = Observation.parse("enemy#02")
        world.update_from_observation(obs)

        self.assertNotEqual(brain.decide(obs), Action.SHOOT)


if __name__ == "__main__":
    unittest.main()
