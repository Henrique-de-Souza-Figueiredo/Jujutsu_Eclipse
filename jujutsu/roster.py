"""Character kits. Numeric values and input conditions are game adaptations.

References and the boundary between canon and game rules: docs/REFERENCIAS.md.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Technique:
    name: str
    cost: float
    cooldown: float
    mechanic: str
    instruction: str
    reach: float = 10


@dataclass(frozen=True)
class Character:
    id: str
    name: str
    title: str
    role: str
    accent: str
    outfit: str
    hair: str
    health: int
    speed: float
    power: float
    reach: float
    passive: str
    tips: str
    skills: tuple[Technique, ...]
    ultimate: str
    ultimate_kind: str
    source: str


def skill(name, cost, cooldown, mechanic, instruction, reach=10):
    return Technique(name, cost, cooldown, mechanic, instruction, reach)


ROSTER = (
    Character('gojo', 'Satoru Gojo', 'O MAIS FORTE', 'Controle de espaço',
              '#69ddff', '#1e223d', '#ecf3ff', 240, 5.9, 1.0, 2.5,
              'Seis Olhos: técnicas custam 15% menos energia.',
              'Azul atrai. Vermelho afasta. Use ambos em até 8 s para liberar Roxo.', (
        skill('Azul', 20, 5, 'blue', 'Q: cria uma atração na posição do alvo. Puxe-o para perto.', 12),
        skill('Vermelho', 25, 6, 'red', 'E: projétil de repulsão. Afasta e quebra a postura.', 15),
        skill('Roxo', 40, 12, 'purple', 'R após Q + E (8 s). Acerte ESPAÇO na faixa do QTE.', 18),
        skill('Infinito', 30, 14, 'infinity', 'T: barreira por 2,6 s. Domínios e dano à alma a atravessam.'),
    ), 'Vazio Ilimitado', 'void', 'Satoru_Gojo'),
    Character('yuji', 'Yuji Itadori', 'O RECEPTÁCULO', 'Pressão / precisão',
              '#ff6983', '#293044', '#eea3a4', 285, 6.5, 1.15, 2.5,
              'Corpo excepcional: recupera vigor mais rápido. Golpes atingem a alma.',
              'Aproxime-se com R. Alterne J, J, K e finalize com E no tempo certo.', (
        skill('Punho Divergente', 18, 4, 'divergent', 'Q a curta distância: golpe com um segundo impacto atrasado.', 3),
        skill('Black Flash', 28, 7, 'black_flash', 'E a até 3 m. Aperte ESPAÇO quando o cursor entrar na faixa.', 3),
        skill('Investida', 18, 5, 'rush', 'R: avança até o adversário e aplica um golpe.', 8),
        skill('Foco Amaldiçoado', 20, 12, 'focus', 'T: fortalece ataques e recupera parte do vigor por 6 s.'),
    ), 'Sequência de Black Flashes', 'black_rush', 'Yuji_Itadori'),
    Character('megumi', 'Megumi Fushiguro', 'DEZ SOMBRAS', 'Invocações / armadilhas',
              '#9c91ff', '#202b43', '#141e30', 240, 5.8, .92, 2.5,
              'Mestre das sombras: invocações duram 25% mais dentro do Jardim.',
              'Prenda com Sapo antes de Nue. T invoca Mahoraga: você passa a controlá-lo.', (
        skill('Cão Divino', 25, 9, 'dog', 'Q: invoca um cão que persegue e ataca por 7 s.'),
        skill('Nue', 28, 8, 'nue', 'E: marca uma descarga. O raio atordoa após 0,65 s.', 12),
        skill('Sapo', 18, 6, 'toad', 'R: língua à distância; enraíza o alvo se acertar.', 10),
        skill('Invocar Mahoraga', 65, 35, 'mahoraga', 'T: substitui Megumi por Mahoraga até o fim do round. Vida proporcional.'),
    ), 'Jardim das Sombras Quiméricas', 'shadow_domain', 'Megumi_Fushiguro'),
    Character('nobara', 'Nobara Kugisaki', 'BONECA DE PALHA', 'Marcas / detonação',
              '#ffb969', '#28334e', '#b97140', 230, 5.9, .95, 2.5,
              'Pregos aplicam marcas (máx. 6). Ressonância causa dano à alma.',
              'Acerte Q para fixar pregos. E usa a ligação; R consome as marcas.', (
        skill('Rajada de Pregos', 16, 3.5, 'nails', 'Q: dispara três pregos. Cada acerto aplica uma marca.', 14),
        skill('Ressonância', 24, 6, 'resonance', 'E: exige ao menos uma marca. Dano à alma, em qualquer distância.', 30),
        skill('Grampo', 25, 8, 'hairpin', 'R: detona todos os pregos presos; mais marcas, mais dano.', 30),
        skill('Campo de Pregos', 22, 9, 'nail_trap', 'T: instala uma armadilha onde o inimigo está. Saia da área.', 12),
    ), 'Ressonância: Ruptura', 'resonance_final', 'Nobara_Kugisaki'),
    Character('yuta', 'Yuta Okkotsu', 'A PROMESSA', 'Espada / suporte / cópia',
              '#8cebc8', '#e5e7df', '#202333', 260, 5.7, 1.02, 3.2,
              'Energia imensa: regeneração de energia 35% maior.',
              'E manifesta Rika; E novamente dispara Amor Puro. F abre seu domínio; B usa katanas.', (
        skill('Corte Imbuído', 18, 4, 'katana', 'Q: corte avançando. A lâmina tem alcance maior que punhos.', 4),
        skill('Rika / Amor Puro', 32, 15, 'rika', 'E: Rika por 8 s. E de novo com Rika: feixe por 30 de energia.'),
        skill('Cópia', 26, 7, 'copy', 'R com Rika/domínio: copia o inimigo. Uro: reflexão; Maki: Fala Amaldiçoada.', 15),
        skill('Técnica Reversa', 38, 15, 'heal', 'T: recupera 36 de vida. Crie distância antes de usar.'),
    ), 'Amor Mútuo Autêntico', 'mutual_love', 'Yuta_Okkotsu'),
    Character('maki', 'Maki Zenin', 'ESPECIALISTA EM ARMAS', 'Alcance / contra-ataque',
              '#9bd981', '#263c43', '#21443f', 280, 7.0, 1.17, 3.5,
              'Restrição Celestial: técnicas usam vigor físico; esquiva custa menos.',
              'T alterna naginata (alcance) e espada (dano). R prepara um contra-ataque.', (
        skill('Varredura', 16, 4, 'sweep', 'Q: giro em área. Naginata alcança inimigos mais distantes.', 4.5),
        skill('Estocada', 22, 5, 'thrust', 'E: estocada que causa grande dano à guarda.', 5),
        skill('Contra-ataque', 18, 9, 'counter', 'R: por 1,2 s, devolve o próximo ataque direto recebido.'),
        skill('Troca de Arma', 0, 1, 'weapon', 'T: alterna alcance da naginata e dano da espada.'),
    ), 'Arsenal Implacável', 'weapon_rush', 'Maki_Zenin'),
    Character('nanami', 'Kento Nanami', 'FEITICEIRO DE GRAU 1', 'Crítico / quebra de guarda',
              '#ecd095', '#baa685', '#d9b576', 270, 5.2, 1.12, 3,
              'Hora extra: ganha 18% de dano abaixo de 50% de vida.',
              'Marque com T. O QTE de Q tem o ponto crítico na proporção 7:3.', (
        skill('Proporção 7:3', 20, 5, 'ratio', 'Q a até 3,5 m. Acerte ESPAÇO na marca de 70% da barra.', 3.5),
        skill('Colapso', 28, 8, 'collapse', 'E: rompe o solo após um aviso; dano e quebra de guarda.', 9),
        skill('Hora Extra', 25, 14, 'overtime', 'R: aumenta dano e resistência à interrupção por 7 s.'),
        skill('Ponto Fraco', 18, 8, 'weakpoint', 'T: marca o alvo por 6 s; golpes contra ele causam mais dano.', 12),
    ), 'Black Flash: Hora Extra', 'ratio_rush', 'Kento_Nanami'),
    Character('todo', 'Aoi Todo', 'O MELHOR AMIGO', 'Trocas / ritmo',
              '#e9a1f5', '#413665', '#252232', 295, 5.8, 1.18, 2.7,
              'Ritmo: após uma troca, o próximo golpe em 3 s causa +35% de dano.',
              'Q troca as posições. E simula uma palma para abrir a defesa.', (
        skill('Boogie Woogie', 18, 5, 'swap', 'Q: troca instantaneamente sua posição com a do adversário.', 18),
        skill('Palma Falsa', 12, 7, 'feint', 'E: finta que interrompe a guarda inimiga por um instante.', 8),
        skill('Ombro Reforçado', 24, 6, 'shoulder', 'R: investida com resistência a golpes e grande impacto.', 8),
        skill('Reforço Corporal', 20, 12, 'reinforce', 'T: reduz dano recebido e fortalece os golpes por 5 s.'),
    ), 'Boogie Woogie: Irmandade', 'boogie_rush', 'Aoi_Todo'),
    Character('sukuna', 'Ryomen Sukuna', 'REI DAS MALDIÇÕES', 'Cortes / execução',
              '#ff5c62', '#e3daca', '#e69a99', 270, 6.0, 1.12, 2.7,
              'Santuário: use Desmantelar e Clivar para abrir a Fornalha por 12 s.',
              'Q atinge à distância; E exige contato. Ambos liberam R: Fuga.', (
        skill('Desmantelar', 17, 4, 'dismantle', 'Q: lança um corte veloz em linha reta.', 16),
        skill('Clivar', 23, 5, 'cleave', 'E a até 3 m: corte adaptativo, forte contra guarda.', 3),
        skill('Fuga', 38, 12, 'fuga', 'R após Q + E (12 s). Acerte o QTE para ampliar a chama.', 18),
        skill('Técnica Reversa', 38, 15, 'heal', 'T: recupera 36 de vida.'),
    ), 'Santuário Malevolente', 'shrine', 'Sukuna'),
    Character('mahito', 'Mahito', 'FORMA DA ALMA', 'Transformação / contato',
              '#76dbc8', '#363947', '#9fb8c7', 250, 5.9, 1.0, 2.8,
              'Alma maleável: reduz dano físico em 18%, mas não dano à alma.',
              'Q acumula distorção da alma. Yuji e Nobara atravessam sua resistência.', (
        skill('Transfiguração Ociosa', 22, 5, 'soul_touch', 'Q a até 3 m: aplica distorção; 3 marcas causam uma ruptura.', 3),
        skill('Lâmina Mutante', 20, 5, 'morph_blade', 'E: alonga o braço em uma lâmina de médio alcance.', 5.5),
        skill('Corpo de Morte', 28, 14, 'soul_armor', 'R: transforma o corpo; mais dano e armadura por 6 s.'),
        skill('Remodelar', 32, 15, 'reshape', 'T: reconstitui 30 de vida e remove lentidão.'),
    ), 'Autoencarnação da Perfeição', 'soul_domain', 'Mahito'),
    Character('jogo', 'Jogo', 'MALDIÇÃO VULCÂNICA', 'Fogo / controle de área',
              '#ff934f', '#a89451', '#393744', 225, 5.4, .95, 2.4,
              'Chamas do Desastre: técnicas de fogo aplicam queimadura por 3 s.',
              'Force esquivas com Q. E e R avisam a área antes da explosão.', (
        skill('Chamas do Desastre', 18, 4, 'fireball', 'Q: três bolas de fogo em leque.', 16),
        skill('Erupção', 25, 7, 'volcano', 'E: marca o chão sob o alvo; sai lava após 0,8 s.', 12),
        skill('Máximo: Meteoro', 38, 14, 'meteor', 'R: grande área, impacto após 1,7 s. Prenda o inimigo antes.', 13),
        skill('Insetos de Brasa', 23, 9, 'embers', 'T: invoca três insetos que perseguem e explodem.', 15),
    ), 'Caixão da Montanha de Ferro', 'volcano_domain', 'Jogo'),
    Character('choso', 'Choso', 'PINTURA DA MORTE', 'Preparação / projéteis',
              '#dc638b', '#e1dce2', '#292734', 260, 5.6, 1.02, 2.6,
              'Convergência: armazena até 3 cargas para fortalecer técnicas de sangue.',
              'Q comprime sangue. E gasta uma carga; R gasta todas em uma Supernova.', (
        skill('Convergência', 12, 2.5, 'convergence', 'Q: prepara uma carga de sangue (máximo 3).'),
        skill('Sangue Perfurante', 20, 4, 'piercing', 'E com carga: feixe muito rápido que perfura parte da defesa.', 18),
        skill('Supernova', 24, 8, 'supernova', 'R com cargas: detona sangue ao redor do alvo; escala com cargas.', 10),
        skill('Escamas Vermelhas', 24, 12, 'red_scale', 'T: reforça velocidade, dano e defesa por 6 s.'),
    ), 'Manipulação de Sangue: Torrente', 'blood_final', 'Choso'),
    Character('ryu', 'Ryu Ishigori', 'A MAIOR SAÍDA DE ENERGIA', 'Artilharia / feixes',
              '#c792ff', '#302640', '#322334', 285, 5.3, 1.12, 2.9,
              'Saída explosiva: projéteis causam 12% mais dano em disputas de feixes.',
              'Q carrega Granite Blast. T aumenta a próxima descarga. Uro pode devolvê-la.', (
        skill('Granite Blast', 26, 5, 'granite', 'Q: carregue no QTE; ESPAÇO na faixa aumenta potência e tamanho.', 18),
        skill('Rajada de Granito', 25, 7, 'granite_volley', 'E: leque de cinco descargas. Controle o espaço de esquiva.', 18),
        skill('Descarga Direta', 24, 6, 'point_blank', 'R a até 3,5 m: explosão de contato que lança o alvo.', 3.5),
        skill('Saída Máxima', 20, 12, 'output', 'T: aumenta em 40% a próxima descarga em até 6 s.'),
    ), 'Granite Blast: Saída Máxima', 'granite_final', 'Ryu_Ishigori'),
    Character('uro', 'Takako Uro', 'MANIPULAÇÃO DO CÉU', 'Reflexão / distorção',
              '#a5ddff', '#7c91b7', '#d6afc1', 240, 6.4, .98, 2.7,
              'Céu tangível: defesa perfeita também devolve projéteis.',
              'E dobra o céu e rebate projéteis. Q rompe a guarda. Áreas e domínios exigem esquiva.', (
        skill('Quebra-Gelo Fino', 24, 5, 'thin_ice', 'Q a até 4,5 m: quebra o espaço e atravessa a guarda.', 4.5),
        skill('Dobra do Céu', 25, 9, 'sky_guard', 'E: por 2,2 s, devolve projéteis ao lançador. Máximo de 2 reflexões.'),
        skill('Voo Distorcido', 20, 7, 'sky_flight', 'R: reposiciona atrás do alvo e flutua brevemente.', 12),
        skill('Manto Celeste', 22, 12, 'sky_mantle', 'T: por 6 s, a esquiva também ativa reflexão por 0,45 s.'),
    ), 'Ruptura do Firmamento', 'sky_final', 'Takako_Uro'),
)

MAHORAGA = Character('mahoraga', 'Mahoraga', 'GENERAL DIVINO DAS DEZ SOMBRAS', 'Adaptação / extermínio',
                    '#f4dd9a', '#c5b998', '#ede7d9', 355, 5.8, 1.25, 3.8,
                    'Adaptação: após 3 exposições a um fenômeno, reduz esse dano em 65%. A roda gira.',
                    'Q pune maldições. Receba e analise fenômenos diferentes. T acelera a última adaptação.', (
        skill('Espada do Extermínio', 20, 4, 'extermination', 'Q: corte de energia positiva; +50% contra Jogo e Mahito.', 4.5),
        skill('Impacto do General', 24, 6, 'general_slam', 'E: investida e esmagamento do solo; quebra de postura.', 9),
        skill('Corte Adaptativo', 30, 8, 'adaptive_slash', 'R: corte amplo. Após adaptação ao Infinito, atravessa a barreira.', 16),
        skill('Giro da Roda', 30, 10, 'wheel', 'T: avança a análise do último fenômeno sofrido e regenera 18 PV.'),
    ), 'General Divino: Extermínio', 'general_final', 'Eight-Handled_Sword_Divergent_Sila_Divine_General_Mahoraga')

ALL_CHARACTERS = ROSTER + (MAHORAGA,)
BY_ID = {c.id: c for c in ALL_CHARACTERS}
KEYS = ('q', 'e', 'r', 't')
DOMAIN_KINDS = {'void', 'shadow_domain', 'shrine', 'soul_domain', 'volcano_domain', 'mutual_love'}

PHENOMENA = {
    'physical': 'impacto', 'slash': 'cortes', 'fire': 'chamas', 'blood': 'sangue',
    'space': 'espaço', 'soul': 'alma', 'electric': 'eletricidade', 'beam': 'energia',
    'positive': 'energia positiva', 'domain': 'domínios', 'infinity': 'Infinito',
}
