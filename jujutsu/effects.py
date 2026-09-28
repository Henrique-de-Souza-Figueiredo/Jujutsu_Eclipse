"""Transient combat effects, telegraphs and domain scenery."""
import math
import random

from ursina import Entity, Text, Vec3
from ursina.models.procedural.cone import Cone

from .models import part, ring_mesh, tint, make_summon
from .lifecycle import dispose as destroy


EFFECT_COLORS = {
    'blue': '#4b9eff', 'red': '#ff5f73', 'purple': '#ae70ff', 'fire': '#ffa052',
    'fuga': '#ffbe73', 'blood': '#ed477a', 'nail': '#ffd396', 'dismantle': '#f8e6e1',
    'ember': '#ff823c', 'toad': '#a4d6a1', 'nue': '#ccb5ff', 'meteor': '#ff773d',
    'volcano': '#ff7544', 'supernova': '#e44c7c', 'collapse': '#eadba6',
    'nail_trap': '#edb56e', 'void': '#78ceff', 'shrine': '#ff596f',
    'shadow_domain': '#b798fa', 'soul_domain': '#80e0c7', 'volcano_domain': '#ffaf59',
}


class Effects:
    def __init__(self, parent):
        self.root = Entity(parent=parent)
        self.items = []
        self.projectiles = {}
        self.zones = {}
        self.summons = {}
        self.domain_root = None
        self.domain_key = None
        self.rng = random.Random(5)
        self.clock = 0

    def add(self, node, life, velocity=None, growth=0, spin=0):
        self.items.append([node, life, life, velocity or Vec3(0, 0, 0), growth, spin])
        if len(self.items) > 160:
            destroy(self.items.pop(0)[0])
        return node

    def ring(self, pos, tone, radius=1, life=.45, vertical=False):
        node = part(self.root, ring_mesh(40, .07), (pos.x, .07 if not vertical else 1.6, pos.z), .2,
                    tone, lit=False, double_sided=True)
        if vertical:
            node.rotation_x = 90
        return self.add(node, life, growth=radius/life, spin=40)

    def burst(self, pos, tone, count=10, height=1.5):
        for _ in range(count):
            v = Vec3(self.rng.uniform(-3, 3), self.rng.uniform(.4, 4), self.rng.uniform(-3, 3))
            node = part(self.root, 'cube', (pos.x, height, pos.z), (.035, .22, .035), tone,
                        rotation=(self.rng.uniform(0, 180), self.rng.uniform(0, 180), self.rng.uniform(0, 180)), lit=False)
            self.add(node, .4+self.rng.random()*.25, v, spin=250)

    def handle(self, event, battle):
        kind = event['kind']
        pos = event.get('pos')
        if pos is None:
            return
        tone = battle.fighters[event.get('owner', 0)].spec.accent
        if kind == 'hit':
            tone = '#d7f4ff' if event['blocked'] else ('#ff5975' if event.get('soul') else '#ffe6b2')
            self.burst(pos, tone, 7 if event['blocked'] else 12)
            self.ring(pos, tone, 1, .25, vertical=True)
            damage = Text(parent=self.root, text=str(event['amount']), position=(pos.x, 3.5, pos.z),
                          scale=9, origin=(0, 0), billboard=True, color=tint(tone))
            self.add(damage, .8, Vec3(0, 1, 0))
        elif kind in ('parry', 'break', 'barrier'):
            self.ring(pos, '#bceeff', 1.8, .35, vertical=True)
            self.burst(pos, '#bceeff', 9)
        elif kind in ('dodge', 'jump', 'teleport', 'swap', 'summon'):
            self.ring(pos, tone, 2, .5)
            if kind == 'swap':
                self.ring(event['end'], tone, 2, .5)
        elif kind == 'heal':
            self.ring(pos, '#94f9c9', 1.6, .6)
            self.burst(pos, '#94f9c9', 12)
        elif kind == 'cast':
            self.ring(pos, tone, 1.1, .32)
        elif kind in ('finisher', 'resonance', 'eruption'):
            effect = event.get('effect', 'purple')
            tone = EFFECT_COLORS.get(effect, tone)
            self.ring(pos, tone, event.get('radius', 3), .65)
            self.burst(pos, tone, 18)
            if kind == 'eruption':
                if effect == 'nue':
                    wing = Entity(parent=self.root, position=(pos.x, 5.2, pos.z))
                    part(wing, 'sphere', scale=(.8, .6, 1.1), tone='#917eb5')
                    for side in (-1, 1):
                        part(wing, 'cube', (side*1.1, 0, 0), (2, .10, .8), '#b6a2d4', rotation=(0, 0, side*18))
                    self.add(wing, .55, Vec3(0, 1.5, 0))
                    bolt = part(self.root, 'cube', (pos.x, 2.6, pos.z), (.16, 5.2, .16), '#e9dbff', lit=False)
                    self.add(bolt, .25)
                elif effect in ('meteor', 'volcano', 'collapse'):
                    for i in range(8):
                        a = i*math.tau/8
                        rock = part(self.root, 'cube', (pos.x+math.cos(a), .2, pos.z+math.sin(a)),
                                    (.45, 1.8, .6), tone, rotation=(i*14, i*39, 13))
                        self.add(rock, .7, Vec3(math.cos(a)*2, 2.5, math.sin(a)*2), spin=80)
            if kind == 'finisher':
                end = event['end']
                start = Vec3(pos.x, 1.7, pos.z)
                finish = Vec3(end.x, 1.7, end.z)
                beam = part(self.root, 'cube', (start+finish)/2, (.8, .8, max(2, (finish-start).length())), tone, lit=False)
                beam.look_at(finish)
                self.add(beam, .5, growth=.3)
        elif kind == 'swing':
            ring = self.ring(pos, tone, event['reach']*.6, .22, vertical=True)
            ring.rotation_y = battle.fighters[event['owner']].side*180+35

    def sync(self, battle, dt):
        self.clock += dt
        self._sync_projectiles(battle)
        self._sync_zones(battle)
        self._sync_summons(battle, dt)
        self._sync_domain(battle)
        for item in self.items[:]:
            node, life, original, velocity, growth, spin = item
            life -= dt
            item[1] = life
            if life <= 0:
                destroy(node)
                self.items.remove(item)
                continue
            node.position += velocity*dt
            node.scale += Vec3(1, 1, 1)*growth*dt
            node.rotation_y += spin*dt
            node.alpha = min(1, life/original*1.6)

    def _sync_projectiles(self, battle):
        ids = {p.uid for p in battle.projectiles}
        self._prune(self.projectiles, ids)
        for p in battle.projectiles:
            if p.uid not in self.projectiles:
                tone = EFFECT_COLORS.get(p.kind, '#e6cfff')
                root = Entity(parent=self.root)
                scale = (p.radius*2, p.radius*2, p.radius*3)
                if p.kind in ('dismantle', 'nail', 'blood', 'toad'):
                    scale = (.05 if p.kind != 'dismantle' else 2, .10, 1.5)
                part(root, 'sphere' if p.kind not in ('nail', 'dismantle') else 'cube', scale=scale, tone=tone, lit=False)
                part(root, ring_mesh(28, .09), scale=max(.25, p.radius*1.5), tone=tone,
                     rotation=(90, 0, 0), lit=False, double_sided=True)
                self.projectiles[p.uid] = root
            root = self.projectiles[p.uid]
            root.position = (p.pos.x, 1.5, p.pos.z)
            root.rotation_y = math.degrees(math.atan2(p.direction.x, p.direction.z))

    def _sync_zones(self, battle):
        ids = {z.uid for z in battle.zones}
        self._prune(self.zones, ids)
        for z in battle.zones:
            if z.uid not in self.zones:
                root = Entity(parent=self.root, position=(z.pos.x, .05, z.pos.z))
                tone = EFFECT_COLORS.get(z.kind, '#8cd4ff')
                part(root, ring_mesh(64, .03), scale=z.radius, tone=tone, lit=False, double_sided=True)
                inner = part(root, ring_mesh(48, .72), scale=z.radius*.96, tone=tone, lit=False, double_sided=True)
                inner.alpha = .075
                part(root, ring_mesh(48, .012), pos=(0, .01, 0), scale=z.radius*.72, tone=tone, lit=False)
                if z.kind == 'meteor':
                    meteor = part(root, 'sphere', (0, 10, 0), 3.5, '#834459')
                    meteor.name = 'meteor'
                    part(meteor, ring_mesh(32, .12), scale=.65, tone='#ffb75d', rotation=(70, 15, 0), lit=False)
                self.zones[z.uid] = root
            root = self.zones[z.uid]
            root.rotation_y = self.clock*12
            root.alpha = .65+math.sin(self.clock*8)*.15
            for child in root.children:
                if child.name == 'meteor':
                    child.y = max(.7, z.delay*6)

    def _sync_summons(self, battle, dt):
        ids = {s.uid for s in battle.summons}
        self._prune(self.summons, ids)
        for s in battle.summons:
            if s.uid not in self.summons:
                self.summons[s.uid] = make_summon(self.root, s.kind, battle.fighters[s.owner].spec.accent)
            root = self.summons[s.uid]
            root.position = (s.pos.x, abs(math.sin(self.clock*10))*.12, s.pos.z)
            target = battle.fighters[1-s.owner].pos
            root.rotation_y = math.degrees(math.atan2(target.x-s.pos.x, target.z-s.pos.z))

    def _sync_domain(self, battle):
        key = (battle.domain['owner'], battle.domain['kind']) if battle.domain else None
        if key == self.domain_key:
            if self.domain_root:
                self.domain_root.rotation_y += .07
            return
        if self.domain_root:
            destroy(self.domain_root)
            self.domain_root = None
        self.domain_key = key
        if key is None:
            return
        owner, kind = key
        self.domain_root = root = Entity(parent=self.root)
        tone = EFFECT_COLORS[kind]
        part(root, ring_mesh(96, .024), pos=(0, .055, 0), scale=11.8, tone=tone, lit=False)
        for i in range(16):
            a = i*math.tau/16
            x, z = math.cos(a)*12, math.sin(a)*12
            if kind == 'soul_domain':
                hand = Entity(parent=root, position=(x, 2, z), rotation_y=-i*22.5)
                part(hand, pos=(0, .5, 0), scale=(1.1, 1.6, .3), tone='#6faaa4')
                for j in range(4):
                    part(hand, pos=((j-1.5)*.25, 1.6, 0), scale=(.20, 1.4, .22), tone='#91b4ae')
            elif kind in ('shrine', 'void'):
                part(root, 'cube', (x, 3, z), (.055, 6, .055), tone, rotation=(0, 0, 15 if kind == 'shrine' else 0), lit=False)
            elif kind == 'volcano_domain':
                part(root, Cone(7), (x, 2, z), (3, 4, 3), '#884951')
                part(root, ring_mesh(24, .24), (x, .08, z), 2.7, tone, lit=False)
            else:
                part(root, ring_mesh(32, .8), (x*.7, .065, z*.7), 2.0, '#35284c', lit=False)
        if kind == 'shrine':
            for side in (-1, 1):
                part(root, 'cube', (side*2.4, 2.4, 7), (.5, 4.8, .5), '#cd6977')
            part(root, 'cube', (0, 4.8, 7), (6.4, .4, 2), '#54263e')
            part(root, 'cube', (0, 4.3, 7), (5.4, .3, 1.6), '#ed99a1')
        if kind == 'void':
            black_hole = part(root, 'sphere', (0, 8, 16), 5.5, '#101421', lit=False)
            part(root, ring_mesh(80, .025), (0, 8, 15.8), 3.7, '#e1f6ff', rotation=(75, 15, 0), lit=False)

    @staticmethod
    def _prune(mapping, ids):
        for uid in list(mapping):
            if uid not in ids:
                destroy(mapping.pop(uid))

    def clear(self):
        destroy(self.root)
