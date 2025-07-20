# Guide de Démarrage Rapide - Social Media Publisher

Guide pour démarrer rapidement l'infrastructure Docker complète.

## 🚀 Démarrage en 3 étapes

### 1. Configuration des credentials
```bash
# Copier le template
cp .env.example .env

# Éditer avec vos vraies clés API
nano .env
```

### 2. Lancement du système complet
```bash
# Rendre le script exécutable
chmod +x rebuild_social_media_system.sh

# Lancer le rebuild complet
./rebuild_social_media_system.sh
```

### 3. Vérification et tests
```bash
# Vérifier que tous les services sont up
docker compose ps

# Tester l'infrastructure
python test_docker_system.py
```

## 🐳 Services déployés

| Service | Port | Description | URL |
|---------|------|-------------|-----|
| **social-media-api** | 8090 | API FastAPI principale | http://localhost:8090 |
| **social-media-worker-content** | - | Worker génération/formatage | - |
| **social-media-worker-publishing** | - | Worker publication | - |
| **social-media-beat** | - | Scheduler Celery | - |
| **social-media-flower** | 5555 | Monitoring Celery | http://localhost:5555 |
| **social-media-redis** | 6379 | Queue et cache Redis | - |
| **social-media-db** | 5432 | Base PostgreSQL | - |

## 📋 Tests rapides

### Test de santé générale
```bash
curl http://localhost:8090/health
curl http://localhost:5555/api/workers
```

### Test publication simple
```bash
curl -X POST "http://localhost:8090/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "Hello from Docker!",
    "site_web": "stuffgaming.fr",
    "plateformes": ["twitter", "instagram"],
    "hashtags": ["#test"]
  }'
```

### Test publication asynchrone (Celery)
```bash
curl -X POST "http://localhost:8090/publish/async" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "Test async avec Celery!",
    "site_web": "gaming.com",
    "platforms_config": [
      {
        "platform": "instagram",
        "content_type": "carousel",
        "nb_slides": 3,
        "hashtags": ["#async", "#celery"]
      }
    ]
  }'
```

### Suivi des tâches
```bash
# Status des queues
curl http://localhost:8090/queue/status

# Métriques des workflows
curl http://localhost:8090/metrics/workflows

# Tous les workflows
curl http://localhost:8090/workflows
```

## 🔧 Commandes utiles

### Gestion des services
```bash
# Voir tous les conteneurs
docker compose ps

# Redémarrer un service
docker compose restart social-media-api

# Voir les logs
docker compose logs social-media-worker-content

# Logs en temps réel
docker compose logs -f social-media-api
```

### Monitoring des queues
```bash
# Taille des queues
docker compose exec social-media-redis redis-cli llen content_generation
docker compose exec social-media-redis redis-cli llen content_publishing

# Monitor Redis en temps réel
docker compose exec social-media-redis redis-cli monitor
```

### Scaling des workers
```bash
# Ajouter plus de workers
docker compose up -d --scale social-media-worker-content=3
docker compose up -d --scale social-media-worker-publishing=2
```

## 🏢 Configurations multi-sites

### StuffGaming.fr
```bash
curl http://localhost:8090/credentials/stuffgaming.fr/twitter
curl http://localhost:8090/accounts/stuffgaming.fr
```

### Gaming.com
```bash
curl http://localhost:8090/credentials/gaming.com/facebook
curl http://localhost:8090/accounts/gaming.com
```

### Football.com
```bash
curl http://localhost:8090/credentials/football.com/instagram
curl http://localhost:8090/accounts/football.com
```

## 🎯 Endpoints principaux

### Publication
- **POST** `/publish` - Publication simple (rétrocompatible)
- **POST** `/publish/advanced` - Publication avec types spécifiques
- **POST** `/publish/async` - Publication asynchrone distribuée

### Monitoring
- **GET** `/queue/status` - État des queues Celery
- **GET** `/workflows` - Tous les workflows
- **GET** `/workflow/{id}` - Statut d'un workflow
- **GET** `/metrics/workflows` - Métriques globales

### Gestion des comptes
- **GET** `/accounts` - Tous les comptes configurés
- **GET** `/credentials` - Statut des credentials
- **POST** `/test/credentials` - Validation d'un compte

## 🐛 Dépannage rapide

### Service ne démarre pas
```bash
# Vérifier les logs
docker compose logs service-name

# Rebuild si nécessaire
docker compose build --no-cache service-name
docker compose up -d service-name
```

### Redis/PostgreSQL non accessible
```bash
# Test connectivité Redis
docker compose exec social-media-redis redis-cli ping

# Test connectivité PostgreSQL
docker compose exec social-media-db pg_isready -U social_media_user
```

### Workers ne traitent pas les tâches
```bash
# Vérifier les workers actifs
curl http://localhost:5555/api/workers

# Redémarrer les workers
docker compose restart social-media-worker-content social-media-worker-publishing
```

### Reset complet
```bash
# Arrêter et nettoyer
docker compose down -v --rmi all

# Rebuild complet
./rebuild_social_media_system.sh
```

## 📊 Monitoring avec Flower

Accédez à http://localhost:5555 pour :
- Voir les workers actifs
- Monitorer les tâches en temps réel
- Analyser les performances
- Débugger les erreurs

## 🎉 Prêt pour la production !

Une fois tous les tests passés, votre infrastructure est prête pour :
- ✅ Publication multi-sites automatisée
- ✅ Traitement distribué avec Celery
- ✅ Scaling horizontal des workers
- ✅ Monitoring en temps réel
- ✅ Gestion de 9 comptes sociaux

## 📞 Support

En cas de problème :
1. Vérifiez les logs : `docker compose logs`
2. Testez avec : `python test_docker_system.py`
3. Consultez : `DOCKER_DEPLOYMENT.md` pour plus de détails