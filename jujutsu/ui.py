"""Portuguese menu, character dossiers, combat HUD and QTE prompts."""
import math
import textwrap

from ursina import Entity, Text, Button, camera

from .models import tint
from .roster import ROSTER, KEYS
from .lifecycle import dispose as destroy


INK = '#101928'
PANEL = '#172435'
MUTED = '#8d9fb5'
WHITE = '#edf3fa'
GOLD = '#e8c794'


def quad(parent, x, y, width, height, tone=PANEL, z=0, alpha=1):
    return Entity(parent=parent, model='quad', position=(x, y, z), scale=(width, height), color=tint(tone, alpha))


def label(parent, text, x, y, size=.8, tone=WHITE, center=False, **kwargs):
    return Text(parent=parent, text=text, position=(x, y, -.035), scale=size, color=tint(tone),
                origin=(0, 0) if center else (-.5, .5), line_height=1.15, **kwargs)


def button(parent, text, x, y, width, height, callback, tone=PANEL, text_tone=WHITE, size=.8):
    node = Button(parent=parent, text=text, position=(x, y, -.02), scale=(width, height),
                  color=tint(tone), text_color=tint(text_tone), text_size=size, model='quad',
                  highlight_color=tint('#33445a'), pressed_color=tint('#465b70'), on_click=callback)
    return node


class Meter:
    def __init__(self, parent, x, y, width, height, tone):
        self.width = width
        self.bg = quad(parent, x+width/2, y, width, height, '#090f1c')
        self.fill = quad(parent, x, y, width, height*.72, tone, z=-.004)
        self.fill.origin_x = -.5
        self.value = None

    def set(self, value):
        value = max(.001, min(1, value))
        if self.value != value:
            self.value = value
            self.fill.scale_x = self.width*value


class Interface:
    def __init__(self, game):
        self.game = game
        self.root = Entity(parent=camera.ui)
        self.menu = self.hud = self.overlay = self.dossier = None
        self.qte_root = None
        self.qte_identity = None
        self.notice_time = 0
        self.banner_time = 0
        self.last_second = None

    def clear(self):
        for name in ('menu', 'hud', 'overlay', 'dossier', 'qte_root'):
            node = getattr(self, name, None)
            if node:
                destroy(node)
                setattr(self, name, None)
        self.qte_identity = None

    def show_menu(self):
        self.clear()
        game = self.game
        self.menu = root = Entity(parent=self.root)
        quad(root, -.485, .0, .785, 1.02, INK, alpha=.97)
        quad(root, -.865, .0, .006, 1.0, GOLD)
        label(root, 'JUJUTSU KAISEN', -.81, .445, .71, GOLD)
        label(root, 'ECLIPSE', -.815, .394, 3.15)
        label(root, 'Escolha sua técnica. Domine o confronto.', -.81, .295, .68, MUTED)
        for side, name in enumerate(('01 / SEU PERSONAGEM', '02 / ADVERSÁRIO')):
            button(root, name, -.636+side*.354, .221, .336, .042,
                   lambda s=side: game.set_selection_side(s),
                   GOLD if side == game.selection_side else '#223146', INK if side == game.selection_side else WHITE, .65)
        self.cards = []
        for i, spec in enumerate(ROSTER):
            x, y = -.699+(i%3)*.234, .133-(i//3)*.087
            selected = i == game.selected[game.selection_side]
            card = button(root, '', x, y, .218, .073, lambda n=i: game.select_character(n),
                          '#33465a' if selected else '#1b293c')
            quad(root, x-.105, y, .004, .073, spec.accent, z=-.026)
            short = spec.name.split()[0].upper()
            if spec.id == 'sukuna':
                short = 'SUKUNA'
            label(root, short, x-.089, y+.018, .80, spec.accent if selected else WHITE)
            label(root, f'{i+1:02d}  /  '+('VILÃO' if spec.id in ('sukuna', 'mahito', 'jogo') else 'FEITICEIRO'),
                  x-.089, y-.014, .43, MUTED)
            if i in game.selected:
                label(root, 'P1' if game.selected[0] == i else 'CPU', x+.066, y+.02, .46, GOLD)
            self.cards.append(card)
        spec = ROSTER[game.selected[game.selection_side]]
        label(root, spec.title, .065, .414, .64, spec.accent)
        label(root, spec.name.upper(), .062, .377, 1.28)
        label(root, spec.role, .065, .328, .73, MUTED)
        label(root, 'MODELO 3D / ARRASTE PARA GIRAR', .30, -.176, .47, MUTED)
        quad(root, .441, -.294, .743, .147, INK, alpha=.91)
        label(root, 'ESTILO DE COMBATE', .086, -.234, .52, spec.accent)
        label(root, textwrap.fill(spec.tips, 59), .086, -.26, .64)
        button(root, 'TÉCNICAS  [TAB]', .263, -.334, .342, .038, game.toggle_dossier, '#28364a', size=.59)
        button(root, 'GIRAR MODELO', .627, -.334, .342, .038, game.rotate_preview, '#28364a', size=.59)
        button(root, 'ARENA / '+('TEMPLO' if game.arena_style == 'temple' else 'SHIBUYA'), -.633, -.245, .355, .043, game.cycle_arena, size=.58)
        button(root, 'IA / '+game.difficulty.upper(), -.272, -.245, .335, .043, game.cycle_difficulty, size=.6)
        button(root, 'MODO / '+('TREINO' if game.training else 'DUELO'), -.633, -.304, .355, .043, game.cycle_mode, size=.6)
        button(root, 'CONTROLES / TAB', -.272, -.304, .335, .043, game.toggle_dossier, size=.58)
        a, b = (ROSTER[n] for n in game.selected)
        label(root, a.name+'  ×  '+b.name, -.81, -.36, .64, MUTED)
        button(root, 'ENTRAR NA ARENA   /   ENTER', -.454, -.422, .711, .066, game.start_match, GOLD, INK, .83)
        label(root, '12 PERSONAGENS  /  48 TÉCNICAS  /  12 SUPREMOS', .087, -.41, .51, GOLD)
        label(root, 'WASD  mover     J K  atacar     L  defender', .087, -.443, .57, MUTED)
        label(root, 'Fan game • modelos e áudio criados para este projeto', -.81, -.481, .44, MUTED)

    def show_hud(self):
        self.clear()
        battle = self.game.battle
        self.hud = root = Entity(parent=self.root)
        self.health = []
        self.guards = []
        self.hp_labels = []
        self.status_labels = []
        for i, fighter in enumerate(battle.fighters):
            x = -.815 if i == 0 else .185
            quad(root, x+.313, .409, .654, .142, INK, alpha=.94)
            label(root, ('VOCÊ / ' if i == 0 else 'CPU / ')+fighter.spec.name.upper(), x+.012, .465, .83, fighter.spec.accent)
            self.health.append(Meter(root, x+.01, .414, .607, .029, fighter.spec.accent))
            self.guards.append(Meter(root, x+.01, .389, .607, .006, '#e3d0a6'))
            self.hp_labels.append(label(root, '', x+.015, .372, .49, MUTED))
            self.status_labels.append(label(root, '', x+.01, .33, .59, fighter.spec.accent))
        quad(root, 0, .422, .18, .13, INK)
        self.timer = label(root, '99', 0, .432, 1.65, GOLD, True)
        self.round_label = label(root, 'TREINO' if battle.training else f'ROUND {self.game.round_number}', 0, .376, .50, MUTED, True)
        self.score = label(root, f'{self.game.scores[0]}  /  {self.game.scores[1]}', 0, .347, .62, GOLD, True)
        self.notice = label(root, '', 0, .247, .84, WHITE, True)
        self.banner = label(root, '', 0, .16, 1.3, GOLD, True)
        quad(root, -.564, -.266, .533, .089, INK, alpha=.93)
        self.resource_text = label(root, '', -.814, -.232, .56, MUTED)
        self.energy = Meter(root, -.814, -.271, .30, .011, '#86cfea')
        self.stamina = Meter(root, -.814, -.297, .30, .006, '#c9d4dd')
        self.ultimate_text = label(root, '', -.474, -.243, .59, GOLD)
        self.ultimate = Meter(root, -.474, -.284, .15, .012, GOLD)
        self.combo = label(root, '', .79, .18, 1.55, GOLD, True)
        self.skills = []
        for i, skill in enumerate(battle.fighters[0].spec.skills):
            x = -.627+i*.418
            quad(root, x, -.383, .399, .110, INK, alpha=.96)
            quad(root, x-.181, -.351, .029, .028, battle.fighters[0].spec.accent)
            label(root, KEYS[i].upper(), x-.181, -.351, .66, INK, True)
            label(root, skill.name, x-.149, -.341, .66)
            sub = label(root, '', x-.177, -.389, .56, MUTED)
            cooldown = Meter(root, x-.185, -.427, .370, .004, battle.fighters[0].spec.accent)
            self.skills.append((sub, cooldown))
        label(root, 'WASD mover   J combo   K forte   L guarda   ESPAÇO esquiva   C salto   G energia   F supremo   TAB guia   ESC pausa',
              0, -.477, .51, MUTED, True)
        self.enemy_ult = label(root, '', .31, -.262, .59, MUTED)
        self.context = label(root, '', .05, -.302, .62, GOLD)
        self.refresh_hud(0)

    def notify(self, text, duration=2.5):
        if self.hud:
            self.notice.text = text
            self.notice_time = duration

    def announce(self, text, duration=1.4):
        if self.hud:
            self.banner.text = text
            self.banner_time = duration

    def refresh_hud(self, dt):
        if not self.hud:
            return
        battle = self.game.battle
        player, enemy = battle.fighters
        for i, fighter in enumerate(battle.fighters):
            self.health[i].set(fighter.hp/fighter.spec.health)
            self.guards[i].set(fighter.guard/100)
            self.hp_labels[i].text = f'{math.ceil(fighter.hp)} / {fighter.spec.health} PV    |    GUARDA {int(fighter.guard)}'
            statuses = []
            for key, name in (('infinity', 'INFINITO'), ('empower', 'REFORÇADO'), ('armor', 'ARMADURA'),
                              ('root', 'PRESO'), ('burn', 'QUEIMADURA'), ('rika', 'RIKA'), ('weakpoint', 'PONTO FRACO')):
                if fighter.has(key):
                    statuses.append(name)
            if fighter.marks.get('nails'):
                statuses.append(f"PREGOS ×{fighter.marks['nails']}")
            if fighter.marks.get('soul'):
                statuses.append(f"ALMA {fighter.marks['soul']}/3")
            self.status_labels[i].text = ' / '.join(statuses[:3])
        self.timer.text = '∞' if battle.training else str(math.ceil(battle.time_left)).zfill(2)
        resource = 'VIGOR FÍSICO' if player.character_id == 'maki' else 'ENERGIA AMALDIÇOADA'
        self.resource_text.text = f'{resource}  {int(player.resource)}'
        self.energy.set(player.resource/100)
        self.stamina.set(player.stamina/100)
        self.ultimate.set(player.ultimate/100)
        self.ultimate_text.text = 'F  PRONTO' if player.ultimate >= 100 else f'F  {int(player.ultimate)}%'
        self.enemy_ult.text = f'SUPREMO INIMIGO  {int(enemy.ultimate)}%' + ('   /   F3 restaurar treino' if battle.training else '')
        self.combo.text = f'{player.chain}\nHITS' if player.chain_timer > 0 and player.chain >= 2 else ''
        for i, (sub, meter) in enumerate(self.skills):
            skill = player.spec.skills[i]
            cd = player.cooldowns[i]
            sub.text = f'RECARGA  {cd:.1f}s' if cd > 0 else f'PRONTA   /   {skill.cost*(.85 if player.character_id == "gojo" else 1):g} recurso'
            sub.color = tint(MUTED if cd > 0 else player.spec.accent)
            meter.set(1-cd/skill.cooldown)
        context = ''
        if player.character_id == 'gojo':
            context = 'ROXO LIBERADO / R' if player.has('blue_ready') and player.has('red_ready') else 'Prepare Roxo: Q + E > R'
        elif player.character_id == 'choso':
            context = f'CONVERGÊNCIA  {player.blood} / 3'
        elif player.character_id == 'sukuna':
            context = 'FORNALHA ABERTA / R' if player.has('cleave_ready') and player.has('dismantle_ready') else 'Abra a Fornalha: Q + E > R'
        elif player.character_id == 'maki':
            context = 'ESPADA / DANO' if player.weapon else 'NAGINATA / ALCANCE'
        elif player.character_id == 'nobara':
            context = f"LIGAÇÃO  {enemy.marks.get('nails', 0)} PREGOS"
        elif player.character_id == 'yuta':
            context = ('CÓPIA / '+enemy.spec.skills[0].name.upper()) if player.has('rika') else 'Invoque Rika com E para copiar'
        self.context.text = context
        self.notice_time -= dt
        self.banner_time -= dt
        if self.notice_time <= 0:
            self.notice.text = ''
        if self.banner_time <= 0:
            self.banner.text = ''
        self.show_qte(battle.qte)

    def show_qte(self, qte):
        if qte is None:
            if self.qte_root:
                destroy(self.qte_root)
                self.qte_root = None
            self.qte_identity = None
            return
        if self.qte_identity is not qte:
            if self.qte_root:
                destroy(self.qte_root)
            self.qte_identity = qte
            self.qte_root = root = Entity(parent=self.root, z=-.3)
            quad(root, 0, -.047, 1.02, .304, INK, alpha=.98)
            quad(root, 0, .108, 1.02, .004, GOLD)
            label(root, 'QUICK TIME EVENT', 0, .073, .55, GOLD, True)
            label(root, qte.title, 0, .025, .93, WHITE, True)
            if qte.mode == 'timing':
                label(root, 'Aperte ESPAÇO na faixa iluminada', 0, -.018, .63, MUTED, True)
                quad(root, 0, -.08, .78, .022, '#26364a')
                quad(root, -.39+qte.target*.78, -.08, .78*qte.width*2, .032, '#427b73', z=-.006)
                quad(root, -.39+qte.target*.78, -.08, .014, .036, '#b4f7d9', z=-.01)
                self.qte_cursor = quad(root, -.39, -.08, .009, .048, '#ffffff', z=-.02)
                self.qte_hint = label(root, '0%', 0, -.143, .73, GOLD, True)
            else:
                label(root, 'Digite a sequência antes que o tempo acabe', 0, -.02, .60, MUTED, True)
                self.key_nodes = []
                for i, key in enumerate(qte.keys):
                    x = (i-(len(qte.keys)-1)/2)*.129
                    node = quad(root, x, -.085, .105, .066, '#30435a', z=-.01)
                    label(root, key.upper(), x, -.085, 1.1, WHITE, True)
                    self.key_nodes.append(node)
                self.qte_meter = Meter(root, -.33, -.152, .66, .008, GOLD)
        if qte.mode == 'timing':
            self.qte_cursor.x = -.39+qte.progress*.78
            self.qte_hint.text = f'{int(qte.progress*100)}%'
        else:
            for i, node in enumerate(self.key_nodes):
                node.color = tint('#397669' if i < qte.index else ('#6b5360' if i == qte.index else '#26354b'))
            self.qte_meter.set(1-qte.progress)

    def show_pause(self):
        if self.overlay:
            destroy(self.overlay)
        self.overlay = root = Entity(parent=self.root, z=-.5)
        quad(root, 0, 0, 2, 1.1, '#080e1a', alpha=.84)
        quad(root, 0, 0, .61, .52, PANEL)
        label(root, 'PAUSA', 0, .175, 1.6, GOLD, True)
        button(root, 'CONTINUAR  /  ESC', 0, .061, .48, .057, self.game.toggle_pause, GOLD, INK)
        button(root, 'TÉCNICAS  /  TAB', 0, -.022, .48, .057, self.game.toggle_dossier)
        button(root, 'SELEÇÃO DE PERSONAGENS', 0, -.105, .48, .057, self.game.show_menu, size=.65)
        button(root, 'SAIR DO JOGO', 0, -.188, .48, .046, self.game.quit, size=.65)

    def close_overlay(self):
        if self.overlay:
            destroy(self.overlay)
            self.overlay = None

    def show_result(self, match_done):
        self.close_overlay()
        self.overlay = root = Entity(parent=self.root, z=-.5)
        quad(root, 0, 0, 1.15, .48, INK, alpha=.97)
        winner = self.game.battle.winner
        heading = 'EMPATE' if winner is None else ('VITÓRIA' if winner == 0 else 'DERROTA')
        label(root, 'CONFRONTO ENCERRADO' if match_done else 'FIM DO ROUND', 0, .178, .59, MUTED, True)
        label(root, heading, 0, .098, 2.6, GOLD, True)
        f = self.game.battle.fighters[0]
        label(root, f'DANO  {int(f.damage_dealt)}     ACERTOS  {f.hits}     MELHOR COMBO  {f.best_combo}', 0, .013, .70, WHITE, True)
        label(root, f'PLACAR   {self.game.scores[0]} : {self.game.scores[1]}', 0, -.043, .85, GOLD, True)
        button(root, 'REVANCHE / ENTER' if match_done else 'PRÓXIMO ROUND / ENTER', -.235, -.126, .43, .06,
               self.game.continue_match, GOLD, INK, .64)
        button(root, 'ESC / SELEÇÃO', .235, -.126, .43, .06, self.game.show_menu, size=.66)

    def show_dossier(self, spec):
        if self.dossier:
            destroy(self.dossier)
            self.dossier = None
            return
        self.dossier = root = Entity(parent=self.root, z=-.9)
        quad(root, 0, 0, 2, 1.05, '#080e18', alpha=.9)
        quad(root, 0, 0, 1.62, .87, INK)
        quad(root, -.802, 0, .005, .87, spec.accent)
        label(root, 'DOSSIÊ DO FEITICEIRO', -.752, .397, .55, spec.accent)
        label(root, spec.name.upper(), -.755, .344, 1.5)
        label(root, spec.role+'  /  '+str(spec.health)+' PV', -.75, .282, .66, MUTED)
        button(root, 'FECHAR / TAB', .628, .382, .27, .043, self.game.toggle_dossier, size=.61)
        quad(root, .304, -.04, .002, .63, '#334056')
        for i, skill in enumerate(spec.skills):
            y = .198-i*.103
            quad(root, -.727, y-.008, .036, .036, spec.accent, z=-.015)
            label(root, KEYS[i].upper(), -.727, y-.008, .75, INK, True)
            label(root, skill.name, -.687, y+.012, .79)
            label(root, f'{skill.cost:g} recurso  /  {skill.cooldown:g}s', .11, y+.008, .44, MUTED)
            label(root, textwrap.fill(skill.instruction, 74), -.687, y-.02, .56, MUTED)
        label(root, 'F / '+spec.ultimate, -.748, -.237, .79, GOLD)
        label(root, '100% de supremo > sequência de teclas. Acertos ampliam o efeito.', -.748, -.269, .54, MUTED)
        label(root, textwrap.fill(spec.passive, 85), -.748, -.321, .57, spec.accent)
        label(root, 'CONTROLES', .352, .223, .71, GOLD)
        controls = [('W A S D', 'Mover na arena'), ('J / K', 'Combo / golpe forte'), ('L', 'Segurar: guarda'), ('ESPAÇO', 'Esquiva direcional'), ('C', 'Pular ataques de chão'), ('G', 'Segurar: recuperar recurso'), ('Q E R T', 'Técnicas do personagem'), ('F', 'Supremo / QTE'), ('M / ESC', 'Som / pausa'), ('F3', 'Restaurar no treino')]
        for i, (key, description) in enumerate(controls):
            y = .17-i*.038
            label(root, key, .353, y, .55, spec.accent)
            label(root, description, .498, y, .50, MUTED)
        label(root, 'DEFESA PERFEITA', .352, -.245, .58, GOLD)
        label(root, 'Aperte L pouco antes do impacto.\nGolpes fortes quebram a guarda.\nSaia dos círculos antes da explosão.', .352, -.277, .53, MUTED)
        label(root, 'Combos sugeridos: J > J > K  /  esquiva > Q  /  técnica > supremo', -.75, -.395, .58, GOLD)
