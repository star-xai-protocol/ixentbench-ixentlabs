# -*- coding: utf-8 -*-
"""
ixentbench/config.py
Configuración global: Constantes, carga forzada del .env y utilidades de estado.
"""

import os
import pathlib
import click
from dotenv import load_dotenv

# ── DIRECTORIOS LOCALES (Ruta fija en el Home del usuario) ──────────────────
# Forzamos que siempre apunte a ~/ixentbench para evitar problemas de rutas relativas
IXENT_HOME     = pathlib.Path.home() / "ixentbench"
PROMPTS_DIR    = IXENT_HOME / "prompts"
STRATEGIES_DIR = IXENT_HOME / "strategies"
CREDENTIALS    = IXENT_HOME / "credentials.json"
ENV_PATH       = IXENT_HOME / ".env"

# Aseguramos que las carpetas existan
for _d in [PROMPTS_DIR, STRATEGIES_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

# ── CARGA DEL ARCHIVO .ENV (EL "GPS" DE LAS API KEYS) ───────────────────────
# load_dotenv() a secas busca en la carpeta actual. 
# load_dotenv(ENV_PATH) busca específicamente en ~/ixentbench/.env
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    # Intento fallback por si el usuario está en modo desarrollo local
    load_dotenv()

# ── VARIABLES DE ENTORNO (API KEYS Y URLS) ──────────────────────────────────
GOOGLE_API_KEY    = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY")
GROK_API_KEY      = os.getenv("GROK_API_KEY")
DEEPSEEK_API_KEY  = os.getenv("DEEPSEEK_API_KEY")
LOCAL_MODEL_URL   = os.getenv("LOCAL_MODEL_URL")

# URLs del ecosistema iXentLabs
IXENT_SDK_URL = "https://ixentbench-arena-sdk-874064710861.us-central1.run.app"
VISUALIZER_URL = "https://project-8b3bc726-e144-49eb-a7e.web.app"

# ── CREDENCIALES DE PROYECTO (PUBLICAS) ─────────────────────────────────────
# Estas claves identifican la App en Google Cloud/Firebase, no son secretos de usuario.
FIREBASE_API_KEY    = "AIzaSyDXEL47mO93BA8W1TTXHHdWOIK4tFUnamo"
OAUTH_CLIENT_ID     = "874064710861-dds7gf6e1qinl8c4lurs47od9cc5b0ll.apps.googleusercontent.com"
OAUTH_CLIENT_SECRET = "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" # Public Client Secret (RFC 8252)

# ── UTILIDADES PARA EL USUARIO (MENSAJES EN INGLÉS) ─────────────────────────

def validate_env():
    """
    Verifica que al menos una vía de ejecución (Cloud o Local) esté configurada.
    """
    # Incluimos las 5 llaves para que el "portero" las reconozca todas
    has_cloud = any([
        GOOGLE_API_KEY, ANTHROPIC_API_KEY, OPENAI_API_KEY,
        GROK_API_KEY, DEEPSEEK_API_KEY
    ])
    
    if not has_cloud and not LOCAL_MODEL_URL:
        click.echo("\n❌ No API Key found in .env file.", err=True)
        click.echo("   Add at least one of: GOOGLE, ANTHROPIC, OPENAI, GROK or DEEPSEEK", err=True)
        click.echo("   Or set LOCAL_MODEL_URL for a local model.", err=True)
        click.echo(f"   Check your .env file at: {ENV_PATH}", err=True)
        raise SystemExit(1)

def show_status():
    """
    Imprime en consola el estado actual de las configuraciones.
    """
    click.echo("\n📊 iXentBench Status")
    click.echo("─" * 40)
    
    # Verificación de claves con iconos visuales
    g_set = "✅ Set" if GOOGLE_API_KEY else "— Not set"
    a_set = "✅ Set" if ANTHROPIC_API_KEY else "— Not set"
    o_set = "✅ Set" if OPENAI_API_KEY else "— Not set"
    grok_set = "✅ Set" if GROK_API_KEY else "— Not set"
    deep_set = "✅ Set" if DEEPSEEK_API_KEY else "— Not set"
    
    click.echo(f"  iXentLabs Auth:    ✅ Integrated")
    click.echo(f"  Google API Key:    {g_set}")
    click.echo(f"  Anthropic API Key: {a_set}")
    click.echo(f"  OpenAI API Key:    {o_set}")
    click.echo(f"  Grok API Key:      {grok_set}")
    click.echo(f"  DeepSeek API Key:  {deep_set}")
    click.echo(f"  Local Model URL:   {LOCAL_MODEL_URL or '— Not set'}")
    
    # Estado de la sesión de Google (Firebase)
    if CREDENTIALS.exists():
        click.echo("  Credentials:       ✅ Saved")
    else:
        click.echo("  Credentials:       ⚠️  Run: ixentbench login")
        
    click.echo(f"  SDK URL:           {IXENT_SDK_URL}")
    
    # Conteo de archivos de usuario
    p_count = len(list(PROMPTS_DIR.glob('*.txt')))
    s_count = len(list(STRATEGIES_DIR.glob('*.txt')))
    click.echo(f"  Prompts saved:     {p_count}")
    click.echo(f"  Strategies saved:  {s_count}")
    click.echo("─" * 40)
    click.echo(f"  Config path:       {ENV_PATH}\n")

def list_prompts():
    """Lista los archivos.txt en la carpeta de prompts del usuario."""
    files = list(PROMPTS_DIR.glob('*.txt'))
    if not files:
        click.echo(f"📁 No prompt injections found in {PROMPTS_DIR}")
        return
    click.echo(f"📁 Saved Prompt Injections ({PROMPTS_DIR}):")
    for f in files:
        size = f.stat().st_size
        size_str = f"{round(size/1024, 1)} KB" if size >= 1024 else f"{size} B"
        click.echo(f"  - {f.name} ({size_str})")

def list_strategies():
    """Lista los archivos .txt en la carpeta de strategies del usuario."""
    files = list(STRATEGIES_DIR.glob('*.txt'))
    if not files:
        click.echo(f"📁 No strategy files found in {STRATEGIES_DIR}")
        return
    click.echo(f"📁 Saved Strategies ({STRATEGIES_DIR}):")
    for f in files:
        size = f.stat().st_size
        size_str = f"{round(size/1024, 1)} KB" if size >= 1024 else f"{size} B"
        click.echo(f"  - {f.name} ({size_str})")