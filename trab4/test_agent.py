import unittest

from agent import (
    Action,
    Direction,
    DroneBrain,
    KnowledgeMap,
    Observation,
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


if __name__ == "__main__":
    unittest.main()
