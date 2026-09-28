"""Articulated, sculpted character models and original procedural scenery.

All meshes are constructed locally. No downloaded/ripped character assets.
"""
import math
import random
from copy import deepcopy

from ursina import Entity, Mesh, Shader, Vec3, color, lerp
from ursina.models.procedural.cone import Cone

from .roster import BY_ID


TOON = Shader(name='eclipse_cel', language=Shader.GLSL, vertex='''
#version 140
uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat4 p3d_ModelMatrix;
in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec4 p3d_Color;
out vec3 normal;
out vec3 world_pos;
out vec4 vertex_color;
void main() {
    gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
    normal = normalize(mat3(p3d_ModelMatrix) * p3d_Normal);
    world_pos = (p3d_ModelMatrix * p3d_Vertex).xyz;
    vertex_color = p3d_Color;
}
''', fragment='''
#version 140
uniform vec4 p3d_ColorScale;
in vec3 normal;
in vec3 world_pos;
in vec4 vertex_color;
out vec4 fragColor;
void main() {
    vec3 n = normalize(normal);
    float light = dot(n, normalize(vec3(-0.45, 0.85, -0.5)));
    float tone = 0.58 + step(-0.1,light)*0.18 + step(0.5,light)*0.24;
    float edge = pow(1.0-abs(n.z), 3.0)*0.08;
    vec3 col = p3d_ColorScale.rgb*vertex_color.rgb*tone + vec3(0.24,0.48,0.64)*edge;
    fragColor = vec4(col, p3d_ColorScale.a*vertex_color.a);
}
''')


def tint(value, alpha=1):
    c = color.hex(value) if isinstance(value, str) else color.Color(*value)
    c[3] = alpha
    return c


def part(parent, model='sphere', pos=(0, 0, 0), scale=1, tone='#ffffff', rotation=(0, 0, 0), lit=True, **kwargs):
    if isinstance(model, Mesh) and not model.normals:
        model.generate_normals()
    if isinstance(model, Mesh):
        # A Mesh is a NodePath: reusing it directly moves geometry between parts.
        model = deepcopy(model)
    return Entity(parent=parent, model=model, position=pos, scale=scale, color=tint(tone),
                  rotation=rotation, shader=TOON if lit else None, **kwargs)


_lofts = {}


def loft(rings, sides=12):
    """A smooth elliptical silhouette with a closed top and bottom."""
    key = (tuple(rings), sides)
    if key in _lofts:
        return _lofts[key]
    vertices, triangles = [], []
    for y, rx, rz in rings:
        for i in range(sides):
            angle = i*math.tau/sides
            vertices.append((math.cos(angle)*rx, y, math.sin(angle)*rz))
    for row in range(len(rings)-1):
        for i in range(sides):
            a, b = row*sides+i, row*sides+(i+1)%sides
            triangles.extend(((a, a+sides, b), (b, a+sides, b+sides)))
    bottom = len(vertices)
    vertices.append((0, rings[0][0], 0))
    top = len(vertices)
    vertices.append((0, rings[-1][0], 0))
    for i in range(sides):
        ni = (i+1)%sides
        triangles.append((bottom, i, ni))
        triangles.append((top, (len(rings)-1)*sides+ni, (len(rings)-1)*sides+i))
    triangles = [(a, c, b) for a, b, c in triangles]
    mesh = Mesh(vertices=vertices, triangles=triangles, static=True)
    mesh.generate_normals(smooth=True)
    _lofts[key] = mesh
    return mesh


_ring_cache = {}


def ring_mesh(segments=64, thickness=.018):
    key = (segments, thickness)
    if key in _ring_cache:
        return _ring_cache[key]
    vertices, triangles = [], []
    for i in range(segments):
        a = i*math.tau/segments
        for radius in (1-thickness, 1):
            vertices.append((math.cos(a)*radius, 0, math.sin(a)*radius))
    for i in range(segments):
        a, b = 2*i, 2*((i+1)%segments)
        triangles.extend(((a, b, a+1), (b, b+1, a+1)))
    if thickness >= .999:
        vertices = [(0, 0, 0)] + [(math.cos(i*math.tau/segments), 0, math.sin(i*math.tau/segments)) for i in range(segments)]
        triangles = [(0, i+1, (i+1)%segments+1) for i in range(segments)]
    else:
        triangles = [(a, c, b) for a, b, c in triangles]
    mesh = Mesh(vertices=vertices, triangles=triangles, normals=[(0, 1, 0)]*len(vertices), static=True)
    _ring_cache[key] = mesh
    return mesh


def stroke(parent, start, end, width=.02, tone='#192233'):
    start, end = Vec3(*start), Vec3(*end)
    node = part(parent, 'cube', (start+end)/2, (width, width, (end-start).length()), tone)
    # Endpoints are local coordinates; heading is set locally as well.
    delta = end-start
    node.rotation_y = math.degrees(math.atan2(delta.x, delta.z))
    node.rotation_x = -math.degrees(math.atan2(delta.y, math.hypot(delta.x, delta.z)))
    return node


class CharacterModel(Entity):
    def __init__(self, character_id, parent=None, **kwargs):
        super().__init__(parent=parent, **kwargs) if parent is not None else super().__init__(**kwargs)
        self.spec = BY_ID[character_id]
        self.character_id = character_id
        self.phase = 0
        self.last_weapon = -1
        self.base_scale = 1
        cid, spec = character_id, self.spec
        broad = 1.4 if cid == 'mahoraga' else (1.22 if cid in ('todo', 'ryu') else (1.1 if cid in ('nanami', 'sukuna') else .95))
        skin = '#e6baa2' if cid not in ('jogo', 'mahito') else ('#cab999' if cid == 'jogo' else '#d4d0cb')
        if cid == 'mahoraga':
            skin = '#e5e5d7'
        bare = cid in ('todo', 'mahoraga', 'uro')
        clothes = spec.outfit
        self.body = Entity(parent=self, y=1.55)
        part(self.body, loft(((0, .30, .21), (.20, .34, .23), (.78, .46, .24), (1.03, .35, .21))),
             scale=(broad, 1, 1), tone=skin if cid in ('todo', 'mahoraga') else clothes)
        part(self.body, pos=(0, .02, 0), scale=(.65*broad, .33, .46), tone=clothes)
        part(self.body, 'cube', (0, .14, 0), (.66*broad, .09, .45), '#141c2b')
        part(self.body, 'cube', (.04, .14, .235), (.12, .08, .02), '#cbb47c')
        part(self.body, pos=(0, 1.08, 0), scale=(.26, .28, .27), tone=skin)
        self.head = Entity(parent=self.body, position=(0, 1.33, .025))
        head_mesh = loft(((-.33, .10, .13), (-.25, .21, .205), (-.08, .285, .255),
                          (.15, .285, .255), (.29, .22, .20), (.34, .08, .08)), 16)
        part(self.head, head_mesh, tone=skin)
        for side in (-1, 1):
            part(self.head, pos=(side*.28, -.02, 0), scale=(.105, .18, .095), tone=skin)
        self._face(cid, skin)
        self._hair(cid)

        self.arms, self.forearms, self.hands = [], [], []
        for side in (-1, 1):
            shoulder = Entity(parent=self.body, position=(side*.46*broad, .86, 0), rotation_z=side*9)
            part(shoulder, pos=(0, -.08, 0), scale=(.35, .34, .34), tone=skin if bare else clothes)
            part(shoulder, loft(((-.56, .12, .12), (-.3, .145, .145), (0, .17, .17))),
                 tone=skin if bare else clothes)
            elbow = Entity(parent=shoulder, y=-.56)
            part(elbow, loft(((-.49, .09, .10), (-.18, .12, .13), (0, .125, .13))),
                 tone=skin if bare or cid == 'sukuna' else clothes)
            part(elbow, 'cube', (0, -.44, 0), (.205, .085, .22), '#b12743' if cid == 'yuji' else '#1b2333')
            hand = Entity(parent=elbow, y=-.57)
            part(hand, pos=(0, 0, .02), scale=(.19, .24, .21), tone=skin)
            part(hand, pos=(-side*.08, .01, .07), scale=(.07, .15, .09), tone=skin)
            self.arms.append(shoulder)
            self.forearms.append(elbow)
            self.hands.append(hand)

        self.legs, self.knees = [], []
        pants = '#202538' if cid not in ('nanami', 'sukuna', 'todo', 'choso', 'mahoraga', 'uro') else clothes
        for side in (-1, 1):
            hip = Entity(parent=self, position=(side*.20*broad, 1.55, 0))
            part(hip, loft(((-.72, .13, .14), (-.2, .17, .18), (.08, .18, .20))), tone=pants)
            knee = Entity(parent=hip, y=-.73)
            part(knee, loft(((-.59, .115, .13), (-.17, .13, .145), (.05, .14, .15))), tone=pants)
            part(knee, pos=(0, -.64, .10), scale=(.28, .23, .49), tone='#b73c50' if cid == 'yuji' else '#171c2b')
            part(knee, 'cube', (0, -.727, .12), (.26, .055, .43), '#e2d3c3' if cid == 'yuji' else '#383b46')
            self.legs.append(hip)
            self.knees.append(knee)
        self.weapon_root = Entity(parent=self.hands[1])
        self._costume(cid, clothes, skin)
        self._weapon(cid)
        self.energy_orbs = [part(self, pos=(0, 1.4, 0), scale=.12, tone=spec.accent, lit=False, enabled=False) for _ in range(3)]
        self.barrier = part(self, 'sphere', (0, 1.65, 0), (2.0, 3.5, 2), '#69ddff', lit=False, enabled=False)
        self.barrier.color = tint('#69ddff', .12)
        self.barrier.wireframe = True
        self.aura = part(self, ring_mesh(48, .035), (0, .025, 0), 1.1, spec.accent, lit=False, enabled=False)
        if cid == 'jogo':
            self.scale = .88
        elif cid == 'todo':
            self.scale = 1.09
        elif cid == 'mahoraga':
            self.scale = 1.43
        elif cid == 'ryu':
            self.scale = 1.08
        self.base_scale = self.scale_x

    def _face(self, cid, skin):
        if cid == 'mahoraga':
            part(self.head, pos=(0, -.12, .19), scale=(.44, .29, .21), tone='#eeeedd')
            part(self.head, 'cube', (0, -.16, .301), (.30, .06, .025), '#4f514a')
            for i in range(7):
                part(self.head, 'cube', ((i-3)*.04, -.147, .32), (.023, .05, .02), '#ffffff')
            for side in (-1, 1):
                for row in range(2):
                    wing = Entity(parent=self.head, position=(side*.23, .04+row*.17, .02), rotation_z=side*(18+row*16))
                    for j in range(4):
                        part(wing, Cone(5), (side*(.13+j*.075), .025*j, -.02*j),
                             (.10, .38-j*.04, .07), skin, rotation=(0, 0, -side*67))
            return
        if cid == 'jogo':
            part(self.head, pos=(0, .015, .253), scale=(.30, .19, .08), tone='#f8efc7')
            part(self.head, pos=(0, .015, .300), scale=(.085, .13, .03), tone='#262227')
            for side in (-1, 1):
                part(self.head, 'cube', (side*.33, -.03, 0), (.16, .22, .22), '#928b79')
        else:
            for side in (-1, 1):
                part(self.head, pos=(side*.121, .015, .23), scale=(.175, .079, .060), tone='#eee9e4')
                eye_color = '#60cef5' if cid == 'gojo' else ('#ab8162' if cid == 'yuji' else '#778f88')
                part(self.head, pos=(side*.119, .009, .262), scale=(.050, .063, .018), tone=eye_color, lit=False)
                part(self.head, pos=(side*.116, .01, .272), scale=(.024, .05, .008), tone='#1e2130', lit=False)
                part(self.head, pos=(side*.112, .025, .277), scale=.013, tone='#ffffff', lit=False)
                part(self.head, 'cube', (side*.12, .074, .236), (.17, .027, .025), self.spec.hair,
                     rotation=(0, side*10, side*-8))
        part(self.head, pos=(0, -.063, .253), scale=(.075, .115, .082), tone=skin)
        part(self.head, 'cube', (0, -.184, .210), (.108, .016, .012), '#966a6b')
        if cid == 'gojo':
            part(self.head, loft(((-.062, .31, .300), (.105, .30, .296))), tone='#131b2d')
        if cid in ('maki', 'nanami'):
            glass_color = '#962b38' if cid == 'maki' else '#dfc987'
            for side in (-1, 1):
                part(self.head, 'cube', (side*.137, .018, .277), (.225, .117, .037), glass_color)
                part(self.head, 'cube', (side*.137, .018, .298), (.175, .074, .016), '#183642')
            part(self.head, 'cube', (0, .039, .283), (.078, .019, .025), glass_color)
        if cid == 'sukuna':
            for side in (-1, 1):
                for i in range(2):
                    part(self.head, 'cube', (side*(.20-i*.016), -.078-i*.062, .235), (.13, .022, .025), '#3a2430', rotation=(0, 0, side*27))
                part(self.head, 'cube', (side*.10, .215, .195), (.025, .13, .025), '#3a2430', rotation=(0, 0, side*-18))
            part(self.head, 'cube', (0, -.27, .137), (.055, .07, .022), '#3a2430')
        if cid in ('mahito', 'todo'):
            for i in range(7):
                y = -.24+i*.073
                x = .18-y*.28
                part(self.head, 'cube', (x, y, .217), (.065, .014, .018), '#747078', rotation=(0, 0, -15))
            part(self.head, 'cube', (.18, -.035, .220), (.013, .41, .02), '#7b7277', rotation=(0, 0, 12))
        if cid == 'choso':
            part(self.head, 'cube', (0, -.045, .294), (.42, .056, .012), '#634351')
            part(self.head, 'cube', (0, -.074, .296), (.085, .07, .014), '#634351')

    def _hair(self, cid):
        hair = self.spec.hair
        if cid == 'mahoraga':
            part(self.head, loft(((.14, .27, .23), (.34, .20, .17), (.47, .07, .09))), tone=hair)
            for side in (-1, 1):
                part(self.head, Cone(6), (side*.2, .3, -.16), (.19, .64, .16), hair,
                     rotation=(-65, 0, side*24))
            return
        if cid == 'ryu':
            part(self.head, pos=(0, .29, -.02), scale=(.60, .29, .55), tone=hair)
            part(self.head, pos=(0, .44, .20), scale=(.49, .37, .78), tone=hair, rotation=(-17, 0, 0))
            for i in range(6):
                stroke(self.head, ((i-2.5)*.07, .44, .56), ((i-2.5)*.07, .59, .09), .018, '#654e77')
            return
        part(self.head, pos=(0, .23, -.025), scale=(.59, .31, .55), tone=hair)
        if cid in ('gojo', 'yuji', 'megumi', 'sukuna'):
            rng = random.Random(13)
            for i in range(19):
                a = math.tau*i/19
                tall = .4 if cid in ('gojo', 'megumi') else .24
                part(self.head, Cone(5), (math.cos(a)*.21, .29+rng.uniform(0, .13), math.sin(a)*.20),
                     (.18, tall+rng.uniform(0, .16), .18), hair,
                     rotation=(math.sin(a)*36, i*38, -math.cos(a)*38))
            for i in range(5):
                part(self.head, Cone(4), ((i-2)*.1, .19, .22), (.14, .28, .10), hair, rotation=(15, 0, 160+(i-2)*12))
        elif cid == 'jogo':
            part(self.head, loft(((.20, .28, .25), (.41, .26, .23), (.56, .20, .20))), tone='#584853')
            part(self.head, ring_mesh(24, .3), (0, .561, 0), .22, '#a37457')
            part(self.head, 'sphere', (0, .53, 0), (.25, .07, .25), '#ff914c', lit=False)
        else:
            for i in range(9):
                x = (i-4)*.062
                part(self.head, pos=(x, .2+(i%3)*.016, .178), scale=(.12, .33, .17), tone=hair,
                     rotation=(12, 0, 20 if cid == 'nanami' else -10))
            if cid in ('nobara', 'mahito', 'uro'):
                for side in (-1, 1):
                    part(self.head, pos=(side*.25, -.08, -.075), scale=(.20, .66 if cid == 'nobara' else .94, .39), tone=hair)
                if cid == 'mahito':
                    for i in range(5):
                        part(self.head, pos=((i-2)*.10, -.32, -.2), scale=(.12, .88, .15), tone=hair, rotation=(16, 0, (i-2)*7))
                if cid == 'uro':
                    for side in (-1, 1):
                        part(self.head, pos=(side*.32, -.22, -.12), scale=(.18, 1.10, .23), tone=hair, rotation=(10, 0, side*14))
                        part(self.head, ring_mesh(24, .20), (side*.31, -.10, .12), .10, '#e9d486', rotation=(90, 0, 0))
            if cid == 'maki':
                part(self.head, pos=(0, .32, -.34), scale=(.33, .35, .36), tone=hair)
                part(self.head, pos=(0, -.05, -.46), scale=(.27, .71, .28), tone=hair, rotation=(-20, 0, 0))
                part(self.head, pos=(0, .25, -.33), scale=(.35, .09, .30), tone='#9d5364')
            if cid == 'todo':
                part(self.head, pos=(0, .46, -.05), scale=(.28, .26, .28), tone=hair)
            if cid == 'choso':
                for side in (-1, 1):
                    part(self.head, pos=(side*.32, .32, -.11), scale=(.27, .31, .31), tone=hair)

    def _costume(self, cid, clothes, skin):
        self.wheel = self.sky_veil = None
        if cid == 'mahoraga':
            for side in (-1, 1):
                part(self.body, pos=(side*.29, .72, .16), scale=(.57, .39, .28), tone=skin)
                for i in range(3):
                    part(self.body, pos=(side*.15, .27+i*.14, .23), scale=(.28, .18, .12), tone=skin)
                part(self.arms[(side+1)//2], pos=(0, -.26, 0), scale=(.40, .50, .40), tone=skin)
            part(self.body, loft(((-.64, .62, .35), (-.16, .48, .28), (.18, .41, .26))), tone='#ded9c0')
            for i in range(9):
                x = (i-4)*.11
                stroke(self.body, (x*.7, .04, .275), (x, -.60, .30), .018, '#a19f89')
            part(self.body, 'cube', (0, .17, 0), (.95, .18, .57), '#484b43')
            self.wheel = Entity(parent=self, y=3.94)
            part(self.wheel, ring_mesh(64, .09), scale=.68, tone='#d8b967', rotation=(90, 0, 0), lit=False, double_sided=True)
            part(self.wheel, pos=(0, 0, 0), scale=.20, tone='#fff2b1', lit=False)
            for i in range(8):
                a = i*math.tau/8
                end = (math.cos(a)*.82, math.sin(a)*.82, 0)
                stroke(self.wheel, (0, 0, 0), end, .055, '#bfa25f')
                part(self.wheel, pos=end, scale=.18, tone='#fff1b7', lit=False)
            # The tail curls behind the torso, leaving the face and sword readable.
            for i in range(9):
                part(self.body, pos=(math.sin(i*.48)*.22, .15+i*.09, -.30-i*.065),
                     scale=(.16-i*.009, .18, .22), tone=skin)
        if cid == 'ryu':
            part(self.body, 'cube', (0, .64, .247), (.50, .72, .04), skin)
            for side in (-1, 1):
                for i in range(7):
                    part(self.body, pos=(side*(.22+i*.025), .95-i*.11, .29), scale=(.20, .20, .16), tone='#b9a2bc')
                part(self.body, 'cube', (side*.28, .37, .26), (.19, .69, .06), clothes, rotation=(0, 0, side*-12))
            stroke(self.body, (-.14, .84, .29), (0, .58, .31), .025, '#dbc47d')
            stroke(self.body, (.14, .84, .29), (0, .58, .31), .025, '#dbc47d')
        if cid == 'uro':
            self.sky_veil = Entity(parent=self.body)
            part(self.body, loft(((-.42, .47, .28), (.25, .31, .23))), tone=clothes)
            for i in range(4):
                veil = part(self.sky_veil, ring_mesh(48, .40), (0, .18+i*.22, 0),
                            (.60+i*.04, .6, .39), '#aedff2', rotation=(12+i*8, i*55, 14),
                            lit=False, double_sided=True)
                veil.alpha = .36
            stroke(self.body, (-.33, .90, .23), (.25, .21, .25), .07, '#d4f5fc')
        if cid in ('gojo', 'megumi', 'yuji', 'maki'):
            collar = '#ba3f52' if cid == 'yuji' else clothes
            part(self.body, loft(((.90, .26, .245), (1.20, .245, .22))), tone=collar)
            for y in (.85, .66, .47):
                part(self.body, pos=(.10, y, .237), scale=.045, tone='#d3b780')
        if cid == 'yuji':
            part(self.body, pos=(0, 1, -.19), scale=(.64, .34, .27), tone='#a93449')
            for side in (-1, 1):
                part(self.body, 'cube', (side*.10, .83, .25), (.022, .21, .025), '#e6ad9b')
        if cid == 'nobara':
            part(self.body, loft(((-.37, .48, .28), (.14, .30, .215))), tone=clothes)
            part(self.body, 'cube', (.34, .1, .1), (.20, .29, .24), '#a8774e')
            for side in (-1, 1):
                part(self.body, 'cube', (side*.17, .84, .22), (.20, .29, .04), '#374860', rotation=(0, 0, side*25))
        if cid == 'yuta':
            stroke(self.body, (-.19, 1.0, .23), (.17, .20, .24), .026, '#66667b')
            part(self.body, 'cube', (-.1, .7, -.24), (.11, 1.65, .09), '#673e45', rotation=(0, 0, -20))
            part(self.hands[0], pos=(0, .01, .112), scale=(.19, .035, .025), tone='#d4bc7e', lit=False)
        if cid == 'nanami':
            part(self.body, 'cube', (0, .78, .24), (.31, .44, .02), '#8fb9c8')
            for side in (-1, 1):
                part(self.body, 'cube', (side*.18, .70, .255), (.17, .58, .04), '#d4bc92', rotation=(0, 0, side*23))
            part(self.body, 'cube', (0, .68, .28), (.10, .52, .035), '#796138', rotation=(0, 0, -7))
            for i in range(4):
                part(self.body, pos=((i%2)*.024-.01, .52+i*.095, .301), scale=.04, tone='#333142')
        if cid == 'todo':
            for side in (-1, 1):
                part(self.body, pos=(side*.23, .73, .16), scale=(.46, .34, .20), tone=skin)
                for i in range(3):
                    part(self.body, pos=(side*.12, .24+i*.14, .22), scale=(.22, .15, .065), tone=skin)
            part(self.body, 'cube', (0, .13, 0), (.77, .14, .48), '#9b4462')
        if cid == 'sukuna':
            for side in (-1, 1):
                part(self.body, 'cube', (side*.14, .65, .26), (.16, .81, .03), '#414256', rotation=(0, 0, side*21))
                for j in (0, 1):
                    part(self.forearms[(side+1)//2], loft(((-.20-j*.12, .126, .14), (-.17-j*.12, .126, .14))), tone='#443244')
            part(self.body, loft(((-.55, .53, .32), (.12, .32, .23))), tone=clothes)
            part(self.body, 'cube', (0, .17, 0), (.72, .22, .49), '#423c52')
        if cid == 'mahito':
            for side in (-1, 1):
                part(self.body, 'cube', (side*.24, .57, .24), (.30, .34, .025), '#555c6d')
                for i in range(6):
                    part(self.body, 'cube', (side*.23, .41+i*.06, .26), (.035, .017, .012), '#c3c5c3')
        if cid == 'jogo':
            part(self.body, loft(((.08, .60, .33), (.68, .55, .30), (1.1, .3, .24))), tone='#bdac66')
            for i in range(13):
                angle = i*2.4
                part(self.body, pos=(math.sin(angle)*.42, .18+(i%4)*.2, .31), scale=(.12, .095, .04), tone='#373945')
        if cid == 'choso':
            part(self.body, loft(((-.55, .47, .32), (.26, .33, .24))), tone=clothes)
            part(self.body, loft(((.27, .37, .255), (.69, .42, .27))), tone='#63516e')
            part(self.body, 'cube', (.33, .05, .15), (.23, .8, .12), '#685675', rotation=(0, 0, 12))

    def _weapon(self, cid):
        self.sword = self.spear = None
        root = self.weapon_root
        if cid == 'mahoraga':
            self.sword = Entity(parent=self.forearms[1], position=(.14, -.25, .16), rotation_x=175)
            part(self.sword, loft(((0, .13, .045), (1.12, .11, .035), (1.68, .005, .005)), 4), tone='#f0f1d7')
            part(self.sword, 'cube', (0, .65, .045), (.035, 1.32, .015), '#ffffdd', lit=False)
            part(self.sword, 'cube', (0, .06, 0), (.36, .13, .18), '#ada17a')
        if cid in ('yuta', 'maki', 'nanami', 'nobara'):
            part(root, 'cube', (0, -.12, .02), (.085, .43, .085), '#4b3440')
        if cid in ('yuta', 'maki'):
            self.sword = Entity(parent=root)
            part(self.sword, 'cube', (0, .1, 0), (.28, .045, .15), '#ceb77e')
            part(self.sword, loft(((.12, .045, .027), (1.20, .035, .022), (1.35, .002, .001)), 4), tone='#dfeeee')
            part(self.sword, 'cube', (.025, .66, .024), (.014, 1.08, .012), '#f6ffff', lit=False)
        if cid == 'maki':
            self.spear = Entity(parent=root)
            part(self.spear, 'cube', (0, .22, 0), (.085, 2.65, .085), '#752f48')
            part(self.spear, loft(((1.48, .06, .024), (1.78, .17, .025), (2.03, .01, .01)), 4), tone='#d6e6e4')
            for y in (-1.04, 1.36):
                part(self.spear, 'cube', (0, y, 0), (.13, .15, .12), '#d3b271')
            self.sword.enabled = False
        if cid == 'nanami':
            part(root, 'cube', (0, .44, .01), (.25, .83, .09), '#ddd9c5', rotation=(0, 0, -5))
            for i in range(7):
                part(root, 'cube', (0, .16+i*.10, .061), (.28, .022, .008), '#656b76', rotation=(0, 0, -18))
        if cid == 'nobara':
            part(root, 'cube', (0, .24, 0), (.39, .18, .19), '#a7b4bd')
            part(self.hands[0], 'cube', (0, 0, .12), (.022, .35, .022), '#dfebf5')
            part(self.hands[0], 'cube', (0, .17, .12), (.075, .035, .04), '#dae9f5')

    def pose(self, dt, state=None, preview=False):
        self.phase += dt
        phase = self.phase
        action = 'idle' if preview or state is None else state.action
        age = phase if state is None else state.action_time
        breathing = math.sin(phase*2.2)*.016
        self.body.y = 1.55+breathing
        self.body.rotation = (0, 0, 0)
        self.head.rotation_y = math.sin(phase*.6)*3
        for i, (arm, elbow, leg, knee) in enumerate(zip(self.arms, self.forearms, self.legs, self.knees)):
            side = -1 if i == 0 else 1
            arm.rotation = (-14, 0, side*9)
            elbow.rotation = (-18, 0, 0)
            leg.rotation_x = 0
            knee.rotation_x = 0
        if action == 'run':
            swing = math.sin(phase*12)*31
            for i in range(2):
                sign = -1 if i else 1
                self.arms[i].rotation_x = swing*sign
                self.legs[i].rotation_x = -swing*sign
                self.knees[i].rotation_x = max(0, swing*sign)*.7
            self.body.rotation_x = 7
            self.body.y += abs(math.sin(phase*12))*.045
        elif action.startswith('punch') or action in ('heavy', 'cast', 'ultimate'):
            impact = max(0, math.sin(min(1, age/.35)*math.pi))
            which = 0 if action == 'punch2' else 1
            self.arms[which].rotation_x = -30-impact*75
            self.forearms[which].rotation_x = -30+impact*35
            self.body.rotation_y = impact*(-20 if which else 20)
            if action in ('cast', 'ultimate'):
                self.arms[0].rotation_x = -65
                self.arms[1].rotation_x = -65
                self.forearms[0].rotation_z = -25
                self.forearms[1].rotation_z = 25
            if action == 'heavy':
                self.legs[0].rotation_x = -impact*65
        elif action == 'guard':
            for i in range(2):
                self.arms[i].rotation_x = -65
                self.forearms[i].rotation_x = -85
        elif action == 'dodge':
            self.body.rotation_x = 22
            self.body.y -= .25
            self.legs[0].rotation_x = -48
            self.legs[1].rotation_x = 40
        elif action == 'hit':
            self.body.rotation_x = -min(1, age*6)*16
            self.arms[0].rotation_x = 20
        elif action == 'charge':
            self.arms[0].rotation_z = -35
            self.arms[1].rotation_z = 35
            self.forearms[0].rotation_x = self.forearms[1].rotation_x = -70
        self.barrier.enabled = bool(state and state.has('infinity'))
        self.aura.enabled = bool(state and (state.charging or state.has('empower') or state.ultimate >= 100))
        if self.aura.enabled:
            self.aura.scale = 1+math.sin(phase*4)*.08
        for i, orb in enumerate(self.energy_orbs):
            orb.enabled = bool(state and state.blood > i)
            a = phase*2+i*math.tau/3
            orb.position = (math.cos(a)*.85, 1.7+math.sin(a*2)*.2, math.sin(a)*.85)
        if state and self.character_id == 'maki' and self.last_weapon != state.weapon:
            self.last_weapon = state.weapon
            self.sword.enabled = bool(state.weapon)
            self.spear.enabled = not state.weapon
        if state and self.character_id == 'mahito':
            self.body.scale = (1.2, 1.07, 1.1) if state.has('morph') else (1, 1, 1)
        if self.wheel:
            turns = sum(getattr(state, 'adaptation', {}).values()) if state else 0
            self.wheel.rotation_z = lerp(self.wheel.rotation_z, turns*45 + math.sin(phase)*2, min(1, dt*5))
            self.wheel.y = 3.94+math.sin(phase*2)*.025
        if self.sky_veil:
            self.sky_veil.rotation_y = phase*15
            self.sky_veil.scale = 1.35 if state and state.has('sky_guard') else 1
        if state and state.has('flight'):
            self.legs[0].rotation_x = -24
            self.knees[0].rotation_x = 55
            self.arms[0].rotation_z = -48
            self.arms[1].rotation_z = 48
        if state and state.hp <= 0:
            self.body.rotation_z = lerp(self.body.rotation_z, 75, min(1, dt*5))
            self.body.y = .4


def make_summon(parent, kind, accent):
    root = Entity(parent=parent)
    if kind == 'dog':
        part(root, pos=(0, .6, 0), scale=(.48, .57, 1.14), tone='#242739')
        part(root, pos=(0, .93, .58), scale=(.43, .46, .50), tone='#323a4f')
        part(root, pos=(0, .84, .80), scale=(.27, .21, .36), tone='#abb3c2')
        for side in (-1, 1):
            part(root, Cone(4), (side*.16, 1.24, .53), (.19, .31, .18), '#31374b')
            part(root, pos=(side*.155, .99, .76), scale=.072, tone=accent, lit=False)
            for z in (-.38, .38):
                part(root, pos=(side*.2, .26, z), scale=(.16, .52, .16), tone='#252c41')
        part(root, Cone(6), (0, .78, -.7), (.22, .65, .22), '#38445b', rotation=(55, 0, 0))
    elif kind == 'brother':
        CharacterModel('yuji', parent=root)
    else:
        part(root, pos=(0, 1.75, 0), scale=(1.6, 1.7, 1.1), tone='#c8c9d0')
        part(root, pos=(0, 2.76, .15), scale=(1.15, .95, .96), tone='#e4e0d9')
        part(root, 'cube', (0, 2.62, .65), (.77, .24, .10), '#2d243d')
        for i in range(7):
            part(root, Cone(4), ((i-3)*.10, 2.65, .71), (.085, .20, .075), '#f0eadb', rotation=(0, 0, 180))
        part(root, pos=(0, 2.94, .59), scale=(.35, .19, .09), tone='#e19ddb', lit=False)
        for side in (-1, 1):
            part(root, pos=(side*.95, 1.7, .4), scale=(.5, 1.75, .5), tone='#c7c8d2', rotation=(20, 0, side*20))
            part(root, Cone(5), (side*.39, 3.38, .02), (.28, .76, .29), '#c7c8d2', rotation=(0, 0, -side*24))
        root.scale = .85
    return root


class Arena(Entity):
    def __init__(self, style='temple', **kwargs):
        super().__init__(**kwargs)
        rng = random.Random(8)
        self.style = style
        self.static = Entity(parent=self)
        part(self.static, 'cube', (0, -.3, 0), (34, .5, 34), '#232839')
        for x in range(-7, 8):
            for z in range(-7, 8):
                shade = rng.choice(('#333b50', '#353e51', '#30394d', '#384053'))
                part(self.static, 'cube', (x*1.82, -.021, z*1.82), (1.78, .04, 1.78), shade)
        part(self, ring_mesh(128, .008), (0, .023, 0), 13.05, '#637d96', lit=False)
        part(self, ring_mesh(96, .006), (0, .025, 0), 7.3, '#53677d', lit=False)
        for side in (-1, 1):
            for z in (-10, -4, 4, 10):
                self._lantern(side*14, z)
        if style == 'temple':
            self._gate(0, 14.5, 1.0)
            self._gate(-11, 17, .65)
            self._gate(11, 17, .65)
            for side in (-1, 1):
                for z in (-9, -3, 3, 9):
                    part(self.static, 'cube', (side*15.7, 1.4, z), (1.2, 2.8, 1.2), '#484557')
                    part(self.static, 'cube', (side*15.7, 2.7, z), (1.8, .3, 1.8), '#625563')
                part(self.static, 'cube', (side*18, .7, 0), (1, 1.4, 34), '#494251')
        else:
            for x in range(-10, 11, 2):
                part(self.static, 'cube', (x, .028, -6), (1.0, .015, 3.0), '#778798')
            for side in (-1, 1):
                for z in (-10, 0, 10):
                    self._building(side*19, z, rng)
            for side in (-1, 1):
                part(self.static, 'cube', (side*8, .5, 15), (5, 1, 2.5), '#315367')
                part(self.static, 'cube', (side*8, 1.1, 15), (3, .7, 2), '#173344')
        for i in range(18):
            x = rng.uniform(-32, 32)
            self._building(x, rng.uniform(24, 32), rng)
        part(self, 'sphere', (-22, 24, 45), 7, '#d5d2d7', lit=False)
        for i in range(22):
            x, z = rng.uniform(-12, 12), rng.uniform(-12, 12)
            part(self.static, 'cube', (x, .012, z), (.04, .013, rng.uniform(.2, 1.2)), '#161e2c', rotation=(0, rng.uniform(0, 360), 0))
        # One draw call for the non-interactive scenery; dynamic VFX stay separate.
        self.static.combine(auto_destroy=True, include_normals=True)
        self.static.shader = TOON

    def _gate(self, x, z, size):
        gate = Entity(parent=self.static, position=(x, 0, z), scale=size)
        for side in (-1, 1):
            part(gate, 'cube', (side*4, 3.4, 0), (.67, 6.8, .7), '#a24858', rotation=(0, 0, side*-4))
            part(gate, 'cube', (side*4.1, .37, 0), (.85, .75, .84), '#2c2d42')
        part(gate, 'cube', (0, 5.1, 0), (10, .5, .6), '#a84858')
        part(gate, 'cube', (0, 6.7, 0), (11.5, .48, .9), '#402e42')
        part(gate, 'cube', (0, 6.36, 0), (10.4, .25, .65), '#d17275')
        part(gate, 'cube', (0, 5.85, -.02), (.72, 1.7, .22), '#b55c65')
        for side in (-1, 1):
            part(gate, 'cube', (side*5.35, 6.93, 0), (1.6, .3, .9), '#402e42', rotation=(0, 0, side*15))

    def _lantern(self, x, z):
        part(self.static, 'cube', (x, .14, z), (1, .28, 1), '#43485d')
        part(self.static, 'cube', (x, .8, z), (.36, 1.4, .36), '#42485a')
        part(self.static, 'cube', (x, 1.64, z), (.72, .67, .72), '#ddac77')
        part(self.static, 'cube', (x, 2.05, z), (.95, .18, .95), '#464358')
        for sx in (-.3, .3):
            for sz in (-.3, .3):
                part(self.static, 'cube', (x+sx, 1.64, z+sz), (.07, .72, .07), '#343345')

    def _building(self, x, z, rng):
        height = rng.uniform(5, 16)
        width = rng.uniform(3.3, 5.5)
        part(self.static, 'cube', (x, height/2-1, z), (width, height, 4), '#1b263b')
        for row in range(int(height/1.4)):
            for col in range(3):
                if rng.random() < .62:
                    part(self.static, 'cube', (x+(col-1)*1.05, row*1.4+.5, z-2.012),
                         (.36, .57, .025), rng.choice(('#668797', '#967d8f', '#4c697d')))
