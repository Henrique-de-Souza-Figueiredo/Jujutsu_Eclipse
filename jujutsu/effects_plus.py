"""Layered, character-specific combat choreography built from local meshes."""
import math
from functools import lru_cache

from ursina import Entity, Mesh, Vec3

from .effects import Effects, EFFECT_COLORS
from .models import part, ring_mesh, stroke, tint
from .lifecycle import dispose as destroy


PALETTE = {
    **EFFECT_COLORS, 'granite': '#c692ff', 'granite_small': '#bd83ff',
    'granite_max': '#f2baff', 'love_beam': '#a4ffe2', 'adaptive_slash': '#fff0b9',
    'thin_ice': '#b4edff', 'sky_final': '#a2dcff', 'general_slam': '#eed897',
    'mutual_love': '#f4d6ae', 'beam': '#daacff', 'space': '#b9efff',
    'positive': '#ffffbd', 'slash': '#ffe9dc', 'electric': '#d0b3ff',
}


@lru_cache(maxsize=8)
def crescent_mesh(sweep=235):
    vertices, triangles = [], []
    for i in range(33):
        t = i/32
        angle = math.radians(-sweep/2+sweep*t)
        width = math.sin(t*math.pi)*.24
        for radius in (1-width, 1):
            vertices.append((math.cos(angle)*radius, 0, math.sin(angle)*radius))
        if i:
            n = i*2
            triangles.extend(((n-2, n, n-1), (n-1, n, n+1)))
    return Mesh(vertices=vertices, triangles=triangles, normals=[(0, 1, 0)]*len(vertices), static=True)


class CombatEffects(Effects):
    """Keep the simulation authoritative; every visual has a bounded lifetime."""
    def __init__(self, parent):
        super().__init__(parent)
        self.domain_identity = None
        self.domain_age = 0
        self.domain_blades = {}
        self.orbits = []
        self.projectile_frames = {}

    def arc(self, pos, tone, radius=2, life=.32, heading=0, tilt=25, height=1.6):
        root = Entity(parent=self.root, position=(pos.x, height, pos.z), rotation=(tilt, heading, 0))
        part(root, crescent_mesh(), scale=radius, tone=tone, lit=False, double_sided=True)
        part(root, crescent_mesh(), pos=(0, .018, 0), scale=radius*.94, tone='#fff8ec', lit=False, double_sided=True)
        glow = part(root, crescent_mesh(), pos=(0, -.012, 0), scale=radius*1.09,
                    tone=tone, lit=False, double_sided=True)
        glow.alpha = .16
        return self.add(root, life, growth=.35, spin=150)

    def beam(self, start, end, tone, width=.14, life=.32):
        delta = end-start
        if delta.length() < .01:
            return
        root = Entity(parent=self.root, position=(start+end)/2)
        root.look_at(end)
        length = delta.length()
        outer = part(root, 'cube', scale=(width*2.8, width*2.8, length), tone=tone, lit=False)
        outer.alpha = .16
        part(root, 'cube', scale=(width, width, length), tone=tone, lit=False)
        part(root, 'cube', scale=(width*.30, width*.30, length), tone='#fffbee', lit=False)
        return self.add(root, life)

    def lightning(self, pos, tone, radius=2, rays=6, height=1.65):
        for j in range(rays):
            angle = j*math.tau/rays+self.rng.uniform(-.15, .15)
            start = Vec3(pos.x, height, pos.z)
            for i in range(3):
                distance = (i+1)*radius/3
                end = Vec3(pos.x+math.cos(angle)*distance,
                           height+self.rng.uniform(-.65, .65), pos.z+math.sin(angle)*distance)
                self.beam(start, end, tone, .045 if i else .075, .24)
                start = end

    def sky(self, pos, radius=2.3, shattered=False):
        root = Entity(parent=self.root, position=(pos.x, 1.65, pos.z))
        for i in range(9):
            angle = i*math.tau/9
            x, y = math.cos(angle)*radius*.48, math.sin(angle)*radius*.48
            shard = part(root, Mesh(vertices=[(-.7, -.1, 0), (.6, .15, .18), (.10, .8, -.16)],
                                    triangles=[(0, 1, 2)]), (x, y, math.sin(angle*2)*.30),
                         radius*.55, '#d5f5ff' if i % 2 else '#88b8e1',
                         rotation=(i*13, i*21, i*39), lit=False, double_sided=True)
            shard.alpha = .5
        self.add(root, .65, growth=2 if shattered else .3, spin=55)
        self.ring(pos, '#b5f6ff', radius, .5, vertical=True)
        if shattered:
            self.lightning(pos, '#a9e6ff', radius*1.2, 5)

    def wheel_flash(self, pos, radius=2.0):
        root = Entity(parent=self.root, position=(pos.x, 3.5, pos.z))
        part(root, ring_mesh(64, .05), scale=radius, tone='#f5d881', rotation=(90, 0, 0), lit=False, double_sided=True)
        for i in range(8):
            angle = i*math.tau/8
            end = (math.cos(angle)*radius, math.sin(angle)*radius, 0)
            spoke = stroke(root, (0, 0, 0), end, .04, '#ebc67a')
            spoke.shader = None
            part(root, pos=end, scale=.16, tone='#fff9d4', lit=False)
        self.add(root, .85, growth=.3)

    def handle(self, event, battle):
        pos = event.get('pos')
        if pos is None:
            return
        kind = event['kind']
        owner = battle.fighters[event.get('owner', 0)]
        target = battle.target(owner)
        effect = event.get('effect', '')
        tone = PALETTE.get(effect, owner.spec.accent)
        end = event.get('end', target.pos)
        heading = math.degrees(math.atan2(end.x-pos.x, end.z-pos.z))
        if kind == 'swing':
            radius = event.get('reach', 3)*.65
            self.arc(pos, tone, radius, heading=heading, tilt=55 if event.get('heavy') else 12)
            if owner.character_id in ('yuta', 'maki', 'nanami', 'mahoraga'):
                self.arc(pos, '#fff9da', radius*1.12, .22, heading+25, -30)
            return
        if kind == 'cast':
            self.ring(pos, tone, 1.3, .42)
            if effect in ('sky_guard', 'sky_mantle', 'sky_flight', 'thin_ice'):
                self.sky(pos, 2 if effect != 'thin_ice' else 1.2)
            elif effect in ('granite', 'granite_volley', 'output'):
                for i in range(3):
                    ring = self.ring(pos, '#d9a5ff', .9+i*.4, .55, vertical=True)
                    ring.y = 3.25
                    ring.rotation_y = heading
                self.burst(pos, '#edd1ff', 8, height=3.2)
            elif effect in ('katana', 'cleave', 'morph_blade', 'sweep', 'thrust', 'extermination', 'adaptive_slash'):
                self.arc(pos, tone, 2.7, heading=heading, tilt=45)
            elif effect in ('divergent', 'black_flash', 'ratio', 'point_blank'):
                self.lightning(pos, '#ff4060' if effect == 'black_flash' else tone, 1.6, 4)
            elif effect in ('resonance', 'hairpin'):
                self.beam(Vec3(pos.x, 1.9, pos.z), Vec3(end.x, 1.7, end.z), '#f2bc76', .06, .55)
            elif effect == 'mahoraga':
                self.wheel_flash(pos, 2.2)
                for i in range(3):
                    self.ring(pos, '#463951', 2+i, .9)
            elif effect in ('infinity', 'focus', 'overtime', 'reinforce', 'red_scale', 'soul_armor'):
                for i in range(3):
                    ring = self.ring(pos, tone, 1.3, .65)
                    ring.y = .3+i*.65
            else:
                self.burst(pos, tone, 5)
            return
        if kind in ('reflect', 'reflection'):
            self.sky(pos, 2.1, shattered=True)
            self.arc(pos, '#d3fbff', 2.6, .4, heading, 70)
            return
        if kind in ('beam_clash', 'projectile_clash', 'clash'):
            self.lightning(pos, '#f3d9ff', 2.8, 7)
            self.ring(pos, '#fdf0ff', 3, .45, vertical=True)
            self.burst(pos, tone, 14)
            return
        if kind in ('transform', 'adapt'):
            self.wheel_flash(pos, 2.4 if kind == 'transform' else 1.3)
            self.burst(pos, '#ffe4a1', 15, height=3)
            if kind == 'transform':
                for i in range(3):
                    self.ring(pos, '#f8dfaa', 3+i*.8, .8)
            return
        if kind == 'blade_pickup':
            self.arc(pos, tone, 2.4, .5, heading, -25)
            self.burst(pos, '#fff4c7', 12)
            return
        if kind == 'finisher':
            self._finisher_visual(owner, pos, end, effect, tone)
            return
        if kind in ('finisher_strike', 'finisher_hit'):
            pos = end
            self.arc(pos, tone, 3 if event.get('final') else 2, .4, heading, self.rng.uniform(-70, 70))
            if effect in ('black_rush', 'ratio_rush'):
                self.lightning(pos, '#ff304d', 3.2 if event.get('final') else 1.8, 7)
            self.burst(pos, tone, 12)
            return
        if kind == 'projectile_impact':
            self.ring(pos, tone, 1.7, .35, vertical=True)
            self.burst(pos, tone, 8)
            return
        if kind == 'jacob':
            self.beam(Vec3(pos.x, .1, pos.z), Vec3(pos.x, 11, pos.z), '#fff1b8', .6, .42)
            self.ring(pos, '#f8e6aa', 2.2, .55)
            return
        if kind == 'cinematic':
            for i in range(3):
                ring = self.ring(pos, tone, 2+i, 1.2)
                ring.y = .12+i*.18
            return
        if kind == 'hit' and (event.get('heavy') or event.get('soul')):
            self.arc(pos, tone, 1.3, .2, heading, 65)
            if 'BLACK' in event.get('text', ''):
                self.lightning(pos, '#ff254b', 2.4, 7)
        if kind == 'eruption':
            if effect in ('thin_ice', 'sky_final'):
                self.sky(pos, event.get('radius', 3), shattered=True)
                return
            if effect in ('mutual_love', 'jacob'):
                self.beam(Vec3(pos.x, .1, pos.z), Vec3(pos.x, 11, pos.z), '#fff1b8', .65, .5)
                self.ring(pos, '#f8e6aa', 3.2, .7)
                return
            if effect in ('nue', 'supernova'):
                self.lightning(pos, tone, event.get('radius', 3), 8, height=2.1)
            elif effect == 'blue':
                for i in range(3):
                    orb = part(self.root, 'sphere', (pos.x, 1.5, pos.z), .4+i*.4, '#5da4ff', lit=False)
                    orb.alpha = 1 if i == 0 else .12
                    self.add(orb, .65)
        super().handle(event, battle)

    def _finisher_visual(self, owner, pos, end, effect, tone):
        heading = math.degrees(math.atan2(end.x-pos.x, end.z-pos.z))
        self.ring(end, tone, 4.5, .8)
        if effect == 'granite_final':
            for i in range(4):
                ring = self.ring(pos, '#d2a0ff', 1.3+i*.55, .9, vertical=True)
                ring.y = 3
                ring.rotation_y = heading
            self.lightning(pos, '#e1b2ff', 2.5, 6, height=3.1)
        elif effect == 'sky_final':
            self.sky(end, 4.4, shattered=True)
        elif effect == 'blood_final':
            for i in range(7):
                angle = i*math.tau/7
                point = Vec3(pos.x+math.cos(angle)*1.6, 1.7+math.sin(angle)*1.3, pos.z)
                orb = part(self.root, pos=point, scale=.30, tone='#e94978', lit=False)
                self.add(orb, .8)
                self.beam(point, Vec3(end.x, 1.6, end.z), '#d9446f', .08, .6)
        elif effect == 'resonance_final':
            doll = Entity(parent=self.root, position=(end.x, 3, end.z))
            part(doll, 'cube', scale=(.35, 1.0, .22), tone='#c69a58')
            part(doll, pos=(0, .65, 0), scale=.48, tone='#e1b876')
            part(doll, 'cube', (0, .24, 0), (1.15, .20, .20), '#d3ac68')
            self.add(doll, 1.1, spin=70)
            for i in range(8):
                angle = i*math.tau/8
                start = Vec3(end.x+math.cos(angle)*3, 1.7+math.sin(angle)*2, end.z)
                self.beam(start, Vec3(end.x, 2, end.z), '#ffd28c', .05, .75)
        elif effect == 'ratio_rush':
            for i in range(11):
                self.beam(Vec3(end.x-3+i*.6, .4, end.z), Vec3(end.x-3+i*.6, 3.5, end.z),
                          '#ffeb97' if i == 7 else '#9d8651', .06 if i == 7 else .014, .85)
            self.lightning(end, '#ff3554', 3, 8)
        elif effect == 'boogie_rush':
            for side in (-1, 1):
                self.beam(Vec3(end.x+side*4, 1.6, end.z-2), Vec3(end.x, 1.6, end.z),
                          '#ff7795' if side < 0 else '#e6a7ff', .22, .65)
            self.ring(pos, '#dfafff', 3, .6)
        elif effect == 'general_final':
            self.wheel_flash(pos, 3)
            self.arc(end, '#fff4c2', 4.7, .85, heading, 70)
            self.lightning(end, '#fff2b9', 4, 8)
        elif effect == 'weapon_rush':
            for i in range(4):
                self.arc(end, '#cbffbb', 2.8+i*.3, .7, heading+i*50, -65+i*40)
        elif effect == 'black_rush':
            self.lightning(end, '#ff274e', 3.5, 9)
            core = part(self.root, pos=(end.x, 1.6, end.z), scale=.8, tone='#171026', lit=False)
            self.add(core, .5, growth=1)
        else:
            self.arc(end, tone, 3.4, .65, heading, 45)
        self.burst(end, tone, 15)

    def _sync_projectiles(self, battle):
        ids = {p.uid for p in battle.projectiles}
        self._prune(self.projectiles, ids)
        for uid in list(self.projectile_frames):
            if uid not in ids:
                del self.projectile_frames[uid]
        for p in battle.projectiles:
            if p.uid not in self.projectiles:
                root = Entity(parent=self.root)
                tone = PALETTE.get(p.kind, '#e8d3ff')
                beam = p.kind in ('granite', 'granite_small', 'granite_max', 'blood', 'love_beam')
                slash = p.kind in ('dismantle', 'adaptive_slash')
                size = max(.15, p.radius*1.65)
                if slash:
                    part(root, crescent_mesh(150), scale=(size*2, 1, size), tone=tone,
                         rotation=(70, 0, 0), lit=False, double_sided=True)
                elif p.kind == 'nail':
                    part(root, 'cube', scale=(.05, .05, .85), tone='#ecedff', lit=False)
                    part(root, 'cube', (0, 0, -.4), (.17, .17, .055), '#efcc9c')
                else:
                    part(root, 'sphere', scale=(size, size, size*2.6 if beam else size), tone=tone, lit=False)
                    part(root, 'sphere', scale=(size*.45, size*.45, size*3 if beam else size*.55), tone='#fffce9', lit=False)
                    halo = part(root, 'sphere', scale=(size*1.5, size*1.5, size*2.8 if beam else size*1.5), tone=tone, lit=False)
                    halo.alpha = .13
                for i in range(2):
                    part(root, ring_mesh(32, .055), (0, 0, -.18-i*.42), size*(.7+i*.3), tone,
                         rotation=(90, 0, i*40), lit=False, double_sided=True)
                trails = []
                for i in range(5):
                    trail = part(self.root, 'sphere' if not slash else 'cube', scale=.1, tone=tone, lit=False)
                    trail.alpha = .24*(1-i/6)
                    trails.append(trail)
                root.trails = trails
                self.projectiles[p.uid] = root
                self.projectile_frames[p.uid] = []
            root = self.projectiles[p.uid]
            height = 2.65 if p.kind in ('granite', 'granite_small', 'granite_max') else 1.5
            root.position = (p.pos.x, height, p.pos.z)
            root.rotation_y = math.degrees(math.atan2(p.direction.x, p.direction.z))
            history = self.projectile_frames[p.uid]
            # A paused QTE must not continue growing the trail.
            current = Vec3(root.position)
            if not history or (current-history[0]).length() > .01:
                history.insert(0, current)
                del history[6:]
            for i, trail in enumerate(root.trails):
                trail.position = history[min(i+1, len(history)-1)]
                size = max(.10, p.radius*1.4)*(1-i/6)
                trail.scale = (size, size, size*1.8)
                trail.rotation_y = root.rotation_y

    def sync(self, battle, dt):
        self.frame_dt = dt
        super().sync(battle, dt)

    def _sync_domain(self, battle):
        domain = battle.domain
        if domain is not self.domain_identity:
            if self.domain_root:
                destroy(self.domain_root)
            self.domain_root = None
            self.domain_blades.clear()
            self.orbits.clear()
            self.domain_identity = domain
            self.domain_age = self.clock
            self.last_domain_pulse = self.clock
            if domain:
                self._build_domain(domain)
        if not domain:
            return
        dt = getattr(self, 'frame_dt', 0)
        for node, speed in self.orbits:
            node.rotation_y += speed*dt
        if domain['kind'] == 'mutual_love':
            for sword in domain.get('swords', ()):
                node = self.domain_blades.get(sword['uid'])
                if node:
                    node.enabled = sword['respawn'] <= 0
            if self.clock-self.last_domain_pulse >= .75:
                self.last_domain_pulse = self.clock
                target = battle.target(battle.fighters[domain['owner']])
                center = domain['center']
                if (target.pos-center).length() <= 10:
                    self.beam(Vec3(target.pos.x, .1, target.pos.z), Vec3(target.pos.x, 10, target.pos.z), '#fff1bb', .32, .42)
        elif domain['kind'] == 'shrine' and self.clock-self.last_domain_pulse >= .35:
            self.last_domain_pulse = self.clock
            target = battle.target(battle.fighters[domain['owner']])
            self.arc(target.pos, '#ffb6af', 2.7, .25, self.clock*100, 60)

    def _build_domain(self, domain):
        kind = domain['kind']
        center = domain.get('center')
        cx, cz = (center.x, center.z) if center else (0, 0)
        self.domain_root = root = Entity(parent=self.root, position=(cx, 0, cz))
        tone = PALETTE.get(kind, '#bddfff')
        floor = part(root, ring_mesh(96, 1), (0, .065, 0), 10, tone, lit=False, double_sided=True)
        floor.alpha = .11 if kind != 'shadow_domain' else .55
        for radius in (9.6, 10, 10.3):
            part(root, ring_mesh(96, .009), (0, .08, 0), radius, tone, lit=False, double_sided=True)
        orbit = Entity(parent=root)
        self.orbits.append((orbit, 7))
        for i in range(20):
            angle = i*math.tau/20
            x, z = math.cos(angle)*10, math.sin(angle)*10
            line = part(orbit, 'cube', (x, 1.4, z), (.025, 2.8, .025), tone, lit=False)
            line.alpha = .25
        if kind == 'mutual_love':
            for i in range(12):
                angle = i*math.tau/12
                x, z = math.cos(angle)*8.9, math.sin(angle)*8.9
                height = 2.5+(i % 3)*.65
                part(root, 'cube', (x, height/2, z), (.32, height, .35), '#d9bfa9', rotation=(0, i*30, 8))
                part(root, 'cube', (x, height*.76, z), (1.8, .28, .38), '#e9d6bf', rotation=(0, i*30, 8))
            # Mizuhiki ribbons encircle the field; intersecting gold/red strands.
            for strand in range(3):
                last = None
                for i in range(49):
                    angle = i*math.tau/48
                    point = (math.cos(angle)*10.4, 6.0+math.sin(angle*3+strand)*.7+strand*.18,
                             math.sin(angle)*10.4)
                    if last:
                        line = stroke(root, last, point, .045, '#cf536f' if strand != 1 else '#ffe9b1')
                        line.shader = None
                    last = point
            for sword in domain.get('swords', ()):
                p = sword['pos']
                blade = Entity(parent=root, position=(p.x-cx, .13, p.z-cz), rotation=(0, sword['uid']*33, -12))
                part(blade, 'cube', (0, .53, 0), (.09, 1.06, .04), '#ddf1ea', lit=False)
                part(blade, 'cube', (0, 1.12, 0), (.42, .055, .15), '#e4c58b')
                part(blade, 'cube', (0, 1.35, 0), (.10, .42, .075), '#503944')
                glow = part(blade, ring_mesh(40, .05), (0, .02, 0), .55, '#ffedba', lit=False, double_sided=True)
                glow.alpha = .8
                self.domain_blades[sword['uid']] = blade
        elif kind == 'void':
            part(root, 'sphere', (0, 7.2, 12), (6, 6, .9), '#080c19', lit=False)
            for i in range(4):
                halo = part(root, ring_mesh(96, .025 if i % 2 else .065), (0, 7.2, 11.35),
                            3.3+i*.43, '#e6faff' if i % 2 else '#76bcff',
                            rotation=(65+i*8, i*20, 0), lit=False, double_sided=True)
                self.orbits.append((halo, 4+i*3))
            for i in range(65):
                angle = i*2.399
                radius = 7+(i % 7)*.7
                part(root, 'sphere', (math.cos(angle)*radius, 2+(i % 13)*.53, math.sin(angle)*radius),
                     .025+(i % 3)*.015, '#bedaff', lit=False)
            for i in range(9):
                part(root, ring_mesh(64, .007), (0, 2.5+i*.4, 0), 7+i*.28,
                     '#79aff5', rotation=(i*6, 0, i*9), lit=False, double_sided=True)
        elif kind == 'shrine':
            shrine = Entity(parent=root, position=(0, 0, 7.5))
            for side in (-1, 1):
                part(shrine, 'cube', (side*2.2, 2, 0), (.5, 4, .6), '#9e3e4c')
                part(shrine, 'cube', (side*1.2, .9, .15), (.25, 1.8, .32), '#d4b7a1')
            for y, width in ((3.7, 5.7), (4.3, 4.9)):
                part(shrine, 'cube', (0, y, 0), (width, .23, 2.5), '#492332')
                for side in (-1, 1):
                    part(shrine, 'cube', (side*width*.43, y+.22, 0), (.95, .18, 2.6), '#934152', rotation=(0, 0, side*22))
            part(shrine, 'cube', (0, .2, 0), (5.7, .4, 3.1), '#362739')
            for i in range(9):
                skull = part(shrine, 'sphere', ((i-4)*.52, .58, -1.35), (.48, .49, .35), '#cfb8a3')
                for side in (-1, 1):
                    part(skull, 'sphere', (side*.17, .03, -.39), (.22, .27, .1), '#241726')
            for i in range(18):
                angle = i*math.tau/18
                line = stroke(root, (math.cos(angle)*3, .09, math.sin(angle)*3),
                              (math.cos(angle+.12)*10, .09, math.sin(angle+.12)*10), .035, '#e76f78')
                line.shader = None
        elif kind == 'shadow_domain':
            floor.color = tint('#111323')
            for i in range(18):
                angle = i*2.399
                radius = 2+i*.38
                puddle = part(root, ring_mesh(40, 1), (math.cos(angle)*radius, .10, math.sin(angle)*radius),
                              (1.3, 1, .9), '#241c3b', lit=False, double_sided=True)
                for side in (-1, 1):
                    part(root, 'sphere', (puddle.x+side*.18, .14, puddle.z), (.085, .04, .10), '#d9a9ff', lit=False)
            for i in range(8):
                angle = i*math.tau/8
                x, z = math.cos(angle)*9, math.sin(angle)*9
                part(root, 'sphere', (x, 1.5, z), (.5, 3, .5), '#282239', rotation=(12, 0, i*9))
                part(root, 'sphere', (x, 2.7, z), (.9, .6, .8), '#302542')
        elif kind == 'soul_domain':
            for i in range(12):
                angle = i*math.tau/12
                x, z = math.cos(angle)*8.7, math.sin(angle)*8.7
                hand = Entity(parent=root, position=(x, 1.7+(i % 2)*.8, z), rotation=(0, -i*30, 10))
                part(hand, pos=(0, 0, 0), scale=(.95, 1.3, .28), tone='#7eaaa7')
                for j in range(5):
                    part(hand, pos=((j-2)*.20, .85 if j else .28, 0),
                         scale=(.18, 1.15 if j else .6, .20), tone='#bfd2c4', rotation=(0, 0, (j-2)*-6))
                for j in range(5):
                    part(hand, 'cube', ((j-2)*.17, .06, .15), (.035, .16, .025), '#344c54')
            for i in range(5):
                ring = part(root, ring_mesh(64, .024), (0, 4.8+i*.35, 0), 5+i*.8, '#718f92',
                            rotation=(9*i, 0, 0), lit=False, double_sided=True)
                self.orbits.append((ring, 5-i*2))
        elif kind == 'volcano_domain':
            from ursina.models.procedural.cone import Cone
            for i in range(14):
                angle = i*math.tau/14
                x, z = math.cos(angle)*9.1, math.sin(angle)*9.1
                part(root, Cone(7), (x, 1.7, z), (2.5, 3.4+(i % 3)*.6, 2.5), '#653742')
                part(root, ring_mesh(24, .5), (x, .12, z), 1.6, '#ff9356', lit=False)
                start = (math.cos(angle)*2.2, .11, math.sin(angle)*2.2)
                line = stroke(root, start, (x, .11, z), .055, '#ffb15c')
                line.shader = None
            for i in range(30):
                angle = i*2.399
                part(root, 'cube', (math.cos(angle)*7, 2+(i % 6)*.65, math.sin(angle)*7),
                     (.05, .13, .05), '#ffb267', rotation=(20, i*15, 30), lit=False)

    @staticmethod
    def _prune(mapping, ids):
        for uid in list(mapping):
            if uid not in ids:
                node = mapping.pop(uid)
                for trail in getattr(node, 'trails', ()):
                    destroy(trail)
                destroy(node)
