# BD_BE - LIMTIC Flask Backend

Backend Flask pour le projet académique du laboratoire LIMTIC, basé sur le cahier des charges fourni.

## Fonctionnalités couvertes

- Authentification JWT: inscription, connexion, refresh token, reset mot de passe.
- Gestion des rôles: `super_admin`, `admin`, `researcher`, `visitor`.
- Gestion des membres: chercheurs, doctorants, mastériens, import/export CSV.
- Gestion des publications: CRUD, filtres, pagination, export CSV/BibTeX, upload PDF.
- Gestion des axes de recherche: CRUD + association membres.
- Gestion des événements: CRUD, statut automatique, upload galerie photos + programme PDF.
- Page contact: soumission de messages + gestion back-office.
- Dashboard admin: statistiques globales, alertes, dernières actions.
- Journal d'audit des actions critiques.

## Stack

- Flask
- Flask-SQLAlchemy
- Flask-Migrate
- Flask-JWT-Extended
- Flask-Bcrypt

## Démarrage rapide

1. Lancer le script de préparation:

```bash
chmod +x setup_env.sh
./setup_env.sh
```

2. Activer l'environnement:

```bash
source .venv/bin/activate
```

3. Lancer l'API:

```bash
flask --app run.py run --debug
```

4. Vérifier:

```bash
curl http://127.0.0.1:5000/api/health
```

## Variables d'environnement

Copier `.env.example` vers `.env` puis ajuster:

- `DATABASE_URL` (par défaut SQLite)
- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `SMTP_*` (pour reset password en production)
- `UPLOAD_DIR`

## Structure projet

```text
app/
	blueprints/
		auth.py
		public.py
		members.py
		publications.py
		events.py
		axes.py
		contact.py
		admin.py
	utils/
	models.py
	config.py
	extensions.py
run.py
requirements.txt
setup_env.sh
```

## Endpoints principaux

- `GET /api/health`
- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `POST /api/auth/forgot-password`
- `POST /api/auth/reset-password`
- `GET /api/public/home`
- `GET /api/public/researchers`
- `GET /api/public/researchers/<id>`
- `GET /api/public/axes`
- `GET/POST/PATCH/DELETE /api/publications`
- `GET /api/publications/export/csv`
- `GET /api/publications/export/bibtex`
- `GET/POST/PATCH/DELETE /api/events`
- `POST /api/events/<id>/photos`
- `GET/POST/PATCH/DELETE /api/axes`
- `POST /api/contact`
- `GET/PATCH /api/contact`
- `GET /api/admin/dashboard`
- `GET/PATCH /api/admin/users`
- `GET/PUT /api/admin/settings`
- `GET /api/admin/audit-logs`

## Notes importantes

- Ce backend est prêt pour le développement local et la poursuite du projet.
- Pour la production: activer HTTPS, durcir CORS, configurer SMTP réel, et ajouter des tests automatisés.
