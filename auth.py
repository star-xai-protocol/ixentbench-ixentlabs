# -*- coding: utf-8 -*-
"""
ixentbench/auth.py
Google OAuth → Firebase JWT.
Primera ejecución: abre el navegador para Sign in with Google.
Siguientes ejecuciones: refresco silencioso desde credentials.json
"""

import os
import requests
import click
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from ixentbench.config import (
    CREDENTIALS, FIREBASE_API_KEY,
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET
)

SCOPES = ["openid", "https://www.googleapis.com/auth/userinfo.email"]


def get_firebase_token() -> str:
    """
    Devuelve un Firebase ID Token válido (1h).
    Gestiona automáticamente el ciclo de vida de las credenciales.
    """
    creds = None

    if CREDENTIALS.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(CREDENTIALS), SCOPES)
        except Exception:
            creds = None  # Credenciales corruptas — re-autenticar

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None  # Token revocado — re-autenticar

        if not creds:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id":     OAUTH_CLIENT_ID,
                        "client_secret": OAUTH_CLIENT_SECRET,
                        "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
                        "auth_uri":      "https://accounts.google.com/o/oauth2/auth",
                        "token_uri":     "https://oauth2.googleapis.com/token",
                    }
                },
                SCOPES
            )
            creds = flow.run_local_server(port=0, open_browser=True)

        CREDENTIALS.parent.mkdir(parents=True, exist_ok=True)
        CREDENTIALS.write_text(creds.to_json())
        os.chmod(CREDENTIALS, 0o600)

    # Intercambiar Google token → Firebase ID token
    url = (
        f"https://identitytoolkit.googleapis.com/v1/"
        f"accounts:signInWithIdp?key={FIREBASE_API_KEY}"
    )
    resp = requests.post(url, json={
        "postBody":            f"access_token={creds.token}&providerId=google.com",
        "requestUri":          "http://localhost",
        "returnSecureToken":   True,
        "returnIdpCredential": True,
    }, timeout=15)
    resp.raise_for_status()
    return resp.json().get("idToken")


def force_login():
    """Revoca las credenciales en Google, las elimina localmente y fuerza re-autenticación."""
    if CREDENTIALS.exists():
        try:
            old_creds = Credentials.from_authorized_user_file(str(CREDENTIALS), SCOPES)
            token_to_revoke = old_creds.refresh_token or old_creds.token
            if token_to_revoke:
                requests.post(
                    "https://oauth2.googleapis.com/revoke",
                    params={"token": token_to_revoke},
                    headers={"content-type": "application/x-www-form-urlencoded"},
                    timeout=10,
                )
        except Exception:
            click.echo("⚠️  No se pudo revocar el token anterior en Google (se continúa igualmente).", err=True)
        CREDENTIALS.unlink()
        click.echo("🗑️  Credentials cleared and revoked.")
    click.echo("🔐 Opening browser for Google Sign-In...")
    token = get_firebase_token()
    if token:
        click.echo("✅ Login successful. Credentials saved.")
    else:
        click.echo("❌ Login failed.", err=True)