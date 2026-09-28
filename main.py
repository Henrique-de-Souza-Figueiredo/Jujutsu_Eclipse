"""Run Jujutsu Kaisen: Eclipse with Python 3.12+ and Ursina 8.3."""
import argparse
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description='Jujutsu Kaisen: Eclipse — arena de luta 3D')
    parser.add_argument('--smoke-test', action='store_true', help='Verifica modelos e renderiza cenas sem abrir janela')
    parser.add_argument('--mute', action='store_true', help='Inicia sem áudio')
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=720)
    args = parser.parse_args()
    try:
        from panda3d.core import loadPrcFileData
        loadPrcFileData('', 'framebuffer-multisample 1\nmultisamples 2\nsync-video true\nnotify-level warning')
        if args.smoke_test or args.mute:
            loadPrcFileData('', 'audio-library-name null')
        from ursina import Ursina, application, window, camera
    except ImportError:
        print('Instale as dependências: python -m pip install -r requirements.txt')
        return 1
    application.asset_folder = Path(__file__).resolve().parent
    app = Ursina(title='Jujutsu Kaisen | ECLIPSE', borderless=False, fullscreen=False,
                 size=(args.width, args.height), forced_aspect_ratio=16/9,
                 development_mode=False, editor_ui_enabled=False,
                 window_type='offscreen' if args.smoke_test else 'onscreen')
    window.exit_button.enabled = False
    window.fps_counter.enabled = False
    camera.ui_lens.set_film_size(20 * (16/9), 20)
    from jujutsu.game import Game
    game = Game(muted=args.mute or args.smoke_test, offscreen=args.smoke_test)
    if args.smoke_test:
        from tools.render_check import run
        run(app, game)
        app.destroy()
    else:
        app.run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
