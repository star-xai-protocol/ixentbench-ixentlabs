# -*- coding: utf-8 -*-
"""
ixentbench/play.py
Modo Solo — BYOK, Modelo Local, Agente Custom y Sponsored.
"""

import hashlib
import pathlib
import time
import webbrowser
import click
import requests

from ixentbench.auth import get_firebase_token
from ixentbench.config import (
    LOCAL_MODEL_URL, IXENT_SDK_URL, VISUALIZER_URL,
    PROMPTS_DIR, STRATEGIES_DIR, validate_env,
)
from ixentbench.engines import get_move_byok, get_move_local, get_move_agent


# =============================================================================
# HELPER: Carga de archivos opcionales
# =============================================================================

# Límite de seguridad: protección Denial of Wallet (DoW)
MAX_CHARS = 2222

def _load_text_file(path: str, label: str, save_dir: pathlib.Path) -> str:
    """
    Carga un archivo de texto con búsqueda inteligente:
    si no existe en la ruta indicada, lo busca en save_dir.
    """
    p = pathlib.Path(path)

    if not p.exists():
        suggested_p = save_dir / p.name
        if suggested_p.exists():
            p = suggested_p
        else:
            click.echo(f"❌ File not found: {path}", err=True)
            click.echo(f"   Tip: Place your file in {save_dir} or provide the full path.", err=True)
            raise SystemExit(1)

    content = p.read_text(encoding="utf-8").strip()

    if len(content) > MAX_CHARS:
        click.echo(f"❌ {label} too long: {len(content)} chars (max {MAX_CHARS}).", err=True)
        raise SystemExit(1)

    click.echo(f"📄 {label} loaded: {p.name} ({len(content)} chars)")

    # Guardar en la carpeta estándar si vino de una ruta externa
    saved = save_dir / p.name
    if not saved.exists():
        saved.write_text(content, encoding="utf-8")
        click.echo(f"   💾 Saved to: {saved}")

    return content


# =============================================================================
# FUNCIÓN PRINCIPAL
# =============================================================================

def run_play(
    session_id: str,
    mode: str,
    prompt_file: str | None,
    strategy_file: str | None,
    local_url: str | None,
    agent_script: str | None,
):
    local_url = local_url or LOCAL_MODEL_URL

    # =========================================================================
    # 🛡️ ESCUDO ANTI-INYECCIÓN — Benchmark mode no permite modificaciones
    # =========================================================================
    mode = mode.lower().strip()

    if mode == "benchmark":
        if prompt_file or strategy_file or agent_script:
            click.echo("\n" + "═" * 55, err=True)
            click.echo(" 🚨 SECURITY LOCKOUT: OFFICIAL BENCHMARK MODE 🚨",  err=True)
            click.echo("═" * 55, err=True)
            click.echo("❌ --prompt-file, --strategy-file and --agent-script", err=True)
            click.echo("   are not allowed in official benchmark evaluations.", err=True)
            click.echo("   Use --mode lab to experiment with injections.\n",   err=True)
            raise SystemExit(1)
    # =========================================================================

    # Validación de flags incompatibles
    if agent_script and (local_url or prompt_file):
        click.echo("❌ --agent-script cannot be combined with --local-url or --prompt-file.", err=True)
        raise SystemExit(1)

    # Carga de archivos opcionales
    prompt_text   = _load_text_file(prompt_file,   "Prompt Injection", PROMPTS_DIR)    if prompt_file   else None
    strategy_text = _load_text_file(strategy_file, "Strategy",         STRATEGIES_DIR) if strategy_file else None
    prompt_hash   = hashlib.sha256(prompt_text.encode()).hexdigest() if prompt_text else None

    # Autenticación
    click.echo("\n🔐 Authenticating with iXentLabs...")
    jwt     = get_firebase_token()
    headers = {"X-Firebase-Token": jwt, "Content-Type": "application/json"}
    click.echo("✅ Login successful.")

    # Validar sesión e iniciar partida
    click.echo(f"\n🎮 Validating session {session_id}...")
    resp = requests.post(
        f"{IXENT_SDK_URL}/play",
        headers = headers,
        json    = {
            "session_id":        session_id,
            "prompt_injection":  prompt_text,
            "prompt_hash":       prompt_hash,
            "agent_description": strategy_text,
            "strategy":          strategy_text,
            "is_local_model":    bool(local_url or agent_script),
            "is_custom_agent":   bool(agent_script),
        },
        timeout = 30,
    )

    if not resp.ok:
        click.echo(f"❌ Server error: {resp.text}", err=True)
        raise SystemExit(1)

    game_data = resp.json()
    if not game_data.get("success"):
        click.echo(f"❌ {game_data.get('msg')}", err=True)
        raise SystemExit(1)

    # 🛡️ Aviso de moderación — el contenido pudo ser descartado sin bloquear la partida
    if game_data.get("moderation_notice"):
        click.echo(f"\n⚠️  {game_data['moderation_notice']}\n")

    # Extraer datos de la sesión
    game_player_id = game_data["game_player_id"]
    current_state  = game_data["state"]
    motor_url      = game_data["motor_url"]
    model_name     = game_data.get("model", "AI Agent")
    session_info   = game_data.get("session", {})
    system_prompt  = game_data.get("system_prompt", "")
    is_sponsored   = game_data.get("is_sponsored", False)
    # Margen de seguridad: +20 turnos sobre el máximo oficial para absorber
    # movimientos rechazados por el servidor sin penalizar el conteo de la partida.
    max_turns      = current_state.get("meta", {}).get("max_moves", 222) + 20

    # Validar que haya al menos una vía de ejecución configurada
    if not agent_script and not local_url and not is_sponsored:
        validate_env()

    # Mostrar resumen de la sesión
    click.echo(f"✅ Game started — ID: {game_player_id}")
    click.echo(f"   Model: {model_name} | Level: {game_data.get('level', '?')}")
    if is_sponsored:
        click.echo("   💳 Mode: iXentLabs Sponsored")
    elif agent_script:
        click.echo(f"   🤖 Mode: Custom Agent ({agent_script})")
    elif local_url:
        click.echo(f"   💻 Mode: Local Model ({local_url})")
    else:
        click.echo(f"   🔑 Mode: BYOK ({session_info.get('provider', 'google').capitalize()})")

    # Abrir visualizador
    game_id = current_state.get("meta", {}).get("live_game_id", "")
    vis_url = f"{VISUALIZER_URL}?game_id={game_id}" if game_id else VISUALIZER_URL
    webbrowser.open(vis_url)
    click.echo(f"🌐 Visualizer: {vis_url}")

    # Acumuladores de métricas de sesión
    s_tokens = s_input = s_output = s_thinking = s_secs = s_gen = 0

    click.echo("\n🚀 Game starting...\n")
    turn          = 0
    entropy_shown = False

    # =========================================================================
    # GAME LOOP
    # =========================================================================
    while turn < max_turns:
        turn += 1
        click.echo(f"\n🧠 [TURN {turn}] {model_name} thinking...")

        # Seleccionar motor según el modo
        if agent_script:
            cmd, reasoning, td = get_move_agent(agent_script, current_state)
        elif local_url:
            cmd, reasoning, td = get_move_local(model_name, system_prompt, current_state, local_url)
        else:
            cmd, reasoning, td = get_move_byok(model_name, system_prompt, current_state, session_info)

        if not cmd:
            click.echo("⚠️  No valid move generated (JSON parse error / model failure). Forfeiting turn as invalid syntax.")
            cmd = "INVALID_FORMAT"

        # Acumular métricas de tokens
        if td:
            s_tokens   += td["total"]
            s_input    += td.get("input_tokens",      0)
            s_output   += td.get("output_tokens",     0)
            s_thinking += td.get("thinking_tokens",   0)
            s_secs     += td.get("turn_inference_sec",0)
            s_gen      += td.get("output_tokens",     0) + td.get("thinking_tokens", 0)

        avg_tps = round(s_gen / s_secs, 2) if s_secs > 0 else 0
        click.echo(f"   📊 Tokens: {td['total'] if td else 0} (Session: {s_tokens})")
        click.echo(f"   💭 {(reasoning or '—')[:120].rstrip()}{'…' if reasoning and len(reasoning) > 120 else ''}")
        click.echo(f"   ⚡ {cmd}")

        # Enviar movimiento al servidor
        try:
            move_resp = requests.post(
                f"{IXENT_SDK_URL}/move",
                headers = headers,
                json    = {
                    "game_player_id":  game_player_id,
                    "command":         cmd,
                    "reasoning":       reasoning,
                    "motor_url":       motor_url,
                    "evaluation_id":   game_id,   # ← garantiza ID largo en toda circunstancia
                    "session_id":      session_id, # ← necesario para registro en benchmark_results
                "token_usage": {
                        "total":                 s_tokens,
                        "total_input_tokens":    s_input,
                        "total_output_tokens":   s_output,
                        "total_thinking_tokens": s_thinking,
                        "total_inference_sec":   round(s_secs, 2),
                        "average_tps":           avg_tps,
                        "turn_input_tokens":     td.get("input_tokens",      0) if td else 0,
                        "turn_output_tokens":    td.get("output_tokens",     0) if td else 0,
                        "turn_thinking_tokens":  td.get("thinking_tokens",   0) if td else 0,
                        "turn_inference_sec":    td.get("turn_inference_sec",0) if td else 0,
                        "turn_tps":              td.get("turn_tps",          0) if td else 0,
                        "is_local_hardware":     td.get("is_local_hardware", False) if td else False,
                    },
                },
                timeout = 610,
            )
            move_resp.raise_for_status()
            data = move_resp.json()
        except Exception as e:
            click.echo(f"❌ Move error: {e}")
            time.sleep(2)
            continue

        # Actualizar estado
        if "state" in data:
            current_state = data["state"]
        gym = data.get("gym_metrics", {})

        # Gestionar respuesta del servidor
        if not data.get("success", True):
            click.echo(f"   🚫 REJECTED: {data.get('msg')}")
            if gym.get("terminated", False):
                click.echo("   🏁 Server declared end of game (TIMEOUT). Stopping.")
                break
            if not current_state.get("status", {}).get("game_over"):
                time.sleep(2)
                continue
        else:
            click.echo("   👍 ACCEPTED")

        # Detectar evento de entropía
        if not entropy_shown:
            for entry in current_state.get("data", {}).get("history", []):
                if "[EVENT]" in str(entry):
                    click.echo(f"\n   ⚠️  ENTROPY EVENT: {entry}\n")
                    entropy_shown = True
                    break

        # Detectar fin de partida
        if gym.get("terminated") or gym.get("truncated") or current_state.get("status", {}).get("game_over"):
            st     = current_state.get("status", {})
            result = st.get("result", "UNKNOWN")
            score  = current_state.get("scoring", {}).get("benchmark_score", {}).get("P1", 0)
            mice   = st.get("mice_rescued",        {}).get("P1", 0)
            total  = st.get("total_mice_per_player", 0)
            click.echo(f"\n{'🏆' if result == 'VICTORY' else '💀'} GAME OVER: {result}")
            click.echo(f"   Score:   {score}")
            click.echo(f"   Mice:    {mice}/{total}")
            click.echo(f"   Turns:   {turn}")
            click.echo(f"   Tokens:  {s_tokens}")
            click.echo(f"   Time:    {round(s_secs, 1)}s")
            click.echo(f"   Avg TPS: {avg_tps}")
            break

    click.echo("\n✅ Session complete.")