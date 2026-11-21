# Déploiement

Guide de déploiement en production avec Docker Compose : Nginx, Gunicorn, PostgreSQL, Redis, Celery et S3.

## Architecture

```text
Internet
   │
   ▼
Nginx :80  ──►  /static/  (fichiers collectés)
   │            /media/   (stockage local, si S3 désactivé)
   ▼
Gunicorn (web, :8000) ──► PostgreSQL (db)
   │
   ├──► Redis (redis) ◄── Worker Celery
   │
   └──► Amazon S3 (images de profil, si configuré)
```

Services Docker Compose :

- `nginx` : reverse proxy, sert `/static/` et `/media/`, expose le port 80.
- `web` : applique les migrations, collecte les statiques, puis lance Gunicorn.
- `worker` : worker Celery (emails en arrière-plan).
- `db` : PostgreSQL 16.
- `redis` : Redis 7 (broker Celery).

## Prérequis

- Docker et Docker Compose.
- Un nom de domaine (optionnel, pour HTTPS).
- Un bucket S3 (optionnel, recommandé en production pour les médias).
- Un compte SMTP (optionnel si les emails sont désactivés).

## Configuration

Copiez `.env.example` vers `.env` :

```bash
cp .env.example .env
```

Docker Compose utilise `.env` pour les variables `${...}` et le transmet aux conteneurs.

### Variables indispensables

```dotenv
DEBUG=false
SECRET_KEY=une-cle-secrete-longue-et-aleatoire
ALLOWED_HOSTS=app.example.com,www.app.example.com
CSRF_TRUSTED_ORIGINS=https://app.example.com,https://www.app.example.com

POSTGRES_DB=app
POSTGRES_USER=app
POSTGRES_PASSWORD=un-mot-de-passe-solide
```

> Si `POSTGRES_DB` n'est pas défini, les valeurs par défaut `app/app/app` sont utilisées par Compose. Changez impérativement le mot de passe en production.

### Email (SMTP)

```dotenv
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=votre-adresse@gmail.com
EMAIL_HOST_PASSWORD=votre-mot-de-passe-application
EMAIL_USE_TLS=true
DEFAULT_FROM_EMAIL=votre-adresse@gmail.com
```

Le port 465 (`EMAIL_USE_SSL`) est souvent bloqué sur certains réseaux : préférez 587 + STARTTLS.

### Celery

Compose force déjà :

```dotenv
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CELERY_TASK_ALWAYS_EAGER=false
```

### Stockage S3

Laissez les clés vides pour utiliser le stockage local (`media/`).

Pour activer S3 :

```dotenv
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_STORAGE_BUCKET_NAME=mon-bucket-media
AWS_S3_REGION_NAME=eu-west-3
```

Dès que `AWS_STORAGE_BUCKET_NAME` est défini, les images de profil sont envoyées sur S3. Les fichiers sont privés et servis via des URLs signées. L'upload passe par le backend Django (les clés AWS ne sont jamais exposées au navigateur).

## Déploiement

```bash
docker compose up -d --build
```

Au démarrage, le service `web` exécute :

```bash
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

Accès : `http://<ip-ou-domaine>/`

Créez un administrateur :

```bash
docker compose exec web python manage.py createsuperuser
```

## HTTPS avec Nginx

Le reverse proxy écoute en HTTP sur le port 80. Pour HTTPS, ajoutez un certificat (par exemple avec Certbot) et configurez le bloc `server` dans `nginx/default.conf` :

```nginx
server {
    listen 443 ssl;
    server_name app.example.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    # ... mêmes locations que le bloc HTTP
}
```

Pensez à :

- rediriger le port 80 vers 443 ;
- exposer le port 443 dans `compose.yml` ;
- monter les certificats dans le conteneur `nginx` ;
- garder `X-Forwarded-Proto` (déjà transmis par la configuration fournie) ;
- définir `CSRF_TRUSTED_ORIGINS` avec le domaine HTTPS.

## Maintenance

### Logs

```bash
docker compose logs -f
docker compose logs -f web
docker compose logs -f worker
```

### Redéploiement

```bash
git pull
docker compose up -d --build
```

### Scaling

```bash
docker compose up -d --scale worker=2
```

Pour plusieurs instances `web`, retirez la publication de port et placez un load balancer devant Nginx, ou adaptez la configuration.

### Sauvegardes PostgreSQL

```bash
docker compose exec db pg_dump -U app app > backup.sql
```

Restauration :

```bash
cat backup.sql | docker compose exec -T db psql -U app app
```

Les données PostgreSQL sont stockées dans le volume `pgdata`. Redis utilise le volume `redis_data`.

## Checklist sécurité

- [ ] `DEBUG=false`
- [ ] `SECRET_KEY` unique et long
- [ ] `ALLOWED_HOSTS` limité au(x) domaine(s)
- [ ] `CSRF_TRUSTED_ORIGINS` renseigné en HTTPS
- [ ] Mot de passe PostgreSQL changé
- [ ] Bucket S3 privé (pas d'accès public)
- [ ] Certificat HTTPS actif
- [ ] Sauvegardes PostgreSQL planifiées
- [ ] Accès SSH/Docker restreint

## Dépannage

- **502 Bad Gateway** : vérifiez `docker compose logs web` (Gunicorn démarre après les migrations).
- **Statiques manquants** : vérifiez que `collectstatic` s'est exécuté et que le volume `staticfiles` est monté dans `nginx`.
- **Emails non envoyés** : consultez les logs `worker` et vérifiez les identifiants SMTP.
- **Images non affichées** : vérifiez `AWS_STORAGE_BUCKET_NAME`, la région, les droits IAM (PutObject/GetObject) et les URLs signées.
