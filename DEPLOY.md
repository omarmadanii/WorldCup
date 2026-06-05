# Deploy — World Cup 2026 Predictions

Host: **PythonAnywhere free tier**. Cheapest, no server admin, HTTPS included,
SQLite on persistent disk. Good enough for 8 friends over ~1 month.

Public link will be `https://<username>.pythonanywhere.com` — your PythonAnywhere
username *is* the subdomain, so pick it deliberately at signup
(e.g. `bestoworldcup`).

## Steps

1. **Sign up** at pythonanywhere.com → "Create a Beginner account" (free).

2. **Get the code on PA.** In a *Bash console* (Consoles tab):
   - If pushed to GitHub: `git clone <repo-url> worldcup`
   - Otherwise: zip the project locally → upload via *Files* tab → unzip.
   - Either way, also upload `members.md` into `~/worldcup/` (it's gitignored, so
     `git clone` won't bring it).

3. **Virtualenv + deps** (Bash console):
   ```
   cd ~/worldcup
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Create the web app:** *Web* tab → "Add a new web app" → **Manual
   configuration** → Python 3.10+. Then set:
   - Source code: `/home/<username>/worldcup`
   - Virtualenv:  `/home/<username>/worldcup/venv`

5. **Edit the WSGI file** (linked from the Web tab). Replace contents with:
   ```python
   import os, sys

   path = '/home/<username>/worldcup'
   if path not in sys.path:
       sys.path.insert(0, path)

   # MUST be set before importing app (config.py reads env at import time)
   os.environ['SECRET_KEY']     = '<long-random-string>'
   os.environ['ADMIN_USERNAME'] = 'admin'
   os.environ['ADMIN_PASSWORD'] = '<strong-admin-password>'

   from app import app as application
   ```
   Generate the secret locally:
   `python -c "import secrets; print(secrets.token_hex(32))"`

6. **Seed the 8 player accounts** (Bash console). Export the *same* admin vars
   first so the admin row isn't created with the default `admin`/`admin`:
   ```
   cd ~/worldcup && source venv/bin/activate
   export ADMIN_USERNAME=admin
   export ADMIN_PASSWORD=<same-strong-admin-password-as-WSGI>
   python seed_users.py
   ```
   Expect `created: AbuB … created: AbuMuna` (8 players). Safe to re-run; it skips
   accounts that already exist.

7. **Reload** the web app (green button, Web tab) → visit the link over HTTPS.

## After it's live

Send each friend their row from `members.md` + the link. Arabic WhatsApp message:
```
الرابط: https://<username>.pythonanywhere.com
اسم المستخدم: AbuB
كلمة المرور: Besto1
```

## Smoke test

- Login page loads over HTTPS.
- A player logs in (e.g. `AbuB` / `Besto1`) → dashboard renders.
- `admin` + your password → `/admin/players` lists all 8 friends.
- `admin` / `admin` **fails** (no stray default account).
- Submit a prediction, reload → it persists.

## Teardown (after the tournament)

Download `database.db` from the Files tab if you want to keep results, then delete
the web app (or just let the free account lapse). $0 spent.
