# Guide de Déploiement Docker - Social Media Publisher

Guide complet pour déployer le système de publication automatisée multi-sites avec Docker.

## 🏗️ Architecture Docker

### Services déployés
- **social-media-api** (Port 8090) - API FastAPI principale
- **social-media-worker-content** - Worker Celery pour génération de contenu
- **social-media-worker-publishing** - Worker Celery pour publication
- **social-media-beat** - Scheduler Celery pour tâches périodiques
- **social-media-flower** (Port 5555) - Monitoring Celery
- **social-media-redis** (Port 6379) - Cache et queue Redis
- **social-media-db** (Port 5432) - Base de données PostgreSQL

## 🚀 Déploiement Rapide

### 1. Préparation
```bash
# Cloner le projet
git clone <your-repo>
cd social-media-publisher

# Configurer les credentials
cp .env.example .env
# Éditer .env avec vos vraies clés API
```

### 2. Lancement avec le script automatique
```bash
# Rendre le script exécutable
chmod +x rebuild_social_media_system.sh

# Lancer le rebuild complet
./rebuild_social_media_system.sh
```

### 3. Vérification
```bash
# Vérifier que tous les services sont up
docker compose ps

# Tester l'API
curl http://localhost:8090/health

# Vérifier les credentials
curl http://localhost:8090/credentials
```

## 🔧 Déploiement Manuel

### 1. Build des images
```bash
docker compose build --no-cache
```

### 2. Démarrage infrastructure
```bash
# Redis et PostgreSQL d'abord
docker compose up -d social-media-redis social-media-db

# Attendre que les services soient prêts
sleep 15
```

### 3. Démarrage workers
```bash
# Workers Celery
docker compose up -d social-media-worker-content social-media-worker-publishing

# Scheduler
docker compose up -d social-media-beat
```

### 4. Démarrage API
```bash
# API principale
docker compose up -d social-media-api

# Monitoring
docker compose up -d social-media-flower
```

## 📊 Monitoring et Logs

### Vérifier l'état des services
```bash
# Status global
docker compose ps

# Logs d'un service
docker compose logs social-media-api

# Logs en temps réel
docker compose logs -f social-media-worker-content

# Logs de tous les workers
docker compose logs -f social-media-worker-content social-media-worker-publishing
```

### Monitoring Celery
```bash
# Interface web Flower
http://localhost:5555

# État des queues Redis
docker compose exec social-media-redis redis-cli llen content_generation
docker compose exec social-media-redis redis-cli llen content_publishing

# Monitor Redis en temps réel
docker compose exec social-media-redis redis-cli monitor
```

## 🧪 Tests de Fonctionnement

### 1. Test de santé des services
```bash
# API principale
curl http://localhost:8090/health

# Monitoring Celery
curl http://localhost:5555

# Status des comptes
curl http://localhost:8090/accounts
```

### 2. Test de publication simple
```bash
curl -X POST "http://localhost:8090/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "Test de publication automatisée!",
    "site_web": "stuffgaming.fr",
    "plateformes": ["twitter", "instagram"],
    "hashtags": ["#test", "#automation"]
  }'
```

### 3. Test carrousel Instagram
```bash
curl -X POST "http://localhost:8090/publish/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "Guide gaming en 3 étapes",
    "site_web": "stuffgaming.fr",
    "platforms_config": [{
      "platform": "instagram",
      "content_type": "carousel",
      "nb_slides": 3,
      "hashtags": ["#gaming", "#guide"]
    }]
  }'
```

## 🔐 Configuration des Credentials

### Variables d'environnement requises
Créer un fichier `.env` avec :

```env
# API Configuration
ANTHROPIC_API_KEY=your_anthropic_key
API_PORT=8090

# Database
POSTGRES_DB=social_media_publisher
POSTGRES_USER=social_media_user
POSTGRES_PASSWORD=your_secure_password

# StuffGaming.fr
STUFFGAMING_FR_TWITTER_API_KEY=your_key
STUFFGAMING_FR_TWITTER_API_SECRET=your_secret
# ... (voir .env.example pour la liste complète)

# Gaming.com
GAMING_COM_TWITTER_API_KEY=your_key
# ...

# Football.com  
FOOTBALL_COM_TWITTER_API_KEY=your_key
# ...
```

### Validation des credentials
```bash
# Vérifier tous les credentials
curl http://localhost:8090/credentials

# Tester un compte spécifique
curl -X POST "http://localhost:8090/test/credentials" \
  -d "site_web=stuffgaming.fr&platform=twitter"
```

## ⚙️ Configuration Avancée

### Scaling des workers
```bash
# Ajouter plus de workers content
docker compose up -d --scale social-media-worker-content=3

# Ajouter plus de workers publishing  
docker compose up -d --scale social-media-worker-publishing=2
```

### Variables d'environnement personnalisées
```env
# Celery Configuration
CELERY_BROKER_URL=redis://social-media-redis:6379/1
CELERY_RESULT_BACKEND=redis://social-media-redis:6379/1

# Worker Configuration
CELERY_WORKER_CONCURRENCY=2
CELERY_WORKER_MAX_TASKS_PER_CHILD=1000

# Task Configuration
MAX_RETRY_ATTEMPTS=3
TASK_TIMEOUT=300
```

## 🐛 Dépannage

### Problèmes courants

#### Service ne démarre pas
```bash
# Vérifier les logs
docker compose logs service-name

# Redémarrer un service
docker compose restart service-name

# Rebuild si nécessaire
docker compose build --no-cache service-name
```

#### Port déjà utilisé
```bash
# Trouver quel processus utilise le port
lsof -i :8090

# Ou avec Docker
docker ps --filter publish=8090
```

#### Redis connection failed
```bash
# Vérifier Redis
docker compose exec social-media-redis redis-cli ping

# Redémarrer Redis
docker compose restart social-media-redis
```

#### Worker ne traite pas les tâches
```bash
# Vérifier les queues
docker compose exec social-media-redis redis-cli llen content_generation

# Logs des workers
docker compose logs social-media-worker-content

# Redémarrer les workers
docker compose restart social-media-worker-content social-media-worker-publishing
```

### Reset complet
```bash
# Arrêter tout
docker compose down

# Supprimer volumes (ATTENTION: perte de données)
docker compose down -v

# Supprimer images
docker compose down --rmi all

# Rebuild complet
./rebuild_social_media_system.sh
```

## 📈 Production

### Recommandations pour la production

#### 1. Sécurité
- Utiliser des secrets Docker pour les credentials
- Configurer un reverse proxy (Nginx/Traefik)
- Activer HTTPS
- Limiter l'accès aux ports internes

#### 2. Performance
- Configurer Redis avec persistance
- Utiliser PostgreSQL avec backups automatiques
- Scaler les workers selon la charge
- Monitor les métriques avec Prometheus/Grafana

#### 3. Monitoring
- Logs centralisés (ELK Stack)
- Alertes sur les erreurs
- Métriques Celery avec Flower
- Health checks automatiques

#### 4. Backup
```bash
# Backup PostgreSQL
docker compose exec social-media-db pg_dump -U social_media_user social_media_publisher > backup.sql

# Backup Redis
docker compose exec social-media-redis redis-cli save
```

## 🔗 URLs Utiles

- **API principale** : http://localhost:8090
- **Documentation API** : http://localhost:8090/docs
- **Monitoring Celery** : http://localhost:5555
- **Gestion comptes** : http://localhost:8090/accounts
- **Status credentials** : http://localhost:8090/credentials
- **Exemples** : http://localhost:8090/examples

## 🎯 Prochaines Étapes

1. **Implémenter agents de publication réels** avec APIs sociales
2. **Ajouter interface web** pour gestion des comptes
3. **Intégrer monitoring** avancé (Prometheus/Grafana)
4. **Configurer CI/CD** pour déploiement automatique
5. **Ajouter tests d'intégration** Docker