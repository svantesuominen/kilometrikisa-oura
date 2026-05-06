"""
One-time local helper to bootstrap Oura OAuth2 tokens.

Run this once on your machine:
    python auth_setup.py

It will:
1. Open your browser to authorize the Oura app
2. Catch the redirect on a local HTTP server
3. Exchange the code for access + refresh tokens
4. Print the tokens for you to store as GitHub Secrets
"""

import http.server
import os
import sys
import threading
import urllib.parse
import webbrowser

import requests

AUTHORIZE_URL = "https://cloud.ouraring.com/oauth/authorize"
TOKEN_URL = "https://api.ouraring.com/oauth/token"
REDIRECT_PORT = 8080
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
SCOPE = "workout"


def get_env_or_prompt(var_name: str, prompt_text: str) -> str:
    value = os.environ.get(var_name, "").strip()
    if not value:
        value = input(prompt_text).strip()
    return value


class CallbackHandler(http.server.BaseHTTPRequestHandler):
    authorization_code: str | None = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            CallbackHandler.authorization_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(
                b"<h1>Authorization successful!</h1>"
                b"<p>You can close this tab and return to the terminal.</p>"
            )
        elif "error" in params:
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            error = params.get("error", ["unknown"])[0]
            self.wfile.write(f"<h1>Authorization failed: {error}</h1>".encode())
        else:
            self.send_response(404)
            self.end_headers()

        threading.Thread(target=self.server.shutdown, daemon=True).start()

    def log_message(self, format, *args):
        pass


def main():
    client_id = get_env_or_prompt("OURA_CLIENT_ID", "Enter Oura Client ID: ")
    client_secret = get_env_or_prompt("OURA_CLIENT_SECRET", "Enter Oura Client Secret: ")

    if not client_id or not client_secret:
        print("Error: Client ID and Client Secret are required.")
        sys.exit(1)

    auth_url = (
        f"{AUTHORIZE_URL}?"
        f"response_type=code&"
        f"client_id={client_id}&"
        f"redirect_uri={urllib.parse.quote(REDIRECT_URI, safe='')}&"
        f"scope={SCOPE}"
    )

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), CallbackHandler)

    print(f"\nOpening browser for Oura authorization...")
    print(f"If it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    print(f"Waiting for callback on port {REDIRECT_PORT}...")
    server.serve_forever()

    code = CallbackHandler.authorization_code
    if not code:
        print("Error: No authorization code received.")
        sys.exit(1)

    print("Exchanging code for tokens...")
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    resp.raise_for_status()
    tokens = resp.json()

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    print("\n" + "=" * 60)
    print("SUCCESS! Store these as GitHub Secrets:\n")
    print(f"  OURA_CLIENT_ID:     {client_id}")
    print(f"  OURA_CLIENT_SECRET: {client_secret}")
    print(f"  OURA_REFRESH_TOKEN: {refresh_token}")
    print()
    print(f"Access token (expires in {tokens.get('expires_in', '?')}s):")
    print(f"  {access_token}")
    print("=" * 60)


if __name__ == "__main__":
    main()
