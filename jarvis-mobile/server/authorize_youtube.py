"""One-time YouTube OAuth setup.

1. In Google Cloud Console, create a project, enable "YouTube Data API v3",
   and create OAuth credentials of type "Desktop app".
2. Download the JSON as client_secret.json into this folder.
3. Run:  python authorize_youtube.py
   A browser window opens; sign in with the Google account that owns the
   channel. token.json is written next to this script and used by the server.
"""

import os

from google_auth_oauthlib.flow import InstalledAppFlow

from jarvis.youtube import SCOPES, TOKEN_FILE

CLIENT_SECRET_FILE = os.environ.get(
    "YT_CLIENT_SECRET_FILE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "client_secret.json"),
)


def main():
    if not os.path.exists(CLIENT_SECRET_FILE):
        raise SystemExit(
            f"client_secret.json not found at {CLIENT_SECRET_FILE}. "
            "Download it from Google Cloud Console first (see README)."
        )
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        f.write(creds.to_json())
    print(f"Authorized. Token saved to {TOKEN_FILE}")


if __name__ == "__main__":
    main()
