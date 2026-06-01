"""
seed_users.py — run once on the server to create player accounts.

Usage:
    python seed_users.py

Reads members.md (format: "username : password", one per line).
Skips lines starting with # or blank lines.
Safe to re-run: skips usernames that already exist.
"""
import models

MEMBERS_FILE = 'members.md'

def main():
    models.init_db()
    with open(MEMBERS_FILE, encoding='utf-8') as f:
        lines = f.readlines()

    created = 0
    skipped = 0
    for line in lines:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            print(f'  skipping malformed line: {line!r}')
            continue
        username, password = [p.strip() for p in line.split(':', 1)]
        if not username or not password:
            continue
        if models.get_user_by_username(username):
            print(f'  exists — skipping: {username}')
            skipped += 1
        else:
            models.create_user(username, password)
            print(f'  created: {username}')
            created += 1

    print(f'\nDone. Created: {created}  Skipped (already exist): {skipped}')

if __name__ == '__main__':
    main()
