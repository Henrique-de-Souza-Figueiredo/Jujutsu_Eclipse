"""Playable forms, copied techniques and interactions between opposing attacks."""
import unittest

from jujutsu.combat import Battle, V2
from jujutsu.roster import BY_ID, ROSTER


def advance(battle, seconds):
    for _ in range(round(seconds*60)):
        battle.step(1/60, ai=False)


def duel(first, second='yuji', distance=6):
    battle = Battle(first, second, training=True)
    battle.fighters[0].pos = V2(-distance/2, 0)
    battle.fighters[1].pos = V2(distance/2, 0)
    return battle


def unleash(battle, side=0):
    battle.fighters[side].ultimate = 100
    assert battle.ultimate(side)
    for key in battle.qte.keys:
        battle.qte_input(key)
    battle.step(1/60, ai=False)


class ExpansionTests(unittest.TestCase):
    def test_mahoraga_is_an_invoked_form_and_not_a_roster_slot(self):
        self.assertNotIn('mahoraga', [spec.id for spec in ROSTER])
        self.assertIn('mahoraga', BY_ID)
        battle = duel('megumi')
        fighter = battle.fighters[0]
        fighter.hp *= .4
        fighter.damage_dealt = 27
        self.assertTrue(battle.cast(0, 3))
        advance(battle, 1)
        self.assertIs(battle.fighters[0], fighter)
        self.assertEqual(fighter.character_id, 'mahoraga')
        self.assertEqual(fighter.original_id, 'megumi')
        self.assertAlmostEqual(fighter.hp/fighter.spec.health, .4)
        self.assertEqual(fighter.damage_dealt, 27)
        previous = fighter.pos.copy()
        fighter.move = V2(0, 1)
        advance(battle, .5)
        self.assertGreater(fighter.pos.z, previous.z)
        fighter.move = V2()
        self.assertTrue(battle.cast(0, 2))
        advance(battle, 1)
        self.assertGreater(fighter.damage_dealt, 27)

    def test_training_restores_megumi_and_clears_adaptation(self):
        battle = duel('megumi')
        battle.cast(0, 3)
        advance(battle, 1)
        fighter = battle.fighters[0]
        fighter.adaptation['fire'] = 3
        battle.restore_training()
        self.assertEqual(fighter.character_id, 'megumi')
        self.assertEqual(fighter.hp, fighter.spec.health)
        self.assertEqual(fighter.adaptation, {})
        self.assertFalse(battle.summons or battle.projectiles or battle.zones)

    def test_adaptation_is_specific_and_develops_after_exposure(self):
        battle = duel('mahoraga', 'jogo')
        mahoraga, jogo = battle.fighters
        initial = battle.damage(jogo, mahoraga, 16, phenomenon='fire', knockback=0)
        advance(battle, 8.3)
        self.assertEqual(mahoraga.adaptation.get('fire'), 3)
        adapted = battle.damage(jogo, mahoraga, 16, phenomenon='fire', knockback=0)
        fresh = battle.damage(jogo, mahoraga, 16, phenomenon='blood', knockback=0)
        self.assertLess(adapted, initial*.5)
        self.assertAlmostEqual(fresh, initial)

    def test_positive_sword_has_bonus_against_curses(self):
        damage = []
        for target in ('yuji', 'jogo'):
            battle = duel('mahoraga', target, 3)
            self.assertTrue(battle.cast(0, 0))
            advance(battle, .3)
            damage.append(battle.fighters[0].damage_dealt)
        self.assertGreater(damage[1], damage[0]*1.4)

    def test_infinity_requires_its_own_adaptation(self):
        battle = duel('mahoraga', 'gojo', 3)
        mahoraga, gojo = battle.fighters
        mahoraga.adaptation['fire'] = 3
        gojo.statuses['infinity'] = 20
        self.assertEqual(battle.damage(mahoraga, gojo, 12, knockback=0), 0)
        advance(battle, 8.2)
        self.assertGreater(battle.damage(mahoraga, gojo, 12, knockback=0), 0)

    def test_uro_reflects_fast_projectile_and_changes_damage_owner(self):
        battle = duel('ryu', 'uro', 10)
        ryu, uro = battle.fighters
        self.assertTrue(battle.cast(1, 1))
        advance(battle, .2)
        battle._projectile(ryu, 'granite', 30, speed=150)
        battle.step(.1, ai=False)
        self.assertEqual(uro.hp, uro.spec.health)
        self.assertTrue(battle.projectiles)
        projectile = battle.projectiles[0]
        self.assertEqual(projectile.owner, 1)
        self.assertEqual(projectile.reflections, 1)
        advance(battle, .2)
        self.assertLess(ryu.hp, ryu.spec.health)
        self.assertGreater(uro.damage_dealt, 0)

    def test_reflected_nail_marks_original_shooter(self):
        battle = duel('nobara', 'uro', 8)
        nobara, uro = battle.fighters
        uro.statuses['sky_guard'] = 2.2
        battle._projectile(nobara, 'nail', 10, speed=25)
        advance(battle, .8)
        self.assertEqual(nobara.marks.get('nails'), 1)
        self.assertEqual(uro.marks.get('nails', 0), 0)

    def test_uro_cannot_reflect_domain_or_ground_eruption(self):
        battle = duel('jogo', 'uro', 4)
        jogo, uro = battle.fighters
        uro.statuses['sky_guard'] = 10
        battle._zone(jogo, 'volcano', 22, 3, .1)
        advance(battle, .3)
        first = uro.hp
        self.assertLess(first, uro.spec.health)
        battle.damage(jogo, uro, 15, domain=True)
        self.assertLess(uro.hp, first)

    def test_thin_ice_bypasses_guard_but_not_infinity(self):
        for infinity in (False, True):
            battle = duel('uro', 'gojo', 3)
            uro, gojo = battle.fighters
            battle.set_guard(1, True)
            if infinity:
                gojo.statuses['infinity'] = 4
            self.assertTrue(battle.cast(0, 0))
            advance(battle, .3)
            self.assertEqual(uro.damage_dealt == 0, infinity)
            if not infinity:
                self.assertGreater(uro.damage_dealt, 20)

    def test_yuta_can_copy_uros_reflection(self):
        battle = duel('yuta', 'uro')
        yuta = battle.fighters[0]
        yuta.statuses['rika'] = 8
        self.assertTrue(battle.cast(0, 2))
        advance(battle, .2)
        self.assertTrue(yuta.has('sky_guard'))

    def test_domain_katanas_require_owner_proximity_and_disappear_on_use(self):
        battle = duel('yuta', 'sukuna')
        unleash(battle)
        self.assertEqual(battle.domain['kind'], 'mutual_love')
        advance(battle, 1.3)
        yuta = battle.fighters[0]
        blade = battle.domain['swords'][0]
        yuta.pos = V2(-12, 0)
        self.assertFalse(battle.domain_blade(0))
        yuta.pos = blade['pos'].copy()
        self.assertTrue(battle.domain_blade(0))
        self.assertGreater(blade['respawn'], 0)
        battle.fighters[1].pos = blade['pos'].copy()
        battle.fighters[1].stun = battle.fighters[1].lock = 0
        self.assertFalse(battle.domain_blade(1))
        advance(battle, 10)
        self.assertIsNone(battle.domain)
        self.assertFalse(battle.domain_blade(0))

    def test_equal_opposing_beams_annihilate(self):
        battle = duel('yuta', 'yuta', 10)
        a, b = battle.fighters
        battle._projectile(a, 'love_beam', 30, speed=100)
        battle._projectile(b, 'love_beam', 30, speed=100)
        battle.step(.1, ai=False)
        self.assertFalse(battle.projectiles)
        self.assertEqual(a.hp, a.spec.health)
        self.assertEqual(b.hp, b.spec.health)
        self.assertTrue(any(e['kind'] == 'beam_clash' for e in battle.events))


if __name__ == '__main__':
    unittest.main()
