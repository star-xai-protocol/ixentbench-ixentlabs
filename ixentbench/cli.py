# -*- coding: utf-8 -*-
"""
ixentbench/cli.py
Punto de entrada CLI — comando `ixentbench`
"""

import click
from ixentbench import __version__
from ixentbench.install import first_run_setup

# =============================================================================
# ALFOMBRA ROJA: Ejecución inmediata al cargar el comando.
# Esto asegura que la carpeta ~/ixentbench se cree incluso si el usuario
# solo escribe 'ixentbench' para ver la ayuda.
# =============================================================================
first_run_setup()


@click.group()
@click.version_option(version=__version__, prog_name="ixentbench")
def main():
    """
    iXentBench™ — iXentBench — The Benchmark Beyond AI Reasoning

    Causal spatial reasoning at 4×10⁸⁵ scale.
    Developed by iXentLabs (iXent Games S.L.)
    """
    # No es necesario ponerlo aquí dentro, ya se ejecuta arriba.
    pass


# =============================================================================
# ixentbench play
# =============================================================================
@main.command()
@click.option("--session",       required=True,  help="Session ID from iXentLabs web portal")
@click.option("--mode",          required=True,
              type=click.Choice(["benchmark", "lab"], case_sensitive=False),
              help="Evaluation mode: 'benchmark' (official, no injections) or 'lab' (experimental)")
@click.option("--prompt-file",   default=None,   help="Prompt Injection .txt (added to SYSTEM PROMPT)")
@click.option("--strategy-file", default=None,   help="Strategy .txt (logged for Talent Hub, NOT sent to AI)")
@click.option("--local-url",     default=None,   help="Local model URL — e.g. http://localhost:11434/v1")
@click.option("--agent-script",  default=None,   help="Custom agent .py script path")
def play(session, mode, prompt_file, strategy_file, local_url, agent_script):
    """Run iXentBench Solo (BYOK, Local model, Custom agent or Sponsored)."""
    
    # --- INICIO COMPROBACIÓN DE ACTUALIZACIONES ---
    import requests
    from ixentbench import __version__
    try:
        latest_version = requests.get("https://pypi.org/pypi/ixentbench/json", timeout=1.5).json()["info"]["version"]
        if latest_version != __version__:
            click.secho(f"\n⚠️  New version available ({latest_version}). Run 'pip install --upgrade ixentbench' to update.", fg="yellow")
    except Exception:
        pass # Si falla internet o PyPI, ignoramos el error en silencio para que pueda jugar offline/local
    # --- FIN COMPROBACIÓN DE ACTUALIZACIONES ---

    from ixentbench.play import run_play
    run_play(
        session_id    = session,
        mode          = mode,
        prompt_file   = prompt_file,
        strategy_file = strategy_file,
        local_url     = local_url,
        agent_script  = agent_script,
    )

# =============================================================================
# ixentbench arena
# =============================================================================
@main.group()
def arena():
    """iXentBench Arena — Multiplayer mode (1v1, 2v2, 4v4, Human vs AI)."""
    pass


@arena.command("create")
@click.option("--mode",  default="1v1",
              type=click.Choice(["1v1", "2v2", "4v4", "human"], case_sensitive=False),
              help="Game mode")
@click.option("--level", default=1, type=click.IntRange(1, 4), help="Level (1-4)")
@click.option("--model", default=None, help="AI model to use (default: gemini-2.5-flash or Human)")
@click.option("--prompt-file",   default=None, help="Prompt Injection .txt (added to SYSTEM PROMPT)")
@click.option("--strategy-file", default=None, help="Strategy .txt (logged for Talent Hub, NOT sent to AI)")
@click.option("--room",          default=None, help="Pre-generated room code from Web UI (e.g. IXENT-4X7K)")
def arena_create(mode, level, model, prompt_file, strategy_file, room):
    """Create a new Arena room. You become the host."""
    from ixentbench.arena import create_room
    create_room(mode=mode, level=level, model=model, prompt_file=prompt_file, strategy_file=strategy_file, room_code=room)


@arena.command("join")
@click.option("--room", required=True, help="Room code — e.g. IXENT-4X7K")
@click.option("--model", default=None, help="AI model to use (default: gemini-2.5-flash or Human)")
@click.option("--prompt-file",   default=None, help="Prompt Injection .txt (added to SYSTEM PROMPT)")
@click.option("--strategy-file", default=None, help="Strategy .txt (logged for Talent Hub, NOT sent to AI)")
def arena_join(room, model, prompt_file, strategy_file):
    """Join an existing Arena room."""
    from ixentbench.arena import join_room
    join_room(room_code=room, model=model, prompt_file=prompt_file, strategy_file=strategy_file)


# =============================================================================
# ixentbench login / status / prompts
# =============================================================================
@main.command()
def login():
    """Force Google re-authentication."""
    from ixentbench.auth import force_login
    force_login()


@main.command()
def status():
    """Show current credentials and session status."""
    from ixentbench.config import show_status
    show_status()

# =============================================================================
# ixentbench prompts
# =============================================================================
@main.group()
def prompts():
    """Manage your saved Prompt Injection files."""
    pass


@prompts.command("list")
def prompts_list():
    """List all saved prompt injection files."""
    from ixentbench.config import list_prompts
    list_prompts()

# =============================================================================
# ixentbench strategies
# =============================================================================
@main.group()
def strategies():
    """Manage your saved Strategy files."""
    pass

@strategies.command("list")
def strategies_list():
    """List all saved strategy files."""
    from ixentbench.config import list_strategies
    list_strategies()

if __name__ == "__main__":
    main()