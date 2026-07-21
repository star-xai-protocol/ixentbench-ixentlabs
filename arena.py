# -*- coding: utf-8 -*-
"""
ixentbench/arena.py
Modo Arena — Bucle multijugador completo (1v1, 2v2, 4v4, Human vs AI).
"""

import os
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
from ixentbench.play import _load_text_file # Importamos el helper para cargar y validar txt


# =============================================================================
# HELPER: Inyección de token fresco en el entorno
# =============================================================================

def _inject_fresh_token() -> str:
    """
    Obtiene un token Firebase fresco via auth.py y lo inyecta en la
    variable de entorno FIREBASE_ID_TOKEN para que el SDK lo use.
    Usa el flujo OAuth completo de auth.py — más robusto que el refresco
    manual del SDK para sesiones interactivas de usuario.
    """
    token = get_firebase_token()
    if token:
        os.environ["FIREBASE_ID_TOKEN"] = token
    return token


# =============================================================================
# BUCLE MAESTRO DE ARENA
# =============================================================================

def _run_arena_loop(
    player_slot: str,
    motor_url: str,
    mode: str,
    model_name: str,
    system_prompt: str,
    session_info: dict,
    local_url: str | None,
    agent_script: str | None,
    game_id: str,
    game_player_id: str,
):
    """
    Bucle de juego Arena para un jugador.
    Espera el turno, llama al motor LLM y envía el movimiento via HTTP.

    Args:
        player_slot:    rol del jugador ("P1"..."P4")
        motor_url:      URL del servidor Arena en Cloud Run
        mode:           modo de juego ("ffa", "team_a", "team_b")
        model_name:     nombre del modelo (para logging)
        system_prompt:  system prompt completo para el agente
        session_info:   metadatos de sesión (incluye "provider")
        local_url:      URL del modelo local, o None
        agent_script:   ruta al script custom, o None
        game_id:        identificador de la partida (para el visualizador)
        game_player_id: ID de sesión del jugador (para el servidor)
    """
    click.echo(f"\n🚀 Arena Game Loop started — Playing as {player_slot}")

    # Abrir visualizador UNA SOLA VEZ
    # Mostrar URL del visualizador sin forzar apertura
    if game_id:
        if model_name.lower() in ("human", "h_expert"):
            vis_url = f"{VISUALIZER_URL}?game_id={game_id}&mode=human&player={player_slot}"
        else:
            vis_url = f"{VISUALIZER_URL}?game_id={game_id}&player={player_slot}"
    else:
        vis_url = VISUALIZER_URL
        
    click.echo(f"🌐 Live Visualizer: {vis_url}")
    click.echo("   (Opening automatically in your browser. If it fails, copy/paste the link above)")
    webbrowser.open(vis_url)  # Abre los visualizadores en modo WEB

    # Cabeceras HTTP — se reconstruyen en cada petición para usar token fresco
    def _headers():
        return {"X-Firebase-Token": _inject_fresh_token(), "Content-Type": "application/json"}

    # Acumuladores de métricas de sesión
    s_tokens = s_input = s_output = s_thinking = s_secs = s_gen = 0

    turn      = 0
    game_over = False

    # =========================================================================
    # GAME LOOP
    # =========================================================================
    while not game_over:
        click.echo(f"\n⏳ [{player_slot}] Waiting for my turn...")

        # Polling a /arena/turn hasta que sea nuestro turno
        current_state = None
        while True:
            try:
                resp = requests.get(
                    f"{IXENT_SDK_URL}/arena/turn/{game_player_id}",
                    headers = _headers(),
                    timeout = 10,
                )
                if resp.ok:
                    data = resp.json()
                    
                    # Partida terminada mientras esperábamos
                    if data.get("status", {}).get("game_over", False):
                        click.echo("\n🏁 Game Over detected while waiting.")
                        game_over = True
                        break
                    
                    # Es nuestro turno
                    if data.get("your_turn", False):
                        current_state = data.get("state", data)
                        break
            except Exception:
                pass
            time.sleep(2)

        if game_over or current_state is None:
            break

        turn += 1

        # --- NUEVO: Bucle de espera para humanos ---
        if model_name.lower() in ("human", "h_expert"):
            click.echo(f"\n🕹️ [TURN {turn}] It's your turn! Make your move directly in the Web Visualizer.")
            # La terminal solo se queda esperando a que el humano mueva en la web
            while True:
                time.sleep(3)
                try:
                    resp = requests.get(f"{IXENT_SDK_URL}/arena/turn/{game_player_id}", headers=_headers(), timeout=10)
                    if resp.ok:
                        d = resp.json()
                        if not d.get("your_turn", False) or d.get("status", {}).get("game_over", False):
                            break # El turno ha pasado al siguiente o acabó el juego
                except Exception:
                    pass
            continue # Salta a la siguiente iteración del GAME LOOP
        # -------------------------------------------

        click.echo(f"\n🎯 [TURN {turn}] {model_name} thinking...")

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
                f"{IXENT_SDK_URL}/arena/move",
                headers = _headers(),
                json    = {
                    "game_player_id": game_player_id,
                    "command":        cmd,
                    "reasoning":      reasoning or "",
                    "motor_url":      motor_url,
                    "evaluation_id":  game_id,   # ← garantiza ID largo en Arena
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
            result = move_resp.json()
        except Exception as e:
            click.echo(f"❌ Move error: {e}")
            time.sleep(2)
            continue

        gym = result.get("gym_metrics", {})

        if not result.get("success", True):
            click.echo(f"   🚫 REJECTED: {result.get('msg')}")
            if gym.get("terminated", False):
                click.echo("   🏁 Server declared end of game (TIMEOUT). Stopping.")
                game_over = True
        else:
            click.echo("   👍 ACCEPTED")

        if gym.get("terminated") or gym.get("truncated"):
            game_over = True

    # =========================================================================
    # RESUMEN FINAL
    # =========================================================================
    if 'avg_tps' not in dir():
        avg_tps = 0.0
    click.echo(f"\n🏁 Arena match completed.")
    try:
        final   = requests.get(
            f"{IXENT_SDK_URL}/arena/result/{game_player_id}",
            headers = _headers(),
            timeout = 10,
        ).json()
        st      = final.get("status",  {})
        scoring = final.get("scoring", {})
        result  = st.get("result", "UNKNOWN")

        # Datos en bruto del motor
        raw_scores = scoring.get("scores", {})
        mice       = st.get("mice_rescued", {})
        total      = st.get("total_mice_per_player", 1)  # Evitar división por 0
        p_tokens   = scoring.get("thinking_tokens", {})  # Tokens gastados por jugador

        # Detección estricta de los modos válidos
        is_team_mode = (mode == "2v2")

        if is_team_mode and raw_scores:
            # Equipos estrictos 2v2
            team_a_players = ["P1", "P2"]
            team_b_players = ["P3", "P4"]

            # Fórmula: arena_score * (mice_exit / total_mice)
            def calc_final_score(p):
                score   = raw_scores.get(p, 0)
                rescued = mice.get(p, 0)
                return score * (rescued / total)

            # Cálculos por equipo
            team_a_score  = sum(calc_final_score(p) for p in team_a_players)
            team_a_tokens = sum(p_tokens.get(p, 0)  for p in team_a_players)
            team_b_score  = sum(calc_final_score(p) for p in team_b_players)
            team_b_tokens = sum(p_tokens.get(p, 0)  for p in team_b_players)

            # Lógica de victoria y desempate por thinking tokens
            if team_a_score > team_b_score:
                winning_team = "Team A"
            elif team_b_score > team_a_score:
                winning_team = "Team B"
            else:
                if team_a_tokens < team_b_tokens:
                    winning_team = "Team A"
                elif team_b_tokens < team_a_tokens:
                    winning_team = "Team B"
                else:
                    winning_team = "TIE"

            # Determinar mi equipo
            my_team   = "Team A" if player_slot in team_a_players else "Team B"
            is_winner = (winning_team == my_team) or (winning_team == "TIE" and result == "VICTORY")

            click.echo(f"\n{'🏆' if is_winner else '💀'} GAME OVER: {result}")
            click.echo("   🛡️ Team Scores (2v2):")
            winner_a_icon = "👑 " if winning_team == "Team A" else "   "
            winner_b_icon = "👑 " if winning_team == "Team B" else "   "
            click.echo(f"  {winner_a_icon}Team A (P1+P2): {team_a_score:,.2f} pts | 🧠 {team_a_tokens} tokens")
            click.echo(f"  {winner_b_icon}Team B (P3+P4): {team_b_score:,.2f} pts | 🧠 {team_b_tokens} tokens")
            click.echo("\n   👤 Individual Breakdown:")

        else:
            # Modo Individual (1v1, ffa)
            my_score  = raw_scores.get(player_slot, 0) * (mice.get(player_slot, 0) / total)
            is_winner = my_score == max(
                [s * (mice.get(p, 0) / total) for p, s in raw_scores.items()], default=0
            )
            click.echo(f"\n{'🏆' if is_winner else '💀'} GAME OVER: {result}")
            click.echo("   Scores:")

        # Desglose individual (se imprime siempre)
        for p, s in raw_scores.items():
            rescued      = mice.get(p, 0)
            final_p_score = s * (rescued / total)
            t_spent      = p_tokens.get(p, 0)
            marker       = " ← you" if p == player_slot else ""
            click.echo(f"     {p}: {final_p_score:,.2f} pts (Raw: {s}) | 🐭 {rescued}/{total} | 🧠 {t_spent} tokens{marker}")

        click.echo(f"\n   Your turns:  {turn}")
        click.echo(f"   Time:        {round(s_secs, 1)}s")
        click.echo(f"   Avg TPS:     {avg_tps}")

    except Exception as e:
        click.echo(f"   ⚠️ Error fetching final results: {e}")

    click.echo("\n✅ Session complete.")


# =============================================================================
# COMANDOS PÚBLICOS — llamados desde cli.py
# =============================================================================

def create_room(mode: str, level: int, model: str = None, prompt_file: str = None, strategy_file: str = None, room_code: str = None):
    """
    Crea una sala Arena y arranca el bucle de juego como host (P1).
    """
    click.echo(f"\n🎮 Creating Arena room — Mode: {mode.upper()} | Level: {level}")

    def _headers():
        return {"X-Firebase-Token": _inject_fresh_token(), "Content-Type": "application/json"}

    if not model:
        model = "H_Expert" if mode == "human" else "gemini-2.5-flash"

    if model.lower() != "human":
        validate_env()

    # --- LAZY IMPORTS (Evita ciclos con cli.py) ---
    from ixentbench.play import _load_text_file

    prompt_text   = _load_text_file(prompt_file,   "Prompt Injection", PROMPTS_DIR)    if prompt_file   else None
    strategy_text = _load_text_file(strategy_file, "Strategy",         STRATEGIES_DIR) if strategy_file else None

    payload = {
        "mode": mode, 
        "level": level, 
        "model": model,
        "prompt_injection": prompt_text,
        "strategy": strategy_text
    }
    if room_code:
        payload["room_code"] = room_code

    resp = requests.post(
        f"{IXENT_SDK_URL}/arena/create",
        headers = _headers(),
        json    = payload,
        timeout = 30,
    )

    if not resp.ok:
        click.echo(f"❌ Error creating room: {resp.text}", err=True)
        raise SystemExit(1)

    data           = resp.json()

    # 🛡️ Aviso de moderación — el contenido pudo ser descartado sin bloquear la partida
    if data.get("moderation_notice"):
        click.echo(f"\n⚠️  {data['moderation_notice']}\n")

    room_code      = data.get("room_code")
    mode           = data.get("mode", mode)
    motor_url      = data.get("motor_url",      IXENT_SDK_URL)
    model_name     = data.get("model",          "AI Agent")
    session_info   = data.get("session",        {})
    system_prompt  = data.get("system_prompt",  "")
    game_id        = data.get("game_id",        "")
    game_player_id = data.get("game_player_id", "")
    local_url      = LOCAL_MODEL_URL or None
    agent_script   = None

    click.echo(f"\n✅ Room created!")
    click.echo(f"   Code: {room_code}")
    click.echo(f"\n   Share this code with your opponents:")
    click.echo(f"   ixentbench arena join --room {room_code}\n")
    click.echo("⏳ Waiting for all players to join...")

    # Polling hasta que la sala esté llena y la partida arranque
    while True:
        time.sleep(3)
        status_resp = requests.get(
            f"{IXENT_SDK_URL}/arena/room/{room_code}",
            headers = _headers(),
            timeout = 10,
        )
        if status_resp.ok:
            room_data = status_resp.json()
            if room_data.get("status") == "playing":
                game_id = room_data.get("game_id", game_id)
                click.echo("\n🎉 All players joined! Game starting...")
                break
            players_joined = room_data.get("players_joined", 0)
            players_needed = room_data.get("players_needed", 0)
            click.echo(f"   Players: {players_joined}/{players_needed}")

    _run_arena_loop(
        player_slot    = "P1",
        motor_url      = motor_url,
        mode           = mode,
        model_name     = model_name,
        system_prompt  = system_prompt,
        session_info   = session_info,
        local_url      = local_url,
        agent_script   = agent_script,
        game_id        = game_id,
        game_player_id = game_player_id,
    )


def join_room(room_code: str, model: str = None, prompt_file: str = None, strategy_file: str = None):
    """
    Se une a una sala Arena existente y arranca el bucle de juego.
    """
    click.echo(f"\n🎮 Joining Arena room: {room_code}")

    def _headers():
        return {"X-Firebase-Token": _inject_fresh_token(), "Content-Type": "application/json"}

    # Aquí es un poco más complicado saber si es Human o no sin preguntar a la sala, 
    # pero como default rápido para CLI:
    if not model:
        model = "gemini-2.5-flash" # Asumimos AI por defecto al unirse por CLI a menos que se especifique

    if model.lower() != "human":
        validate_env()

    # --- LAZY IMPORTS (Evita ciclos con cli.py) ---
    from ixentbench.play import _load_text_file

    prompt_text   = _load_text_file(prompt_file,   "Prompt Injection", PROMPTS_DIR)    if prompt_file   else None
    strategy_text = _load_text_file(strategy_file, "Strategy",         STRATEGIES_DIR) if strategy_file else None

    resp = requests.post(
        f"{IXENT_SDK_URL}/arena/join",
        headers = _headers(),
        json    = {
            "room_code": room_code, 
            "model": model,
            "prompt_injection": prompt_text,
            "strategy": strategy_text
        },
        timeout = 30,
    )

    if not resp.ok:
        click.echo(f"❌ Error joining room: {resp.text}", err=True)
        raise SystemExit(1)

    data           = resp.json()

    # 🛡️ Aviso de moderación — el contenido pudo ser descartado sin bloquear la partida
    if data.get("moderation_notice"):
        click.echo(f"\n⚠️  {data['moderation_notice']}\n")

    player_slot    = data.get("player_slot",    "P2")
    motor_url      = data.get("motor_url",      IXENT_SDK_URL)
    mode           = data.get("mode",           "ffa")
    model_name     = data.get("model",          "AI Agent")
    session_info   = data.get("session",        {})
    system_prompt  = data.get("system_prompt",  "")
    game_id        = data.get("game_id",        "")
    game_player_id = data.get("game_player_id", "")
    local_url      = LOCAL_MODEL_URL or None
    agent_script   = None

    click.echo(f"✅ Joined room {room_code} as {player_slot}")
    click.echo("⏳ Waiting for host to start the game...")

    # Polling hasta que la partida arranque
    while True:
        time.sleep(3)
        status_resp = requests.get(
            f"{IXENT_SDK_URL}/arena/room/{room_code}",
            headers = _headers(),
            timeout = 10,
        )
        if status_resp.ok:
            room_data = status_resp.json()
            if room_data.get("status") == "playing":
                game_id = room_data.get("game_id", game_id)
                click.echo("\n🎉 Host started the game!")
                break

    _run_arena_loop(
        player_slot    = player_slot,
        motor_url      = motor_url,
        mode           = mode,
        model_name     = model_name,
        system_prompt  = system_prompt,
        session_info   = session_info,
        local_url      = local_url,
        agent_script   = agent_script,
        game_id        = game_id,
        game_player_id = game_player_id,
    )