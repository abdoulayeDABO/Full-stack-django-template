# Développement

Guide pour lancer et développer le projet en local.

## Prérequis

- Python 3.12+
- Redis (optionnel si vous utilisez l'exécution synchrone des tâches)
- Docker et Docker Compose (optionnel)

## Installation locale

```bash
git clone https://github.com/abdoulayeDABO/Full-stack-django-template.git
cd Full-stack-django-template

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
```

Copiez la configuration d'exemple :

```bash
cp .env.example .env
```

Renseignez au minimum les variables email si vous voulez tester l'envoi réel.

## Base de données

Par défaut, le projet utilise SQLite (`db.sqlite3`) : aucune configuration n'est nécessaire.

Pour utiliser PostgreSQL, renseignez dans `.env` :

```dotenv
POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=app
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
```

Dès que `POSTGRES_DB` est défini, Django bascule sur PostgreSQL. Sinon il reste sur SQLite.

Appliquez les migrations :

```bash
python manage.py migrate
```

Créez un superutilisateur si besoin :

```bash
python manage.py createsuperuser
```

## Emails et Celery

Les emails (réinitialisation du mot de passe) passent par la tâche Celery `accounts.tasks.send_email`.

En développement, `CELERY_TASK_ALWAYS_EAGER` vaut `true` par défaut quand `DEBUG=true` : les tâches s'exécutent immédiatement, sans worker ni Redis.

Pour tester le vrai mode asynchrone :

1. Lancez Redis :

   ```bash
   redis-server
   ```

2. Dans `.env` :

   ```dotenv
   CELERY_BROKER_URL=redis://localhost:6379/0
   CELERY_RESULT_BACKEND=redis://localhost:6379/0
   CELERY_TASK_ALWAYS_EAGER=false
   ```

3. Lancez le worker :

   ```bash
   celery -A config worker -l info
   ```

Pour éviter d'envoyer de vrais emails en développement, utilisez la console :

```dotenv
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

## Lancer le serveur

```bash
python manage.py runserver
```

- Accueil : http://localhost:8000/
- Admin : http://localhost:8000/admin/
- Connexion : http://localhost:8000/accounts/login/

## Tests

```bash
python manage.py test
```

Les tests utilisent une base SQLite isolée et un backend email local (`locmem`).

## Docker Compose

La stack complète est décrite dans `compose.yml` :

- `web` : migrations, `collectstatic`, Gunicorn
- `worker` : Celery
- `db` : PostgreSQL 16
- `redis` : Redis 7
- `nginx` : reverse proxy sur le port 80

```bash
docker compose up --build
```

Accès : http://localhost

Commandes utiles :

```bash
docker compose logs -f web
docker compose exec web python manage.py createsuperuser
docker compose exec web python manage.py migrate
docker compose down
docker compose down -v   # supprime aussi les volumes (données)
```

## Commandes utiles

```bash
python manage.py makemigrations
python manage.py migrate
python manage.py collectstatic
python manage.py shell
python manage.py test accounts
```

## Dépannage

- **Port 465 bloqué** : utilisez le port 587 avec `EMAIL_USE_TLS=true` (STARTTLS).
- **Emails non envoyés** : vérifiez `EMAIL_*` dans `.env`, puis les logs du worker Celery.
- **Statiques manquants** : lancez `python manage.py collectstatic` (ou via le conteneur `web`).
- **Images de profil** : sans `AWS_STORAGE_BUCKET_NAME`, elles sont stockées dans `media/avatars/` et servies en `DEBUG`.
