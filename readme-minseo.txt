Minseo — brief change log (for teammates)

ADDED (new files)
- templates/login.html — login page UI (Jinja; company greens / customer wording).
- static/css/login.css — styles for that page.
- requirements.txt — flask dependency.
- run.bat — runs pip + app.py using the real Python path (helps if Store “python” alias is broken).
- .gitignore — __pycache__, venv, .env patterns.

CHANGED
- app.py — real Flask app: GET / and /login, stub POST /login (no auth yet). Later: TEMP /dev/skip-login (dev only), GET /staff serves books.html after dev session.
- readme.txt — how to run + note about temporary skip-login.
- books.html — only copy: “Patron Management” → “Customer Management” (file was already in repo before).

NOT mine / not changed by me in these commits
- register.html — existed earlier (demo / admin front-end commits).
- Project Front End/ — untouched by these commits.
- books.html layout and behavior otherwise — existed before; I did not build the staff dashboard from scratch.

If something looks wrong: say which URL or file; login vs /staff vs static HTML opened as a file behave differently.
