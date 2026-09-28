"""Application controller: menu, rounds, input and simulation presentation."""
import math
import random

from ursina import Entity, Vec3, camera, window, application, held_keys, mouse, time, lerp

from .audio import SoundBank
from .combat import Battle, V2
from .effects_plus import CombatEffects as Effects
from .models import Arena, CharacterModel, part, ring_mesh, tint
from .roster import ROSTER, KEYS
from .ui import Interface
from .lifecycle import dispose as destroy


class Game(Entity):
    def __init__(self, muted=False, offscreen=False):
        super().__init__()
        self.offscreen = offscreen
        self.mode = 'menu'
        self.selected = [0, 8]
        self.selection_side = 0
        self.arena_style = 'temple'
        self.difficulty = 'Normal'
        self.training = False
        self.scores = [0, 0]
        self.round_number = 1
        self.round_recorded = False
        self.match_done = False
        self.paused = False
        self.intro = 0
        self.battle = None
        self.arena = None
        self.actors = None
        self.effects = None
        self.preview = None
        self.rigs = []
        self.shadows = []
        self.shake = 0
        self.rng = random.Random(17)
        self.audio = SoundBank(muted)
        self.ui = Interface(self)
        self.show_menu()

    def _clear_actors(self):
        if self.effects:
            self.effects.clear()
            self.effects = None
        if self.actors:
            destroy(self.actors)
        self.actors = Entity()
        self.preview = None
        self.rigs = []
        self.shadows = []

    def _arena(self):
        if self.arena and self.arena.style == self.arena_style:
            return
        if self.arena:
            destroy(self.arena)
        self.arena = Arena(self.arena_style)

    def show_menu(self):
        self.mode, self.paused = 'menu', False
        self.battle = None
        self._clear_actors()
        self._arena()
        camera.fov = 52
        camera.position = (0, 3.5, -10.5)
        camera.look_at(Vec3(.35, 1.85, 0))
        window.color = tint('#101b2e')
        self._make_preview()
        self.ui.show_menu()

    def _make_preview(self):
        if self.preview:
            destroy(self.preview)
        self.preview = CharacterModel(ROSTER[self.selected[self.selection_side]].id, parent=self.actors,
                                      position=(3.1, 0, 0), rotation_y=165)
        if not self.shadows:
            platform = part(self.actors, 'cube', (3.1, -.09, 0), (3.4, .15, 3.2), '#222e43')
            part(self.actors, ring_mesh(64, .035), (3.1, .025, 0), 1.7, '#799bb7', lit=False)
            self.shadows.append(platform)

    def select_character(self, index):
        self.selected[self.selection_side] = index % len(ROSTER)
        self._make_preview()
        self.ui.show_menu()
        self.audio.play('select')

    def set_selection_side(self, side):
        self.selection_side = side
        self._make_preview()
        self.ui.show_menu()

    def rotate_preview(self):
        if self.preview:
            self.preview.rotation_y += 45

    def cycle_arena(self):
        self.arena_style = 'city' if self.arena_style == 'temple' else 'temple'
        self._arena()
        self.ui.show_menu()

    def cycle_difficulty(self):
        choices = ['Fácil', 'Normal', 'Difícil']
        self.difficulty = choices[(choices.index(self.difficulty)+1)%3]
        self.ui.show_menu()

    def cycle_mode(self):
        self.training = not self.training
        self.ui.show_menu()

    def start_match(self):
        self.scores = [0, 0]
        self.round_number = 1
        self.match_done = False
        self.start_round()

    def start_round(self):
        self.mode, self.paused = 'battle', False
        self._clear_actors()
        self._arena()
        self.round_recorded = False
        a, b = (ROSTER[n].id for n in self.selected)
        self.battle = Battle(a, b, self.difficulty, self.training, seed=17+self.round_number)
        self.effects = Effects(self.actors)
        for f in self.battle.fighters:
            rig = CharacterModel(f.character_id, parent=self.actors)
            self.rigs.append(rig)
            shadow = part(self.actors, ring_mesh(48, 1), (f.pos.x, .033, f.pos.z), 1.0, '#0a101b', lit=False)
            shadow.alpha = .45
            self.shadows.append(shadow)
        camera.fov = 60
        camera.position = (0, 6.3, -14)
        camera.look_at(Vec3(0, 1.3, 0))
        self.intro = 1.6 if self.training else 2.6
        self.ui.show_hud()
        self._sync_rigs(0)

    def continue_match(self):
        if self.match_done:
            self.start_match()
        else:
            self.round_number += 1
            self.start_round()

    def toggle_pause(self):
        if self.mode != 'battle' or self.battle.finished:
            return
        self.paused = not self.paused
        for f in self.battle.fighters:
            f.move = V2()
            f.blocking = f.charging = False
        if self.paused:
            self.ui.show_pause()
        else:
            self.ui.close_overlay()

    def toggle_dossier(self):
        spec = self.battle.fighters[0].spec if self.mode == 'battle' else ROSTER[self.selected[self.selection_side]]
        self.ui.show_dossier(spec)
        if self.battle:
            self.battle.fighters[0].move = V2()
            self.battle.fighters[0].blocking = False
            self.battle.fighters[0].charging = False

    def input(self, key):
        if key == 'm':
            muted = self.audio.toggle()
            self.ui.notify('Som desligado' if muted else 'Som ligado')
            return
        if self.ui.dossier:
            if key in ('tab', 'escape'):
                self.toggle_dossier()
            return
        if key == 'tab':
            self.toggle_dossier()
            return
        if self.mode == 'menu':
            if key == 'enter':
                self.start_match()
            elif key in ('left arrow', 'right arrow', 'up arrow', 'down arrow'):
                change = {'left arrow': -1, 'right arrow': 1, 'up arrow': -4, 'down arrow': 4}[key]
                self.select_character(self.selected[self.selection_side]+change)
            elif key == 'v':
                self.set_selection_side(1-self.selection_side)
            return
        if self.battle.finished:
            if key == 'enter':
                self.continue_match()
            elif key == 'escape':
                self.show_menu()
            return
        if key == 'escape':
            self.toggle_pause()
            return
        if self.paused:
            return
        if key == 'f3' and self.battle.training:
            self.battle.restore_training()
            self.ui.notify('Treino restaurado: vida, energia e supremo completos.')
            return
        if self.intro > 0:
            return
        if self.battle.qte:
            self.battle.qte_input(key)
            return
        if key in ('j', 'left mouse down'):
            self.battle.attack(0)
        elif key in ('k', 'right mouse down'):
            self.battle.attack(0, heavy=True)
        elif key in KEYS:
            self.battle.cast(0, KEYS.index(key))
        elif key == 'space':
            self.battle.dodge(0, self.battle.fighters[0].move)
        elif key == 'c':
            self.battle.jump(0)
        elif key == 'f':
            self.battle.ultimate(0)
        elif key == 'b':
            self.battle.domain_blade(0)

    def update(self):
        self.tick(min(.05, time.dt))

    def tick(self, dt):
        if self.mode == 'menu':
            if self.preview:
                self.preview.pose(dt, preview=True)
                if held_keys['left mouse'] and mouse.x > -.05 and not self.ui.dossier:
                    self.preview.rotation_y -= mouse.velocity[0]*160
            return
        if self.paused or self.ui.dossier:
            return
        battle = self.battle
        if self.intro > 0:
            self.intro -= dt
            self.ui.announce('PREPARE-SE' if self.intro > 1 else 'EXORCIZE!', .2)
            self._sync_rigs(dt)
            return
        player = battle.fighters[0]
        player.move = V2(held_keys['d']-held_keys['a'], held_keys['w']-held_keys['s'])
        battle.set_guard(0, bool(held_keys['l']))
        player.charging = bool(held_keys['g'] and player.move.length() < .1 and not player.blocking and player.lock <= 0 and player.stun <= 0)
        battle.step(dt)
        for event in battle.drain_events():
            self.effects.handle(event, battle)
            kind = event['kind']
            self.audio.play(kind)
            if kind == 'notice':
                self.ui.notify(event['text'])
            elif kind == 'cast' and event['owner'] == 1:
                self.ui.notify('INIMIGO / '+event['text'], 1.4)
            elif kind == 'transform':
                self.ui.show_hud()
                self.ui.announce(event['text'], 2.2)
            elif kind in ('qte_result', 'parry', 'break', 'domain', 'adapt', 'reflect', 'blade_pickup'):
                self.ui.announce(event['text'], 1.5)
            elif kind == 'hit':
                self.shake = max(self.shake, .10 if event['heavy'] else .04)
                if event.get('text'):
                    self.ui.announce(event['text'], 1.0)
            elif kind == 'shake':
                self.shake = event['strength']
            elif kind == 'round_end' and not self.round_recorded:
                self.round_recorded = True
                if battle.winner is not None:
                    self.scores[battle.winner] += 1
                self.match_done = max(self.scores) >= 2
                self.ui.show_result(self.match_done)
        self._sync_rigs(dt)
        self.effects.sync(battle, 0 if battle.qte else dt)
        self.ui.refresh_hud(dt)
        self._camera(dt)

    def _sync_rigs(self, dt):
        for index, f in enumerate(self.battle.fighters):
            rig, shadow = self.rigs[index], self.shadows[index]
            if rig.character_id != f.character_id:
                destroy(rig)
                rig = self.rigs[index] = CharacterModel(f.character_id, parent=self.actors)
            rig.position = (f.pos.x, f.height, f.pos.z)
            delta = self.battle.target(f).pos-f.pos
            rig.rotation_y = math.degrees(math.atan2(delta.x, delta.z))
            rig.pose(dt, f)
            shadow.position = (f.pos.x, .033, f.pos.z)
            shadow.scale = (1.5 if f.character_id == 'mahoraga' else .95)-f.height*.12
            shadow.alpha = .45-f.height*.12

    def _camera(self, dt):
        a, b = self.battle.fighters
        midpoint = (a.pos+b.pos)*.5
        distance = (a.pos-b.pos).length()
        center = Vec3(midpoint.x, 1.25, midpoint.z)
        desired = Vec3(midpoint.x, 5.8+distance*.055, midpoint.z-12-distance*.27)
        if any(f.character_id == 'mahoraga' for f in self.battle.fighters):
            center.y = 2.2
            desired.y += 1.1
            desired.z -= 1.0
        if self.battle.qte:
            actor = self.battle.fighters[self.battle.qte.actor]
            center = Vec3(actor.pos.x, 1.9, actor.pos.z)
            desired = center+Vec3(2.2, 1.1, -6.3)
        camera.position = lerp(camera.position, desired, min(1, dt*4))
        camera.look_at(center)
        if self.shake > .001:
            camera.position += Vec3(self.rng.uniform(-self.shake, self.shake), self.rng.uniform(-self.shake, self.shake), 0)
            self.shake *= max(0, 1-dt*13)

    @staticmethod
    def quit():
        application.quit()
