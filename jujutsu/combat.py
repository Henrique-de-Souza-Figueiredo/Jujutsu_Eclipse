"""Deterministic combat simulation, independent of Ursina and rendering."""
from __future__ import annotations

from dataclasses import dataclass, field
import math
import random

from .roster import BY_ID, DOMAIN_KINDS


@dataclass
class V2:
    x: float = 0
    z: float = 0

    def __add__(self, other):
        return V2(self.x + other.x, self.z + other.z)

    def __sub__(self, other):
        return V2(self.x - other.x, self.z - other.z)

    def __mul__(self, value):
        return V2(self.x * value, self.z * value)

    def length(self):
        return math.hypot(self.x, self.z)

    def unit(self):
        length = self.length()
        return self * (1 / length) if length > .0001 else V2(0, 1)

    def copy(self):
        return V2(self.x, self.z)


def segment_distance(point, start, end):
    delta = end - start
    length2 = delta.x ** 2 + delta.z ** 2
    t = max(0, min(1, ((point.x-start.x)*delta.x + (point.z-start.z)*delta.z) / max(.0001, length2)))
    return (point - (start + delta*t)).length()


@dataclass
class Fighter:
    character_id: str
    side: int
    pos: V2
    hp: float = 0
    energy: float = 100
    stamina: float = 100
    guard: float = 100
    ultimate: float = 0
    cooldowns: list = field(default_factory=lambda: [0.0] * 4)
    statuses: dict = field(default_factory=dict)
    marks: dict = field(default_factory=dict)
    blocking: bool = False
    charging: bool = False
    parry: float = 0
    invulnerable: float = 0
    stun: float = 0
    lock: float = 0
    action: str = 'idle'
    action_time: float = 0
    serial: int = 0
    combo: int = 0
    combo_window: float = 0
    height: float = 0
    vertical_speed: float = 0
    dash_time: float = 0
    dash_dir: V2 = field(default_factory=V2)
    move: V2 = field(default_factory=V2)
    blood: int = 0
    weapon: int = 0
    ai_timer: float = .8
    ai_guard: float = 0
    hits: int = 0
    damage_dealt: float = 0
    best_combo: int = 0
    chain: int = 0
    chain_timer: float = 0

    def __post_init__(self):
        self.hp = self.spec.health

    @property
    def spec(self):
        return BY_ID[self.character_id]

    @property
    def resource(self):
        return self.stamina if self.character_id == 'maki' else self.energy

    def has(self, status):
        return self.statuses.get(status, 0) > 0


@dataclass
class Projectile:
    uid: int
    owner: int
    pos: V2
    direction: V2
    speed: float
    damage: float
    kind: str
    radius: float = .4
    life: float = 2.5
    homing: bool = False
    piercing: bool = False


@dataclass
class Zone:
    uid: int
    owner: int
    pos: V2
    radius: float
    delay: float
    duration: float
    damage: float
    kind: str
    tick: float = 0
    activated: bool = False


@dataclass
class Summon:
    uid: int
    owner: int
    pos: V2
    kind: str
    life: float
    attack_cd: float = .5


@dataclass
class QTE:
    actor: int
    kind: str
    title: str
    mode: str
    payload: object = None
    elapsed: float = 0
    duration: float = 2.2
    target: float = .7
    width: float = .10
    keys: tuple = ('w', 'a', 's', 'd')
    index: int = 0
    mistakes: int = 0
    result: float | None = None

    @property
    def progress(self):
        return min(1, self.elapsed / self.duration)

    def press(self, key):
        if self.result is not None:
            return
        if self.mode == 'timing':
            if key == 'space':
                distance = abs(self.progress - self.target)
                self.result = max(0, 1 - distance / (self.width * 2))
        elif key in ('w', 'a', 's', 'd', 'j', 'k'):
            if key == self.keys[self.index]:
                self.index += 1
                if self.index == len(self.keys):
                    self.result = max(.35, 1 - self.mistakes * .2)
            else:
                self.mistakes += 1


class Battle:
    def __init__(self, player='gojo', enemy='sukuna', difficulty='Normal', training=False, seed=11):
        self.rng = random.Random(seed)
        self.fighters = [Fighter(player, 0, V2(-4, -1)), Fighter(enemy, 1, V2(4, 1))]
        self.difficulty = difficulty
        self.training = training
        self.time_left = 99.0
        self.elapsed = 0.0
        self.finished = False
        self.winner = None
        self.events = []
        self.projectiles = []
        self.zones = []
        self.summons = []
        self.pending = []
        self.qte = None
        self.domain = None
        self.next_uid = 1
        if training:
            self.fighters[0].ultimate = 100

    def uid(self):
        self.next_uid += 1
        return self.next_uid

    def emit(self, kind, fighter=None, **data):
        if fighter is not None:
            data.setdefault('owner', fighter.side)
            data.setdefault('pos', fighter.pos.copy())
        self.events.append(dict(kind=kind, **data))

    def drain_events(self):
        events, self.events = self.events, []
        return events

    def target(self, fighter):
        return self.fighters[1 - fighter.side]

    def distance(self, fighter):
        return (fighter.pos - self.target(fighter).pos).length()

    def can_act(self, fighter):
        return not (self.finished or self.qte or fighter.hp <= 0 or fighter.stun > 0 or fighter.lock > 0)

    def notify(self, fighter, text):
        if fighter.side == 0:
            self.emit('notice', fighter, text=text)
        return False

    def animate(self, fighter, action, duration):
        fighter.action, fighter.action_time, fighter.lock = action, 0, duration
        fighter.serial += 1
        fighter.blocking = fighter.charging = False

    def schedule(self, fighter, delay, kind, data, interruptible=True):
        self.pending.append([delay, fighter.side, fighter.serial if interruptible else None, kind, data])

    def set_guard(self, side, held):
        fighter = self.fighters[side]
        active = held and fighter.stun <= 0 and fighter.lock <= 0 and fighter.guard > 0
        if active and not fighter.blocking:
            fighter.parry = .16
        fighter.blocking = active
        if active:
            fighter.charging = False

    def attack(self, side, heavy=False):
        fighter = self.fighters[side]
        if not self.can_act(fighter):
            return False
        if fighter.stamina < (16 if heavy else 6):
            return self.notify(fighter, 'Sem vigor. Crie distância para recuperar.')
        fighter.stamina -= 16 if heavy else 6
        fighter.combo = (fighter.combo % 3 + 1) if fighter.combo_window > 0 else 1
        fighter.combo_window = 1.15
        ender = fighter.combo == 3
        startup = .25 if heavy else .13
        self.animate(fighter, 'heavy' if heavy else f'punch{fighter.combo}', .6 if heavy else .34)
        reach = fighter.spec.reach + (.5 if heavy else 0)
        if fighter.character_id == 'maki' and fighter.weapon == 1:
            reach -= .7
        self.schedule(fighter, startup, 'melee', dict(damage=(19 if heavy else 9) + (5 if ender else 0),
                      reach=reach, heavy=heavy or ender, soul=fighter.character_id == 'yuji', label='COMBO' if ender else ''))
        self.emit('swing', fighter, heavy=heavy, reach=reach)
        return True

    def dodge(self, side, direction=None):
        fighter = self.fighters[side]
        if not self.can_act(fighter) or fighter.has('root'):
            return False
        cost = 16 if fighter.character_id == 'maki' else 24
        if fighter.stamina < cost:
            return self.notify(fighter, 'Vigor insuficiente para esquivar.')
        fighter.stamina -= cost
        fighter.dash_dir = (direction if direction and direction.length() > .1 else fighter.pos - self.target(fighter).pos).unit()
        fighter.dash_time, fighter.invulnerable = .22, .28
        self.animate(fighter, 'dodge', .28)
        self.emit('dodge', fighter)
        return True

    def jump(self, side):
        fighter = self.fighters[side]
        if self.can_act(fighter) and fighter.height == 0 and not fighter.has('root'):
            fighter.vertical_speed = 7
            self.emit('jump', fighter)
            return True
        return False

    def cast(self, side, slot):
        fighter = self.fighters[side]
        if not self.can_act(fighter):
            return False
        tech = fighter.spec.skills[slot]
        if fighter.cooldowns[slot] > 0:
            return self.notify(fighter, f'{tech.name}: recarga {fighter.cooldowns[slot]:.1f}s')
        kind = tech.mechanic
        target = self.target(fighter)
        if tech.reach <= 5.5 and self.distance(fighter) > tech.reach:
            return self.notify(fighter, f'Aproxime-se: alcance de {tech.reach:g} m.')
        if kind == 'purple' and not (fighter.has('blue_ready') and fighter.has('red_ready')):
            return self.notify(fighter, 'Roxo: use Azul (Q) e Vermelho (E) em até 8 s.')
        if kind == 'fuga' and not (fighter.has('dismantle_ready') and fighter.has('cleave_ready')):
            return self.notify(fighter, 'Fuga: use Desmantelar (Q) e Clivar (E) primeiro.')
        if kind in ('resonance', 'hairpin') and target.marks.get('nails', 0) == 0:
            return self.notify(fighter, 'Sem ligação: acerte um prego com Q primeiro.')
        if kind in ('piercing', 'supernova') and fighter.blood == 0:
            return self.notify(fighter, 'Comprima sangue com Q antes de usar esta técnica.')
        if kind == 'convergence' and fighter.blood >= 3:
            return self.notify(fighter, 'Convergência completa: use E ou R.')
        if kind == 'copy' and not fighter.has('rika'):
            return self.notify(fighter, 'Cópia exige Rika: invoque-a com E.')
        if kind in ('heal', 'reshape') and fighter.hp >= fighter.spec.health:
            return self.notify(fighter, 'Vida já está completa.')
        cost = tech.cost * (.85 if fighter.character_id == 'gojo' else 1)
        if fighter.resource < cost:
            return self.notify(fighter, f'Recurso insuficiente: precisa de {cost:g}. Segure G.')
        if fighter.character_id == 'maki':
            fighter.stamina -= cost
        else:
            fighter.energy -= cost
        fighter.cooldowns[slot] = tech.cooldown
        self.animate(fighter, 'cast', .52)
        self.emit('cast', fighter, text=tech.name, effect=kind)
        if kind in ('blue', 'red', 'dismantle', 'cleave'):
            fighter.statuses[kind + '_ready'] = 8 if kind in ('blue', 'red') else 12
        if kind in ('purple', 'fuga'):
            for status in ('blue_ready', 'red_ready', 'dismantle_ready', 'cleave_ready'):
                fighter.statuses.pop(status, None)
        if kind in ('black_flash', 'ratio', 'purple', 'fuga'):
            if side == 0:
                self.qte = QTE(side, 'skill', tech.name.upper(), 'timing', payload=kind,
                               target=.7 if kind == 'ratio' else .66,
                               width=.14 if self.difficulty == 'Fácil' else .10)
            else:
                self.schedule(fighter, .5, 'skill', (kind, self.rng.uniform(.35, .95)))
        else:
            self.schedule(fighter, .12, 'skill', (kind, 1.0))
        return True

    def ultimate(self, side):
        fighter = self.fighters[side]
        if not self.can_act(fighter):
            return False
        if fighter.ultimate < 100:
            return self.notify(fighter, 'Supremo exige 100%. Acerte golpes ou receba dano para carregar.')
        fighter.ultimate = 0
        self.animate(fighter, 'ultimate', 1.0)
        target = self.target(fighter)
        if side == 0:
            kind = 'ultimate'
            title = fighter.spec.ultimate.upper()
        elif target.ultimate >= 100 and target.spec.ultimate_kind in DOMAIN_KINDS and fighter.spec.ultimate_kind in DOMAIN_KINDS:
            kind = 'clash'
            target.ultimate = 0
            title = 'CHOQUE DE DOMÍNIOS'
        else:
            kind = 'defend'
            title = 'ROMPA A PRESSÃO / DEFENDA-SE'
        keys = tuple(self.rng.sample(('w', 'a', 's', 'd', 'j', 'k'), 5))
        self.qte = QTE(side, kind, title, 'sequence', keys=keys,
                       duration=4.5 if self.difficulty == 'Fácil' else 3.6)
        self.emit('cinematic', fighter, text=fighter.spec.ultimate)
        return True

    def qte_input(self, key):
        if self.qte:
            self.qte.press(key)

    def _resolve_qte(self):
        qte, self.qte = self.qte, None
        fighter = self.fighters[qte.actor]
        grade = qte.result or 0
        text = 'PERFEITO' if grade >= .85 else ('SUCESSO' if grade >= .5 else 'FALHOU')
        self.emit('qte_result', fighter, text=text, grade=grade)
        if qte.kind == 'skill':
            self._skill(fighter, qte.payload, grade)
        elif qte.kind == 'clash' and grade >= .6:
            self._finisher(self.target(fighter), grade)
        else:
            if qte.kind in ('defend', 'clash'):
                self.target(fighter).statuses['domain_guard'] = 7
                grade = 1 - grade * .8
            self._finisher(fighter, grade)

    def _projectile(self, fighter, kind, damage, speed=15, radius=.4, homing=False, angle=0, piercing=False):
        direction = (self.target(fighter).pos - fighter.pos).unit()
        if angle:
            direction = V2(direction.x*math.cos(angle) - direction.z*math.sin(angle),
                           direction.x*math.sin(angle) + direction.z*math.cos(angle))
        self.projectiles.append(Projectile(self.uid(), fighter.side, fighter.pos + direction*.9,
                                          direction, speed, damage, kind, radius, 3, homing, piercing))

    def _zone(self, fighter, kind, damage, radius, delay, duration=.1, position=None):
        self.zones.append(Zone(self.uid(), fighter.side, (position or self.target(fighter).pos).copy(),
                               radius, delay, duration, damage, kind))

    def _summon(self, fighter, kind, duration):
        self.summons.append(Summon(self.uid(), fighter.side, fighter.pos + V2(1, .4), kind, duration))
        self.emit('summon', fighter, effect=kind)

    def _melee(self, fighter, damage, reach, heavy=False, soul=False, label='', knockback=1):
        target = self.target(fighter)
        if self.distance(fighter) <= reach and abs(fighter.height-target.height) < 1.6:
            return self.damage(fighter, target, damage, heavy=heavy, soul=soul, label=label, knockback=knockback)
        self.emit('miss', fighter)
        return 0

    def _skill(self, f, kind, quality=1):
        t = self.target(f)
        factor = .65 + quality*.85
        if kind == 'blue':
            self._zone(f, 'blue', 16, 3.2, .5)
        elif kind in ('red', 'purple', 'dismantle', 'fuga'):
            damage, speed, radius = {'red': (25, 14, .6), 'purple': (46*factor, 13, 1.1),
                                      'dismantle': (21, 21, .65), 'fuga': (43*factor, 17, .8)}[kind]
            self._projectile(f, kind, damage, speed, radius, piercing=kind in ('purple', 'dismantle'))
        elif kind == 'infinity':
            f.statuses['infinity'] = 2.6
        elif kind == 'divergent':
            if self._melee(f, 13, 3, soul=True):
                self.schedule(f, .48, 'echo', 15, interruptible=False)
        elif kind in ('black_flash', 'ratio'):
            self._melee(f, (31 if kind == 'black_flash' else 29)*factor, 3.6, heavy=True,
                        soul=kind == 'black_flash', label='BLACK FLASH' if kind == 'black_flash' else '7 : 3', knockback=2)
        elif kind in ('rush', 'shoulder', 'katana', 'thrust'):
            direction = (t.pos-f.pos).unit()
            f.pos += direction * max(0, min(5, self.distance(f)-1.7))
            if kind == 'shoulder':
                f.statuses['armor'] = .8
            self._melee(f, 24 if kind in ('shoulder', 'thrust') else 21, 4.5, heavy=True, knockback=2)
        elif kind == 'focus':
            f.statuses['empower'] = 6
            f.stamina = min(100, f.stamina+35)
        elif kind == 'dog':
            self._summon(f, 'dog', 8.75 if f.has('shadow_domain') else 7)
        elif kind == 'nue':
            self._zone(f, 'nue', 25, 2.7, .65)
        elif kind == 'toad':
            self._projectile(f, 'toad', 9, 12, .55)
        elif kind == 'shadowstep':
            f.pos = t.pos + (t.pos-f.pos).unit()*2
            f.invulnerable = .55
            self.emit('teleport', f)
        elif kind == 'nails':
            for angle in (-.075, 0, .075):
                self._projectile(f, 'nail', 6, 19, .25, angle=angle)
        elif kind in ('resonance', 'hairpin'):
            nails = t.marks.get('nails', 0)
            self.damage(f, t, 12+nails*(7 if kind == 'hairpin' else 3), soul=True, unblockable=True,
                        label='GRAMPO' if kind == 'hairpin' else 'RESSONÂNCIA')
            if kind == 'hairpin':
                t.marks['nails'] = 0
            self.emit('resonance', f, pos=t.pos.copy())
        elif kind == 'nail_trap':
            self._zone(f, 'nail_trap', 9, 2.7, .75, 5)
        elif kind == 'rika':
            self._summon(f, 'rika', 8)
            f.statuses['rika'] = 8
        elif kind == 'copy':
            copied = t.spec.skills[0].mechanic
            if t.character_id == 'maki':
                t.stun = 1.3
                self.damage(f, t, 13, unblockable=True, label='PARE!')
            elif copied == 'convergence':
                self._projectile(f, 'blood', 29, 30, .35, piercing=True)
            else:
                self._skill(f, copied, .8)
            self.emit('notice', f, text='Cópia: ' + ('Fala Amaldiçoada' if t.character_id == 'maki' else t.spec.skills[0].name))
        elif kind in ('heal', 'reshape'):
            amount = 30 if kind == 'reshape' else 36
            f.hp = min(f.spec.health, f.hp + amount)
            if kind == 'reshape':
                f.statuses.pop('root', None)
                f.statuses.pop('slow', None)
            self.emit('heal', f, amount=amount)
        elif kind == 'sweep':
            self._melee(f, 26, 4.5 if f.weapon == 0 else 3.5, heavy=True, knockback=2)
        elif kind == 'counter':
            f.statuses['counter'] = 1.2
            f.lock = .15
        elif kind == 'weapon':
            f.weapon = 1 - f.weapon
            self.emit('notice', f, text='ESPADA / mais dano' if f.weapon else 'NAGINATA / mais alcance')
        elif kind == 'collapse':
            self._zone(f, 'collapse', 31, 3.2, .7)
        elif kind == 'overtime':
            f.statuses['empower'] = f.statuses['armor'] = 7
        elif kind == 'weakpoint':
            t.statuses['weakpoint'] = 6
        elif kind == 'swap':
            f.pos, t.pos = t.pos.copy(), f.pos.copy()
            f.statuses['rhythm'] = 3
            t.stun = .35
            self.emit('swap', f, end=t.pos.copy())
        elif kind == 'feint':
            t.blocking = False
            t.stun = .75
            f.invulnerable = .3
            self.emit('feint', f)
        elif kind == 'reinforce':
            f.statuses['armor'] = f.statuses['empower'] = 5
        elif kind == 'cleave':
            self._melee(f, 27 + t.guard*.06, 3.2, heavy=True, knockback=.6)
        elif kind == 'soul_touch':
            if self._melee(f, 18, 3, soul=True):
                t.marks['soul'] = t.marks.get('soul', 0)+1
                if t.marks['soul'] >= 3:
                    t.marks['soul'] = 0
                    self.damage(f, t, 26, soul=True, unblockable=True, label='RUPTURA DA ALMA')
        elif kind == 'morph_blade':
            self._melee(f, 26, 5.5, heavy=True)
            self.emit('blade', f, end=t.pos.copy())
        elif kind == 'soul_armor':
            f.statuses['armor'] = f.statuses['empower'] = f.statuses['morph'] = 6
        elif kind == 'fireball':
            for angle in (-.15, 0, .15):
                self._projectile(f, 'fire', 11, 12, .5, angle=angle)
        elif kind == 'volcano':
            self._zone(f, 'volcano', 30, 3, .8, 1)
        elif kind == 'meteor':
            self._zone(f, 'meteor', 58, 4.6, 1.7)
        elif kind == 'embers':
            for angle in (-.7, 0, .7):
                self._projectile(f, 'ember', 10, 7, .35, homing=True, angle=angle)
        elif kind == 'convergence':
            f.blood = min(3, f.blood+1)
        elif kind == 'piercing':
            f.blood -= 1
            self._projectile(f, 'blood', 32, 34, .4, piercing=True)
        elif kind == 'supernova':
            self._zone(f, 'supernova', 15+14*f.blood, 4.2, .35)
            f.blood = 0
        elif kind == 'red_scale':
            f.statuses['haste'] = f.statuses['empower'] = f.statuses['armor'] = 6

    def _finisher(self, fighter, quality):
        kind = fighter.spec.ultimate_kind
        target = self.target(fighter)
        factor = .4 + quality*.6
        fighter.lock = .65
        if kind in DOMAIN_KINDS:
            # A new domain replaces the old field, including its damage zones.
            self.zones = [z for z in self.zones if z.kind not in DOMAIN_KINDS]
            self.domain = dict(owner=fighter.side, kind=kind, remaining=6, quality=quality)
            fighter.statuses[kind] = 6
            self._zone(fighter, kind, 10*factor, 10, .35, 5.6, position=fighter.pos)
            if kind == 'void':
                target.stun = .8 + 1.8*quality
            if kind == 'shadow_domain':
                self._summon(fighter, 'dog', 8.75)
                self._summon(fighter, 'dog', 8.75)
            self.emit('domain', fighter, text=fighter.spec.ultimate, effect=kind)
        else:
            fighter.pos = target.pos + (fighter.pos-target.pos).unit()*2.3
            self.damage(fighter, target, (77 if kind == 'love_beam' else 68)*factor,
                        soul=kind in ('black_rush', 'resonance_final'), unblockable=True,
                        domain=True, label=fighter.spec.ultimate, knockback=3)
            self.emit('finisher', fighter, end=target.pos.copy(), effect=kind)
            if kind == 'boogie_rush':
                self._summon(fighter, 'brother', 3)
        self.emit('shake', fighter, strength=.25)

    def damage(self, source, target, amount, heavy=False, soul=False, unblockable=False,
               label='', knockback=1, domain=False, dot=False):
        if self.finished or target.hp <= 0 or (target.invulnerable > 0 and not domain):
            return 0
        if target.has('infinity') and not soul and not domain:
            self.emit('barrier', target, text='INFINITO')
            return 0
        if target.has('counter') and not domain and not dot and not unblockable:
            target.statuses.pop('counter')
            source.stun = .7
            self.emit('parry', target, text='CONTRA-ATAQUE')
            self.damage(target, source, 25, heavy=True, unblockable=True, knockback=2)
            return 0
        if target.blocking and target.parry > 0 and not unblockable and not domain:
            target.parry = 0
            source.stun = .55
            source.serial += 1
            target.ultimate = min(100, target.ultimate+8)
            self.emit('parry', target, text='DEFESA PERFEITA')
            return 0
        amount *= source.spec.power
        if source.has('empower'):
            amount *= 1.22
        if source.character_id == 'nanami' and source.hp < source.spec.health*.5:
            amount *= 1.18
        if source.character_id == 'maki' and source.weapon:
            amount *= 1.15
        if source.has('rhythm') and not dot:
            amount *= 1.35
            source.statuses.pop('rhythm', None)
        if target.has('weakpoint'):
            amount *= 1.2
        if target.character_id == 'mahito' and not soul:
            amount *= .82
        if target.has('armor') and not soul:
            amount *= .7
        if target.has('domain_guard') and domain:
            amount *= .65
        blocked = target.blocking and not unblockable and not domain
        if blocked:
            target.guard -= amount*(2.2 if heavy else 1.2)
            amount *= .22
            knockback *= .25
            if target.guard <= 0:
                target.guard = 0
                target.blocking = False
                target.stun = 1.1
                target.serial += 1
                self.emit('break', target, text='GUARDA QUEBRADA')
        elif not dot:
            target.stun = max(target.stun, .16 if target.has('armor') else (.4 if heavy else .22))
            if not target.has('armor'):
                target.serial += 1
            target.charging = False
            target.action, target.action_time = 'hit', 0
            target.pos += (target.pos-source.pos).unit()*knockback
        amount = min(target.hp, amount)
        target.hp = max(0, target.hp-amount)
        source.damage_dealt += amount
        source.ultimate = min(100, source.ultimate+amount*.5)
        target.ultimate = min(100, target.ultimate+amount*.32)
        if not dot:
            source.hits += 1
            source.chain = source.chain+1 if source.chain_timer > 0 else 1
            source.chain_timer = 1.8
            source.best_combo = max(source.best_combo, source.chain)
            source.energy = min(100, source.energy+2)
            self.emit('hit', source, pos=target.pos.copy(), target=target.side, amount=round(amount),
                      text=label, blocked=blocked, soul=soul, heavy=heavy)
        if target.hp == 0:
            if self.training:
                target.hp = target.spec.health
                target.marks.clear()
                self.emit('notice', self.fighters[0], text='Treino: vida do alvo restaurada.')
            else:
                self.finish(source.side)
        return amount

    def finish(self, winner):
        if self.finished:
            return
        self.finished, self.winner = True, winner
        self.pending.clear()
        self.projectiles.clear()
        self.zones.clear()
        self.summons.clear()
        self.qte = self.domain = None
        for f in self.fighters:
            f.blocking = f.charging = False
            f.move = V2()
        self.emit('round_end', self.fighters[winner] if winner is not None else None)

    def restore_training(self):
        if not self.training:
            return
        for f in self.fighters:
            f.hp, f.energy, f.stamina, f.guard, f.ultimate = f.spec.health, 100, 100, 100, 100
            f.cooldowns = [0.] * 4
            f.statuses.clear()
            f.marks.clear()
            f.stun = f.lock = 0
            f.invulnerable = f.parry = f.dash_time = 0
            f.blood = f.weapon = f.combo = f.chain = 0
            f.combo_window = f.chain_timer = 0
            f.height = f.vertical_speed = 0
            f.action = 'idle'
            f.action_time = 0
            f.move = V2()
            f.serial += 1
            f.blocking = f.charging = False
        self.pending.clear()
        self.projectiles.clear()
        self.zones.clear()
        self.summons.clear()
        self.qte = self.domain = None

    def step(self, real_dt, ai=True):
        if self.finished:
            return
        real_dt = min(.1, max(0, real_dt))
        if self.qte:
            self.qte.elapsed += real_dt
            if self.qte.elapsed >= self.qte.duration and self.qte.result is None:
                self.qte.result = (self.qte.index / len(self.qte.keys))*.55 if self.qte.mode == 'sequence' else 0
            if self.qte.result is not None:
                self._resolve_qte()
            # Freeze combat completely during input prompts. QTE uses real time.
            return
        dt = real_dt
        self.elapsed += dt
        if not self.training:
            self.time_left = max(0, self.time_left-dt)
            if self.time_left <= 0:
                fractions = [f.hp / f.spec.health for f in self.fighters]
                self.finish(None if abs(fractions[0]-fractions[1]) < .001 else (0 if fractions[0] > fractions[1] else 1))
                return
        for f in self.fighters:
            self._tick_fighter(f, dt)
        if ai and not self.training:
            self._ai(self.fighters[1], dt)
        ready = []
        for entry in self.pending:
            entry[0] -= dt
            if entry[0] <= 0:
                ready.append(entry)
        self.pending = [entry for entry in self.pending if entry[0] > 0]
        for _, side, serial, kind, data in ready:
            if self.finished:
                break
            f = self.fighters[side]
            if serial is not None and serial != f.serial:
                continue
            if kind == 'melee':
                self._melee(f, **data)
            elif kind == 'echo':
                self.damage(f, self.target(f), data, soul=True, label='IMPACTO DIVERGENTE')
            elif kind == 'skill':
                self._skill(f, *data)
        if self.finished:
            return
        self._tick_projectiles(dt)
        self._tick_zones(dt)
        self._tick_summons(dt)
        if self.domain:
            self.domain['remaining'] -= dt
            if self.domain['remaining'] <= 0:
                self.domain = None
        # Bounds and separation are applied after every kind of displacement.
        for f in self.fighters:
            length = f.pos.length()
            if length > 12.7:
                f.pos = f.pos * (12.7/length)
        a, b = self.fighters
        diff = b.pos-a.pos
        if diff.length() < 1.15:
            correction = diff.unit() * ((1.15-diff.length())*.5)
            a.pos -= correction
            b.pos += correction

    def _tick_fighter(self, f, dt):
        for attr in ('stun', 'lock', 'invulnerable', 'parry', 'combo_window', 'chain_timer'):
            setattr(f, attr, max(0, getattr(f, attr)-dt))
        f.cooldowns = [max(0, cd-dt) for cd in f.cooldowns]
        f.statuses = {key: value-dt for key, value in f.statuses.items() if value > dt}
        f.action_time += dt
        if f.lock <= 0 and f.stun <= 0:
            f.action = 'guard' if f.blocking else ('charge' if f.charging else ('run' if f.move.length() > .1 else 'idle'))
        regen = 24 if f.character_id in ('yuji', 'maki') else 18
        f.stamina = min(100, f.stamina + dt * (3 if f.blocking or f.lock > 0 else regen))
        f.guard = min(100, f.guard + dt * (0 if f.blocking else 16))
        f.energy = min(100, f.energy + dt * (4.1 if f.character_id == 'yuta' else 3.1))
        if f.charging and f.stun <= 0 and f.lock <= 0 and not f.blocking:
            f.energy = min(100, f.energy + dt*19)
            if f.character_id == 'maki':
                f.stamina = min(100, f.stamina+dt*25)
        if f.has('burn'):
            self.damage(self.target(f), f, dt*3, dot=True, knockback=0)
        if self.training and f.side == 0:
            f.ultimate = min(100, f.ultimate+dt*12)
        if f.height > 0 or f.vertical_speed > 0:
            f.vertical_speed -= dt*19
            f.height = max(0, f.height + f.vertical_speed*dt)
            if f.height == 0:
                f.vertical_speed = 0
        if f.dash_time > 0:
            f.dash_time -= dt
            f.pos += f.dash_dir * dt*19
        elif f.stun <= 0 and f.lock <= .05 and not f.has('root') and not f.charging:
            speed = f.spec.speed * (.36 if f.blocking else 1) * (1.28 if f.has('haste') else 1)
            f.pos += f.move.unit()*dt*speed if f.move.length() > .01 else V2()

    def _tick_projectiles(self, dt):
        for p in self.projectiles[:]:
            if self.finished:
                return
            f = self.fighters[p.owner]
            t = self.target(f)
            start = p.pos.copy()
            if p.homing:
                desired = (t.pos-p.pos).unit()
                p.direction = (p.direction*(1-dt*3)+desired*dt*3).unit()
            p.pos += p.direction*dt*p.speed
            p.life -= dt
            if segment_distance(t.pos, start, p.pos) < .65+p.radius and t.height < 1.4:
                hit = self.damage(f, t, p.damage, heavy=p.kind in ('red', 'purple'),
                                  unblockable=p.piercing, knockback=3 if p.kind == 'red' else .5)
                if hit:
                    if p.kind == 'nail':
                        t.marks['nails'] = min(6, t.marks.get('nails', 0)+1)
                    elif p.kind == 'toad':
                        t.statuses['root'] = 1.7
                    elif p.kind in ('fire', 'ember', 'fuga'):
                        t.statuses['burn'] = 3
                p.life = 0
            if p.life <= 0 or p.pos.length() > 22:
                if p in self.projectiles:
                    self.projectiles.remove(p)

    def _tick_zones(self, dt):
        for z in self.zones[:]:
            if self.finished:
                return
            z.delay -= dt
            if z.delay > 0:
                continue
            if not z.activated:
                z.activated = True
                self.emit('eruption', self.fighters[z.owner], pos=z.pos.copy(), effect=z.kind, radius=z.radius)
            z.duration -= dt
            z.tick -= dt
            f = self.fighters[z.owner]
            t = self.target(f)
            is_domain = z.kind in DOMAIN_KINDS
            if z.tick <= 0:
                z.tick = .75
                if (t.pos-z.pos).length() <= z.radius and (t.height < .8 or is_domain or z.kind in ('nue', 'meteor')):
                    hit = self.damage(f, t, z.damage, heavy=z.kind in ('meteor', 'collapse'),
                                      soul=z.kind == 'soul_domain', domain=is_domain,
                                      unblockable=is_domain, knockback=0 if is_domain else .5)
                    if hit:
                        if z.kind == 'blue':
                            t.pos = f.pos + (t.pos-f.pos).unit()*2.4
                        elif z.kind == 'nue':
                            t.stun = .9
                        elif z.kind == 'nail_trap':
                            t.marks['nails'] = min(6, t.marks.get('nails', 0)+1)
                            t.statuses['root'] = .5
                        elif z.kind in ('volcano', 'volcano_domain', 'meteor'):
                            t.statuses['burn'] = 3
            if z.duration <= 0 and z in self.zones:
                self.zones.remove(z)

    def _tick_summons(self, dt):
        for summon in self.summons[:]:
            if self.finished:
                return
            summon.life -= dt
            summon.attack_cd -= dt
            f = self.fighters[summon.owner]
            t = self.target(f)
            delta = t.pos-summon.pos
            if delta.length() > 1.4:
                summon.pos += delta.unit()*dt*(6.2 if summon.kind == 'dog' else 4.8)
            if delta.length() < 2 and summon.attack_cd <= 0:
                self.damage(f, t, 8 if summon.kind == 'dog' else 13, knockback=.15)
                summon.attack_cd = 1.2
                self.emit('summon_hit', f, pos=summon.pos.copy(), effect=summon.kind)
            if summon.life <= 0 and summon in self.summons:
                self.summons.remove(summon)

    def _ai(self, f, dt):
        t = self.target(f)
        distance = self.distance(f)
        f.ai_timer -= dt
        f.ai_guard = max(0, f.ai_guard-dt)
        self.set_guard(f.side, f.ai_guard > 0)
        direction = (t.pos-f.pos).unit()
        ranged = f.character_id in ('gojo', 'nobara', 'megumi', 'choso', 'jogo')
        desired = 5.5 if ranged and f.energy > 25 else 2.1
        if distance > desired+.6:
            f.move = direction
        elif distance < desired-1:
            f.move = direction * -.6
        else:
            f.move = V2(direction.z, -direction.x)*(.4 if int(self.elapsed*1.5)%2 else -.4)
        if self.difficulty != 'Fácil':
            for z in self.zones:
                if z.owner != f.side and z.delay > 0 and (f.pos-z.pos).length() < z.radius+.5:
                    f.move = (f.pos-z.pos).unit()
                    if z.delay < .4:
                        self.dodge(f.side, f.move)
        if f.ai_timer > 0 or not self.can_act(f):
            return
        f.ai_timer = self.rng.uniform(.4, .8) * {'Fácil': 1.5, 'Normal': 1, 'Difícil': .65}[self.difficulty]
        if f.ultimate >= 100 and distance < 10:
            self.ultimate(f.side)
            return
        if distance < 3 and self.rng.random() < .2:
            f.ai_guard = .65
            self.set_guard(f.side, True)
            return
        priorities = {
            'gojo': [2, 0, 1, 3], 'yuji': [1, 0, 2, 3], 'megumi': [0, 2, 1, 3],
            'nobara': [2, 1, 0, 3], 'yuta': [1, 2, 0, 3], 'maki': [1, 0, 2, 3],
            'nanami': [0, 2, 1, 3], 'todo': [0, 2, 1, 3], 'sukuna': [2, 1, 0, 3],
            'mahito': [0, 1, 2, 3], 'jogo': [1, 0, 2, 3], 'choso': [1, 2, 0, 3],
        }[f.character_id]
        if self.rng.random() < .72:
            for slot in priorities:
                if self.cast(f.side, slot):
                    return
        if distance < f.spec.reach+.4:
            self.attack(f.side, self.rng.random() < .3)
        elif f.energy < 18:
            f.charging = True
