# -*- coding: utf-8 -*-
"""
ixentbench/engines.py
Motores de ejecución para los agentes IA (BYOK, Local, Custom Script).
Agnóstico al modo de juego (Solo o Arena) — importable desde play.py y arena.py.
"""

import json
import time
import subprocess
import sys
import click
import requests

from ixentbench.config import (
    GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY,
    GROK_API_KEY, DEEPSEEK_API_KEY,
)

# =============================================================================
# HELPER: Limpieza de bloques markdown en la respuesta del LLM
# =============================================================================

def strip_markdown(raw: str) -> str:
    """Elimina las etiquetas ```json y ``` que algunos LLMs añaden alrededor del JSON."""
    if raw.startswith("```"):
        lines = raw.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        raw = "\n".join(lines)
    return raw.strip()


# =============================================================================
# HELPER: Construcción del mensaje de usuario (común a todos los motores)
# =============================================================================

def build_user_message(state: dict) -> str:
    """
    Construye el mensaje de usuario con el estado actual del juego.
    Solo envía los campos relevantes para el agente — omite token_metrics
    y otros datos de infraestructura que no aportan contexto estratégico.
    """
    context = {
        "meta":           state.get("meta", {}),
        "inventory":      state.get("data", {}).get("inventory", {}),
        "mice":           state.get("data", {}).get("mice", {}),
        "board_encoding": state.get("data", {}).get("board_encoding", {}),
        "history_full":   state.get("data", {}).get("history", []),
    }
    return (
        f"--- CURRENT SITUATION (TURN {state.get('meta', {}).get('turn', '?')}) ---\n"
        f"{json.dumps(context, ensure_ascii=False)}\n"
        f"TASK: Generate JSON response with your best move."
    )


# =============================================================================
# MOTOR A: BYOK — API Key local del usuario
# Soporta Google (Gemini), Anthropic (Claude), OpenAI (GPT), Grok, DeepSeek
# =============================================================================

def get_move_byok(
    model_name: str,
    system_prompt: str,
    state: dict,
    session: dict,
) -> tuple[str | None, str | None, dict | None]:
    """
    Obtiene un movimiento usando la API Key del usuario (BYOK).

    Args:
        model_name:    nombre del modelo (ej: "gemini-2.5-pro")
        system_prompt: system prompt completo para el agente
        state:         estado actual del juego (JSON del servidor)
        session:       metadatos de sesión (incluye "provider")

    Returns:
        (command, reasoning, token_data) — cualquiera puede ser None si hay error.
    """
    user_msg  = build_user_message(state)
    provider  = session.get("provider", "google")
    t0        = time.time()

    try:
        if provider == "google":
            from google import genai
            from google.genai import types
            client   = genai.Client(api_key=GOOGLE_API_KEY)
            response = client.models.generate_content(
                model    = model_name,
                contents = [system_prompt + "\n\n" + user_msg],
                config   = types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            raw     = response.text.strip()
            usage   = response.usage_metadata
            in_t    = getattr(usage, "prompt_token_count",     0) or 0
            out_t   = getattr(usage, "candidates_token_count", 0) or 0
            tot_t   = getattr(usage, "total_token_count",      0) or 0
            think_t = max(0, tot_t - in_t - out_t)

        elif provider == "anthropic":
            import anthropic
            client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
            msg    = client.messages.create(
                model      = model_name,
                max_tokens = 4096,
                system     = system_prompt,
                messages   = [{"role": "user", "content": user_msg}],
            )
            raw     = msg.content[0].text.strip()
            in_t    = msg.usage.input_tokens
            out_t   = msg.usage.output_tokens
            tot_t   = in_t + out_t
            think_t = 0

        elif provider in ("openai", "grok", "deepseek"):
            from openai import OpenAI
            if provider == "openai":
                client = OpenAI(api_key=OPENAI_API_KEY)
            elif provider == "grok":
                client = OpenAI(api_key=GROK_API_KEY,     base_url="https://api.x.ai/v1")
            else:
                client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")

            resp    = client.chat.completions.create(
                model    = model_name,
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                response_format={"type": "json_object"},
            )
            raw     = resp.choices[0].message.content.strip()
            in_t    = resp.usage.prompt_tokens
            out_t   = resp.usage.completion_tokens
            tot_t   = resp.usage.total_tokens
            details = getattr(resp.usage, "completion_tokens_details", None)
            think_t = getattr(details, "reasoning_tokens", 0) if details else 0

        else:
            click.echo(
                f"❌ Unknown provider: '{provider}'. "
                f"Valid options: google, anthropic, openai, grok, deepseek",
                err=True,
            )
            raise SystemExit(1)

    except Exception as e:
        click.echo(f"\n🛑 CRITICAL AI ERROR: {type(e).__name__}: {e}", err=True)
        raise SystemExit(1)

    inference_sec = round(time.time() - t0, 2)
    gen_t = out_t + think_t
    tps   = round(gen_t / inference_sec, 2) if inference_sec > 0 else 0
    click.echo(f"   ⏱️  {inference_sec}s | {tps} TPS")

    token_data = {
        "input_tokens":      in_t,
        "output_tokens":     out_t,
        "thinking_tokens":   think_t,
        "total":             tot_t,
        "turn_inference_sec": inference_sec,
        "turn_tps":          tps,
        "is_local_hardware": False,
    }

    raw = strip_markdown(raw)
    try:
        decision = json.loads(raw, strict=False)
        return decision.get("command"), decision.get("reasoning"), token_data
    except json.JSONDecodeError as e:
        click.echo(f"⚠️  JSON parse error: {e}")
        # 💰 La llamada a la API ya se completó y generó coste real antes de que
        # fallara el parseo — devolvemos token_data en vez de None para que ese
        # gasto no desaparezca del contador de sesión.
        return None, "Invalid Format", token_data


# =============================================================================
# MOTOR B: MODELO LOCAL — Ollama, LM Studio, llama.cpp, etc.
# Compatible con cualquier servidor que implemente la API OpenAI
# No requiere API Key. is_local_hardware=True excluye TPS del leaderboard.
# =============================================================================

def get_move_local(
    model_name: str,
    system_prompt: str,
    state: dict,
    local_url: str,
) -> tuple[str | None, str | None, dict | None]:
    """
    Obtiene un movimiento desde un modelo local (Ollama, LM Studio, llama.cpp).

    Args:
        model_name:    nombre del modelo local (ej: "llama3.2")
        system_prompt: system prompt completo para el agente
        state:         estado actual del juego
        local_url:     URL base del servidor local (ej: "http://localhost:11434/v1")

    Returns:
        (command, reasoning, token_data) — cualquiera puede ser None si hay error.
    """
    user_msg = build_user_message(state)
    t0       = time.time()

    try:
        resp = requests.post(
            f"{local_url}/chat/completions",
            json={
                "model":    model_name,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_msg},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=610,
        )
        resp.raise_for_status()
        data    = resp.json()
        raw     = data["choices"][0]["message"]["content"].strip()
        in_t    = data.get("usage", {}).get("prompt_tokens",     0)
        out_t   = data.get("usage", {}).get("completion_tokens", 0)
        tot_t   = data.get("usage", {}).get("total_tokens",      0)
        think_t = 0

    except Exception as e:
        click.echo(f"⚠️  Local model error: {e}")
        return None, "Local model error", None

    inference_sec = round(time.time() - t0, 2)
    gen_t = out_t + think_t
    tps   = round(gen_t / inference_sec, 2) if inference_sec > 0 else 0
    click.echo(f"   ⏱️  {inference_sec}s | {tps} TPS (local — excluded from leaderboard)")

    token_data = {
        "input_tokens":      in_t,
        "output_tokens":     out_t,
        "thinking_tokens":   think_t,
        "total":             tot_t,
        "turn_inference_sec": inference_sec,
        "turn_tps":          tps,
        "is_local_hardware": True,
    }

    raw = strip_markdown(raw)
    try:
        decision = json.loads(raw, strict=False)
        return decision.get("command"), decision.get("reasoning"), token_data
    except json.JSONDecodeError as e:
        click.echo(f"⚠️  JSON parse error: {e}")
        # 💰 Mismo caso que en get_move_byok — el coste ya se generó.
        return None, "Invalid Format", token_data


# =============================================================================
# MOTOR C: AGENTE CUSTOM — Script Python del usuario
# Recibe el estado por stdin (JSON) y devuelve la jugada por stdout (JSON).
# No requiere API Key ni conexión a internet.
# =============================================================================

def get_move_agent(
    agent_script: str,
    state: dict,
) -> tuple[str | None, str | None, dict | None]:
    """
    Obtiene un movimiento ejecutando un script Python personalizado.

    El script recibe el estado completo via stdin (JSON) y debe devolver
    via stdout un JSON con la forma:
        {"command": "G4@P21(b=0)+90", "reasoning": "..."}

    Args:
        agent_script: ruta al script Python del agente
        state:        estado actual del juego

    Returns:
        (command, reasoning, token_data) — cualquiera puede ser None si hay error.
    """
    state_json = json.dumps(state, ensure_ascii=False)
    t0         = time.time()

    try:
        result = subprocess.run(
            [sys.executable, agent_script],
            input          = state_json,
            capture_output = True,
            text           = True,
            timeout        = 120,
        )
        if result.returncode != 0:
            click.echo(f"⚠️  Agent script error:\n{result.stderr[:300]}")
            return None, "Agent error", None

        raw           = result.stdout.strip()
        inference_sec = round(time.time() - t0, 2)
        click.echo(f"   ⏱️  Agent: {inference_sec}s (local script)")

        token_data = {
            "input_tokens":      0,
            "output_tokens":     0,
            "thinking_tokens":   0,
            "total":             0,
            "turn_inference_sec": inference_sec,
            "turn_tps":          0,
            "is_local_hardware": True,
        }

        decision = json.loads(raw, strict=False)
        return decision.get("command"), decision.get("reasoning"), token_data

    except subprocess.TimeoutExpired:
        click.echo("⚠️  Agent script timed out (120s)")
        return None, "Timeout", None
    except json.JSONDecodeError as e:
        click.echo(f"⚠️  Agent JSON parse error: {e}")
        # token_data ya se construyó antes de este json.loads() fallido —
        # accesible en scope de función, igual que en los otros dos motores.
        return None, "Invalid Format", token_data