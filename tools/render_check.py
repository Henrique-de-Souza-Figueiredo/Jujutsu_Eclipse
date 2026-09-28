"""Real offscreen GPU render check, exercised with main.py --smoke-test."""
from pathlib import Path

from panda3d.core import Filename
from ursina import camera, Vec3, scene

from jujutsu.combat import V2
from jujutsu.roster import ROSTER


def run(app, game):
    directory = Path(__file__).resolve().parent.parent / 'artifacts'
    directory.mkdir(exist_ok=True)
    # The controller is advanced explicitly so tests do not depend on frame rate.
    game.enabled = False

    def frame(count=2):
        for _ in range(count):
            app.taskMgr.step()
            app.graphicsEngine.renderFrame()

    def save(name):
        frame(3)
        assert app.win.saveScreenshot(Filename.fromOsSpecific(str(directory / name)))

    save('menu.png')
    game.toggle_dossier()
    save('guia.png')
    game.toggle_dossier()
    for index, spec in enumerate(ROSTER):
        game.select_character(index)
        frame()
        if spec.id in ('nobara', 'jogo', 'sukuna'):
            save(f'modelo_{spec.id}.png')
    game.selected = [0, 8]
    game.training = True
    game.start_match()
    game.intro = 0
    game.tick(.016)
    save('combate.png')

    for index, spec in enumerate(ROSTER):
        game.selected[0] = index
        game.start_match()
        game.intro = 0
        battle = game.battle
        for slot in range(4):
            battle.restore_training()
            a, b = battle.fighters
            a.pos, b.pos = V2(-1.3, 0), V2(1.3, 0)
            a.hp -= 60
            a.blood = 2
            a.statuses.update(blue_ready=8, red_ready=8, dismantle_ready=12, cleave_ready=12, rika=8)
            b.marks['nails'] = 3
            assert battle.cast(0, slot), (spec.id, slot)
            if battle.qte:
                game.tick(.016)
                if spec.id == 'yuji':
                    save('qte_precisao.png')
                battle.qte.elapsed = battle.qte.duration*battle.qte.target
                game.input('space')
            for _ in range(20):
                game.tick(.05)
            frame()
        battle.restore_training()
        assert battle.ultimate(0)
        game.tick(.016)
        if spec.id == 'gojo':
            save('qte_sequencia.png')
        for key in battle.qte.keys:
            game.input(key)
        for _ in range(12):
            game.tick(.05)
        frame()
        if spec.id == 'gojo':
            save('dominio.png')
        assert len(scene.entities) < 2500, 'Entity leak while changing characters'
    game.arena_style = 'city'
    game.start_match()
    game.intro = 0
    game.tick(.016)
    save('shibuya.png')
    game.toggle_pause()
    save('pausa.png')
    game.toggle_pause()
    game.training = False
    game.start_match()
    game.intro = 0
    game.battle.finish(0)
    game.tick(.016)
    assert game.scores == [1, 0]
    save('resultado.png')
    game.continue_match()
    assert not game.battle.projectiles and not game.battle.qte
    game.show_menu()
    frame()
    print('RENDER OK: 12 modelos, 48 técnicas, 12 supremos, duas arenas, QTEs e reinício de round.')
    print('Capturas:', directory)
