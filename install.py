# -*- coding: utf-8 -*-
"""
ixentbench/install.py
Lógica de bienvenida — se dispara la primera vez que el usuario
ejecuta cualquier comando ixentbench.
Crea ~/ixentbench/ con .env, README.html y env_configuration.html.
"""

import shutil
import pathlib

ENV_CONTENT = """\
# ─────────────────────────────────────────────────────────────
#  iXentBench — Player Configuration
#  ⚠️  Keep this file ONLY on your local machine.
#  ⚠️  NEVER share it, send it or upload it to anyone.
#  ⚠️  iXentLabs never downloads or accesses this file.
#      Your keys stay on your machine at all times.
#
#  HOW TO OPEN THIS FILE:
#  Mac:     Right click → Open With → TextEdit
#  Windows: Right click → Open With → Notepad
# ─────────────────────────────────────────────────────────────

# ── OPTION A: Cloud AI — BYOK (Bring Your Own Key) ───────────
#  Fill in only the key for the model you want to use.
#
#  Get your Gemini key at:    https://aistudio.google.com
GOOGLE_API_KEY=
#
#  Get your Anthropic key at: https://console.anthropic.com
ANTHROPIC_API_KEY=
#
#  Get your OpenAI key at:    https://platform.openai.com
OPENAI_API_KEY=
#
#  Get your Grok key at:      https://console.x.ai
GROK_API_KEY=
#
#  Get your DeepSeek key at:  https://platform.deepseek.com
DEEPSEEK_API_KEY=

# ── OPTION B: Local Open Source Model ────────────────────────
#  Run Ollama, LM Studio or llama.cpp on your machine first.
#  Examples:
#    Ollama:    http://localhost:11434/v1
#    LM Studio: http://localhost:1234/v1
#    llama.cpp: http://localhost:8080/v1
#
LOCAL_MODEL_URL=

# ── OPTION C: Custom Agent Script ────────────────────────────
# Write your own Python agent and run it with:
#   ixentbench play --session IQWUWP --agent-script ./my_agent.py
#
# Your script receives the board state via stdin (JSON)
# and must return a move via stdout (JSON):
#   {"command": "G4@P21(b=0)+90", "reasoning": "..."}
#
# No API Key needed for custom agents.

# ── OPTION D: iXentLabs Sponsored ────────────────────────────
#  If you selected "Use iXentLabs credits" on the web,
#  leave all keys empty. The cloud handles everything.
# ─────────────────────────────────────────────────────────────
"""

LICENSE_CONTENT = """\
iXentBench™ NON-COMMERCIAL SOURCE LICENSE

Copyright (c) 2026 iXentLabs / Antoni Guasch / María Isabel Valdez (iXent Games SL).
All rights reserved.

This software and associated documentation files (the "Software") are copyrighted
material. The intellectual property rights of the mechanics, design, name, and concept
derived from the original physical board game and digital applications belong
exclusively to the authors.

Permission is hereby granted, free of charge, to any person obtaining a copy of this
Software, to deal in the Software without restriction solely for academic research,
educational, and non-commercial personal purposes, including the rights to use, copy,
modify, and merge copies of the Software, subject to the following conditions:

1. The above copyright notice and this permission notice shall be included in all
   copies or substantial portions of the Software.

2. Any publication, paper, or presentation making use of the Software must include
   an appropriate citation to iXentBench™ and iXentLabs.

COMMERCIAL RESTRICTION: The Software may not be used, in whole or in part, for any
Commercial Purpose by any corporation, business entity, organization, or private
individual. "Commercial Purpose" includes, without limitation:

   a) Selling, licensing, or renting the Software.
   b) Providing the Software as a service (SaaS) to third parties in exchange for
      financial compensation.
   c) Using the Software to evaluate, train, or benchmark Artificial Intelligence
      models that serve an ultimate commercial or corporate purpose.
   d) Integrating the Software into a larger commercial product or service.

Any commercial use requires a separate, written license agreement ("Commercial
License") explicitly granted by the copyright holders.

DISCLAIMER: THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN
AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH
THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
"""

def welcome_message(ixent_home: pathlib.Path):
    """Muestra el mensaje de bienvenida en el terminal."""
    print("\n" + "=" * 55)
    print("  ✅ iXentBench installed successfully!")
    print("=" * 55)
    print(f"\n  📁 Player folder:  {ixent_home}")
    print(f"  📖 Manual:         double-click README.html")
    print(f"  🔑 API Key setup:  double-click env_configuration.html")
    print(f"  🕹️  Solo Rules:     double-click GAME_RULES_vSOLO.html")
    print(f"  ⚔️  Arena Rules:    double-click GAME_RULES_vARENA.html")
    print(f"  🧠 System Prompt:  double-click SYSTEM_PROMPT_vREFERENCE.html")
    print(f"  🤖 Agent Template: check agent_template.py")
    print(f"  📄 Config file:    .env  (add your API Key here)")
    print(f"\n  Next steps:")
    print(f"  1. Open your player folder:")
    print(f"     {ixent_home}")
    print(f"  2. Double-click env_configuration.html")
    print(f"  3. Follow the instructions to add your API Key")
    print(f"  4. Run from ANY folder:  ixentbench login")
    print(f"  5. Go to ixentlabs.com to create your session")
    print(f"  6. Run from ANY folder:  ixentbench play --session YOUR_SESSION_ID")
    print(f"\n  iXentLabs never accesses your keys or this folder.")
    print("=" * 55 + "\n")


def first_run_setup():
    """
    Punto de entrada — llamado desde cli.py antes de cualquier comando.
    Crea la estructura base la primera vez, y actualiza los assets fijos siempre.
    """
    ixent_home = pathlib.Path.home() / "ixentbench"
    is_new_install = not ixent_home.exists()

    # 1. SI ES UNA INSTALACIÓN NUEVA: Creamos carpetas y el .env virgen
    if is_new_install:
        ixent_home.mkdir(parents=True, exist_ok=True)
        (ixent_home / "prompts").mkdir(exist_ok=True)
        (ixent_home / "strategies").mkdir(exist_ok=True)
        (ixent_home / ".env").write_text(ENV_CONTENT, encoding="utf-8")

    # 2. PARA TODOS: Generamos/Actualizamos la Licencia directamente desde el código
    (ixent_home / "LICENSE").write_text(LICENSE_CONTENT, encoding="utf-8")

    # 3. PARA TODOS: Copiamos/Actualizamos los archivos HTML desde el paquete
    pkg_dir = pathlib.Path(__file__).parent
    for filename in ["README.html", "env_configuration.html", "GAME_RULES_vSOLO.html", "GAME_RULES_vARENA.html", "SYSTEM_PROMPT_vREFERENCE.html", "agent_template.py"]:
        src = pkg_dir / filename
        if src.exists():
            shutil.copy(src, ixent_home / filename)

    # 4. Mensaje de bienvenida SOLO la primera vez
    if is_new_install:
        welcome_message(ixent_home)