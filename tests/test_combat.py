import math
import unittest

from jujutsu.combat import Battle, QTE, V2, segment_distance
from jujutsu.roster import ROSTER, DOMAIN_KINDS


def advance(battle, seconds, ai=False):
    for _ in range(math.ceil(seconds*60)):
        battle.step(1/60, ai=ai)


def close_battle(character, target='yuji'):
    battle = Battle(character, target, training=True)
    battle.fighters[0].pos = V2(-1, 0)
    battle.fighters[1].pos = V2(1, 0)
    return battle


def prepare_skill(battle):
    a, b = battle.fighters
    a.hp -= 50
    a.statuses.update(blue_ready=8, red_ready=8, dismantle_ready=12, cleave_ready=12, rika=8)
    a.blood = 2
    b.marks['nails'] = 3


class CombatTests(unittest.TestCase):
    def test_twelve_distinct_complete_kits(self):
        self.assertGreaterEqual(len(ROSTER), 10)
        self.assertEqual(len({c.id for c in ROSTER}), len(ROSTER))
        self.assertEqual(len({c.ultimate_kind for c in ROSTER}), len(ROSTER))
        for spec in ROSTER:
            self.assertEqual(len(spec.skills), 4)
            self.assertTrue(all(s.instruction for s in spec.skills))

    def test_every_technique_executes_and_leaves_finite_state(self):
        for spec in ROSTER:
            for slot, tech in enumerate(spec.skills):
                with self.subTest(character=spec.id, technique=tech.name):
                    battle = close_battle(spec.id)
                    prepare_skill(battle)
                    self.assertTrue(battle.cast(0, slot))
                    if battle.qte:
                        battle.qte.elapsed = battle.qte.target*battle.qte.duration
                        battle.qte_input('space')
                    advance(battle, 2)
                    for fighter in battle.fighters:
                        self.assertTrue(math.isfinite(fighter.hp))
                        self.assertGreaterEqual(fighter.hp, 0)
                        self.assertGreaterEqual(fighter.energy, 0)
                        self.assertTrue(math.isfinite(fighter.pos.x))

    def test_prerequisites_do_not_spend_resources_or_cooldowns(self):
        for character, slot in (('gojo', 2), ('sukuna', 2), ('nobara', 1), ('nobara', 2), ('choso', 1), ('choso', 2), ('yuta', 2)):
            with self.subTest(character=character, slot=slot):
                battle = close_battle(character)
                self.assertFalse(battle.cast(0, slot))
                self.assertEqual(battle.fighters[0].energy, 100)
                self.assertEqual(battle.fighters[0].cooldowns[slot], 0)

    def test_basic_attacks_require_contact(self):
        battle = Battle('yuji', 'sukuna')
        hp = battle.fighters[1].hp
        battle.attack(0)
        advance(battle, .4)
        self.assertEqual(battle.fighters[1].hp, hp)
        battle.fighters[0].pos = battle.fighters[1].pos+V2(-2, 0)
        battle.attack(0)
        advance(battle, .4)
        self.assertLess(battle.fighters[1].hp, hp)

    def test_divergent_fist_really_has_delayed_second_impact(self):
        battle = close_battle('yuji')
        initial = battle.fighters[1].hp
        battle.cast(0, 0)
        advance(battle, .2)
        first = battle.fighters[1].hp
        self.assertLess(first, initial)
        advance(battle, .5)
        self.assertLess(battle.fighters[1].hp, first)

    def test_perfect_guard_negates_hit_and_stuns_attacker(self):
        battle = close_battle('yuji')
        a, b = battle.fighters
        battle.set_guard(1, True)
        self.assertEqual(battle.damage(a, b, 25), 0)
        self.assertEqual(b.hp, b.spec.health)
        self.assertGreater(a.stun, 0)

    def test_holding_guard_reduces_damage_and_heavy_breaks_it(self):
        battle = close_battle('yuji')
        a, b = battle.fighters
        battle.set_guard(1, True)
        b.parry = 0
        b.guard = 8
        amount = battle.damage(a, b, 25, heavy=True)
        self.assertLess(amount, 10)
        self.assertFalse(b.blocking)
        self.assertGreater(b.stun, .9)

    def test_infinity_blocks_physical_but_not_domain_or_soul(self):
        battle = close_battle('yuji', 'gojo')
        a, b = battle.fighters
        b.statuses['infinity'] = 3
        self.assertEqual(battle.damage(a, b, 20), 0)
        self.assertGreater(battle.damage(a, b, 20, soul=True), 0)
        self.assertGreater(battle.damage(a, b, 20, domain=True), 0)

    def test_mahito_has_a_meaningful_soul_damage_weakness(self):
        physical = close_battle('yuji', 'mahito')
        soul = close_battle('yuji', 'mahito')
        amount1 = physical.damage(*physical.fighters, 20)
        amount2 = soul.damage(*soul.fighters, 20, soul=True)
        self.assertGreater(amount2, amount1)

    def test_dodge_cost_invulnerability_and_arena_bounds(self):
        battle = close_battle('maki')
        a, b = battle.fighters
        a.pos = V2(12, 0)
        self.assertTrue(battle.dodge(0, V2(1, 0)))
        self.assertEqual(a.stamina, 84)
        self.assertEqual(battle.damage(b, a, 20), 0)
        advance(battle, .4)
        self.assertLessEqual(a.pos.length(), 12.71)
        self.assertGreater(battle.damage(b, a, 20), 0)

    def test_qte_score_changes_damage_and_combat_waits(self):
        results = []
        for quality in ('fail', 'perfect'):
            battle = close_battle('yuji')
            battle.cast(0, 1)
            before = battle.elapsed
            if quality == 'perfect':
                battle.qte.elapsed = battle.qte.duration*battle.qte.target
            battle.qte_input('space')
            battle.step(.016)
            self.assertEqual(battle.elapsed, before)
            results.append(battle.fighters[1].hp)
        self.assertLess(results[1], results[0])

    def test_sequence_errors_and_timeouts(self):
        qte = QTE(0, 'ultimate', 'test', 'sequence')
        qte.press('k')
        for key in qte.keys:
            qte.press(key)
        self.assertEqual(qte.mistakes, 1)
        self.assertLess(qte.result, 1)
        battle = close_battle('yuji')
        battle.ultimate(0)
        advance(battle, 4)
        self.assertIsNone(battle.qte)
        self.assertGreater(battle.fighters[0].damage_dealt, 0)

    def test_nails_establish_link_and_hairpin_consumes_it(self):
        battle = close_battle('nobara')
        battle.cast(0, 0)
        advance(battle, .7)
        a, b = battle.fighters
        self.assertGreater(b.marks.get('nails', 0), 0)
        b.pos = V2(11, 0)
        hp = b.hp
        self.assertTrue(battle.cast(0, 2))
        advance(battle, .3)
        self.assertEqual(b.marks['nails'], 0)
        self.assertLess(b.hp, hp)

    def test_choso_preparation_and_resource_consumption(self):
        battle = close_battle('choso')
        battle.cast(0, 0)
        advance(battle, .6)
        self.assertEqual(battle.fighters[0].blood, 1)
        self.assertTrue(battle.cast(0, 1))
        advance(battle, .6)
        self.assertEqual(battle.fighters[0].blood, 0)
        self.assertLess(battle.fighters[1].hp, battle.fighters[1].spec.health)

    def test_todo_swaps_exact_positions(self):
        battle = close_battle('todo')
        a, b = battle.fighters
        first, second = a.pos.copy(), b.pos.copy()
        battle.cast(0, 0)
        advance(battle, .2)
        self.assertEqual(a.pos, second)
        self.assertEqual(b.pos, first)
        self.assertTrue(a.has('rhythm'))

    def test_maki_spends_vigor_without_cursed_energy(self):
        battle = close_battle('maki')
        self.assertTrue(battle.cast(0, 0))
        self.assertEqual(battle.fighters[0].energy, 100)
        self.assertEqual(battle.fighters[0].stamina, 84)
        advance(battle, .6)
        battle.cast(0, 3)
        advance(battle, .3)
        self.assertEqual(battle.fighters[0].weapon, 1)

    def test_counter_and_summons_deal_damage(self):
        battle = close_battle('maki')
        a, b = battle.fighters
        battle.cast(0, 2)
        advance(battle, .2)
        battle.damage(b, a, 20)
        self.assertEqual(a.hp, a.spec.health)
        self.assertLess(b.hp, b.spec.health)
        battle = close_battle('megumi')
        battle.cast(0, 0)
        advance(battle, 3)
        self.assertTrue(battle.summons)
        self.assertLess(battle.fighters[1].hp, battle.fighters[1].spec.health)

    def test_every_ultimate_has_effect_and_cleans_up(self):
        for spec in ROSTER:
            with self.subTest(character=spec.id):
                battle = close_battle(spec.id)
                self.assertTrue(battle.ultimate(0))
                for key in battle.qte.keys:
                    battle.qte_input(key)
                battle.step(.016)
                if spec.ultimate_kind in DOMAIN_KINDS:
                    self.assertIsNotNone(battle.domain)
                advance(battle, 11)
                self.assertGreater(battle.fighters[0].damage_dealt, 0)
                self.assertIsNone(battle.domain)

    def test_successful_domain_clash_changes_domain_owner(self):
        battle = close_battle('gojo', 'sukuna')
        battle.fighters[1].ultimate = 100
        battle.ultimate(1)
        self.assertEqual(battle.qte.kind, 'clash')
        for key in battle.qte.keys:
            battle.qte_input(key)
        battle.step(.016)
        self.assertEqual(battle.domain['owner'], 0)
        self.assertEqual(battle.domain['kind'], 'void')

    def test_telegraphed_ground_attack_can_be_avoided(self):
        battle = close_battle('jogo')
        battle.cast(0, 2)
        advance(battle, .3)
        self.assertTrue(battle.zones)
        target = battle.fighters[1]
        target.pos = V2(11, 0)
        advance(battle, 2)
        self.assertEqual(target.hp, target.spec.health)

    def test_swept_projectile_collision(self):
        self.assertLess(segment_distance(V2(0, .1), V2(-5, 0), V2(5, 0)), .2)
        battle = close_battle('choso')
        a, b = battle.fighters
        battle._projectile(a, 'blood', 20, speed=100)
        battle.step(.1, ai=False)
        self.assertLess(b.hp, b.spec.health)

    def test_round_end_stops_damage_and_new_battle_is_clean(self):
        battle = Battle('yuji', 'gojo')
        a, b = battle.fighters
        battle._projectile(a, 'blood', 20)
        battle.damage(a, b, 999, soul=True)
        self.assertTrue(battle.finished)
        self.assertEqual(battle.winner, 0)
        self.assertFalse(battle.projectiles or battle.pending or battle.zones or battle.summons)
        old_hp = a.hp
        advance(battle, 5, ai=True)
        self.assertEqual(a.hp, old_hp)
        clean = Battle('yuji', 'gojo')
        self.assertFalse(clean.finished)
        self.assertEqual(clean.fighters[0].cooldowns, [0]*4)

    def test_all_ai_matchups_can_finish_without_invalid_state(self):
        for spec in ROSTER:
            with self.subTest(character=spec.id):
                battle = Battle('yuji', spec.id, seed=12)
                for _ in range(7000):
                    if battle.finished:
                        break
                    a, b = battle.fighters
                    if battle.qte:
                        qte = battle.qte
                        if qte.mode == 'sequence':
                            battle.qte_input(qte.keys[qte.index])
                        elif qte.progress >= qte.target:
                            battle.qte_input('space')
                    else:
                        a.move = (b.pos-a.pos).unit()
                        if battle.distance(a) < 2.7:
                            battle.attack(0, heavy=True)
                    battle.step(1/60)
                    battle.drain_events()
                    for f in battle.fighters:
                        self.assertTrue(0 <= f.hp <= f.spec.health)
                        self.assertGreaterEqual(f.energy, 0)
                self.assertTrue(battle.finished)


if __name__ == '__main__':
    unittest.main()
