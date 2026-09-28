# Jujutsu Kaisen | ECLIPSE

Jogo de luta 3D local contra a CPU, em Python/Ursina, com 12 personagens
selecionáveis, 48 técnicas, 12 supremos, modelos articulados estilizados e duas
arenas. Combates em melhor de três rounds, três dificuldades e modo de treino.

## Jogar

No Windows, abra **Jogar.bat** ou execute o `main.py` pelo PyCharm usando
o interpretador `.venv\Scripts\python.exe`.

```powershell
.\.venv\Scripts\python.exe main.py
```

Selecione seu lutador e clique em **02 / ADVERSÁRIO** para escolher a CPU.
Escolha arena, dificuldade e modo. **Enter** inicia. No menu, as setas também
selecionam personagens e **V** alterna entre você e adversário. Arraste o
modelo com o mouse para girá-lo.

Para reinstalar em outro ambiente com Python 3.12 ou superior:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## Controles

| Tecla | Ação |
| --- | --- |
| WASD | Mover na arena |
| J / clique esquerdo | Ataque leve; encadeia combo de três golpes |
| K / clique direito | Ataque forte; desgasta mais a guarda |
| L segurado | Defender; início da defesa permite um aparo perfeito |
| Espaço + direção | Esquiva com breve invulnerabilidade e custo de vigor |
| C | Pular; evita algumas áreas no chão |
| Q, E, R, T | Quatro técnicas do personagem |
| G segurado, parado | Recuperar energia; Maki recupera vigor |
| F | Supremo quando a barra alcançar 100% |
| Tab | Dossiê com técnicas, passiva e instruções; pausa a luta |
| Esc | Pausa / retorno ao menu na tela de resultado |
| M | Ligar/desligar efeitos sonoros |
| F3 no treino | Restaurar vida, recursos, recargas e supremo |
| Enter no resultado | Próximo round ou revanche |

## Elenco e diferenças

| Personagem | Como jogar |
| --- | --- |
| **Gojo** | Azul atrai, Vermelho repele. Q + E libera Roxo em R; T ativa Infinito. |
| **Yuji** | Pressão física, impacto duplo e Black Flash com precisão no QTE. |
| **Megumi** | Cão persegue, Sapo imobiliza, Nue atordoa; reposicione-se nas sombras. |
| **Nobara** | Acerte pregos com Q, use Ressonância em E ou consuma marcas com Grampo em R. |
| **Yuta** | Rika em E habilita Cópia em R. Katana de alcance maior e cura em T. |
| **Maki** | Vigor físico, estocadas, contra-ataque e troca entre naginata e espada. |
| **Nanami** | Acerte o QTE de 7:3, marque pontos fracos e ative Hora Extra. |
| **Todo** | Palmas trocam posições; fintas e bônus após a troca criam aberturas. |
| **Sukuna** | Desmantelar à distância e Clivar em contato liberam Fuga. |
| **Mahito** | Acumule distorção da alma, alongue a lâmina e transforme o corpo. |
| **Jogo** | Bolas de fogo, queimadura, insetos perseguidores e áreas de erupção. |
| **Choso** | Q prepara até três cargas. E consome uma; Supernova em R consome todas. |

QTEs de precisão pedem **Espaço na faixa iluminada**. Nos supremos, digite
a sequência mostrada. Erros ou demora reduzem a potência. Supremos inimigos
oferecem QTE defensivo. Se ambos têm domínio e medidor cheio, ocorre um
choque de domínios; completar o QTE permite sobrepor seu domínio ao inimigo.

O treino começa com supremo cheio, regenera o medidor e mantém a CPU parada.
O alvo recupera a vida quando ela termina. Use **Tab** para consultar condições
das técnicas; uma tentativa inválida informa o motivo sem gastar recurso.

## Implementação e validação

- `jujutsu/roster.py`: personagens, técnicas, custos e instruções.
- `jujutsu/combat.py`: regras independentes da renderização; IA, colisões,
  combos, guarda, status, invocações, domínios e QTEs.
- `jujutsu/models.py`: modelos esculpidos em código e animações por articulação.
- `jujutsu/effects.py`: projéteis, avisos de área, partículas e domínios.
- `jujutsu/ui.py` / `game.py`: menus, dossiês, interface e fluxo de rounds.
- `jujutsu/audio.py`: efeitos sintetizados, com cache local.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe main.py --smoke-test
```

O teste gráfico usa renderização real fora da tela e salva imagens em
`artifacts/`. Exercita os 12 modelos, todas as técnicas e supremos,
as duas arenas, QTEs, menus e troca de rounds. Os testes de combate
verificam condições, dano, defesa, invocações, colisão de projéteis,
encerramento e partidas contra a IA.

Esta versão tem arte estilizada própria e mecânicas balanceadas para o jogo.
Os poderes foram pesquisados na wiki; as condições adaptadas e as fontes
estão em [docs/REFERENCIAS.md](docs/REFERENCIAS.md).

Para iniciar sem som: `python main.py --mute`.
