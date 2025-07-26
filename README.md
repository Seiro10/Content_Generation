# 🚀 Social Media Publisher - Système Multi-Agents de Publication Automatisée

> **Système intelligent de publication automatisée sur les réseaux sociaux avec support des drafts et cropping d'images**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestration-purple.svg)](https://python.langchain.com/docs/langgraph)
[![Celery](https://img.shields.io/badge/Celery-Distributed-red.svg)](https://docs.celeryproject.org/)

## 📋 Table des Matières

- [Vue d'ensemble](#-vue-densemble)
- [Fonctionnalités](#-fonctionnalités)
- [Architecture](#-architecture)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [API Reference](#-api-reference)
- [Gestion des Drafts](#-gestion-des-drafts)
- [Exemples d'Usage](#-exemples-dusage)
- [Monitoring](#-monitoring)
- [Troubleshooting](#-troubleshooting)

## 🎯 Vue d'ensemble

Le **Social Media Publisher** est un système multi-agents basé sur **LangGraph** qui automatise la publication de contenu sur plusieurs réseaux sociaux simultanément. Il utilise **Claude LLM** pour générer et adapter le contenu selon les spécificités de chaque plateforme.

### 🏢 Sites supportés
- **StuffGaming.fr** - Gaming & Esport
- **Gaming.com** - Communauté Gaming
- **Football.com** - Actualités Football

### 📱 Plateformes supportées
- **Facebook** - Posts avec support drafts natifs
- **Instagram** - Posts, Stories, Carrousels avec images S3
- **Twitter/X** - Posts avec images S3
- **LinkedIn** - Posts professionnels (à venir)

## ✨ Fonctionnalités

### 🎨 Génération de Contenu
- ✅ **Génération automatique** avec Claude LLM
- ✅ **Adaptation par plateforme** (ton, longueur, hashtags)
- ✅ **Support multi-langue**
- ✅ **Formatage intelligent** selon les contraintes

### 📝 Gestion des Publications
- ✅ **Publication immédiate** (`published=true`)
- ✅ **Création de drafts** (`published=false`) pour vérification
- ✅ **Publication mixte** (certaines plateformes en draft)
- ✅ **Historique des publications**

### 🖼️ Gestion des Images
- ✅ **Support S3** pour le stockage d'images
- ✅ **Cropping intelligent** selon la plateforme
- ✅ **Redimensionnement automatique**
- ✅ **Optimisation qualité/taille**

### ⚡ Performance & Scalabilité
- ✅ **Traitement asynchrone** avec Celery
- ✅ **Workers distribués** pour la parallélisation
- ✅ **Cache Redis** pour les performances
- ✅ **Monitoring en temps réel** avec Flower

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI       │    │   LangGraph     │    │   Celery        │
│   Web API       │◄──►│   Orchestrator  │◄──►│   Workers       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Credentials   │    │   Content       │    │   Publishers    │
│   Manager       │    │   Formatters    │    │   (FB/IG/TW)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Social Media  │    │   Claude LLM    │    │   AWS S3        │
│   APIs          │    │   Service       │    │   Storage       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🚀 Installation

### 1. Prérequis
```bash
# Python 3.11+
python --version

# Docker & Docker Compose
docker --version
docker-compose --version

# Redis (pour Celery)
redis-server --version
```

### 2. Clone et Setup
```bash
# Cloner le repository
git clone https://github.com/your-org/social-media-publisher.git
cd social-media-publisher

# Copier le fichier d'environnement
cp .env.example .env

# Modifier les variables d'environnement
nano .env
```

### 3. Démarrage avec Docker
```bash
# Build et démarrage complet
./rebuild_social_media_system.sh

# Ou démarrage manuel
docker-compose up -d

# Vérifier les services
docker-compose ps
```

### 4. Vérification
```bash
# Health check
curl http://localhost:8090/health

# Interface monitoring
open http://localhost:5555  # Flower (admin:admin)
```

## ⚙️ Configuration

### 🔐 Variables d'Environnement

#### Core Services
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8090
DEBUG=false

# LLM Service (Claude)
ANTHROPIC_API_KEY=your_claude_api_key
CLAUDE_MODEL=claude-3-5-sonnet-20241022

# Celery (Redis)
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/1
```

#### AWS S3 (Images)
```bash
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_DEFAULT_REGION=eu-west-3
S3_BUCKET_NAME=your-bucket-name
```

### 🏢 Credentials par Site Web

#### StuffGaming.fr
```bash
# Twitter
STUFFGAMING_FR_TWITTER_API_KEY=your_api_key
STUFFGAMING_FR_TWITTER_API_SECRET=your_api_secret
STUFFGAMING_FR_TWITTER_ACCESS_TOKEN=your_access_token
STUFFGAMING_FR_TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret
STUFFGAMING_FR_TWITTER_BEARER_TOKEN=your_bearer_token

# Facebook
STUFFGAMING_FR_FACEBOOK_APP_ID=your_app_id
STUFFGAMING_FR_FACEBOOK_APP_SECRET=your_app_secret
STUFFGAMING_FR_FACEBOOK_ACCESS_TOKEN=your_page_access_token
STUFFGAMING_FR_FACEBOOK_PAGE_ID=your_page_id

# Instagram
STUFFGAMING_FR_INSTAGRAM_ACCESS_TOKEN=your_instagram_token
STUFFGAMING_FR_INSTAGRAM_BUSINESS_ACCOUNT_ID=your_business_id
```

#### Gaming.com
```bash
# Même structure avec GAMING_COM_...
GAMING_COM_TWITTER_API_KEY=...
GAMING_COM_FACEBOOK_APP_ID=...
GAMING_COM_INSTAGRAM_ACCESS_TOKEN=...
```

#### Football.com
```bash
# Même structure avec FOOTBALL_COM_...
FOOTBALL_COM_TWITTER_API_KEY=...
FOOTBALL_COM_FACEBOOK_APP_ID=...
FOOTBALL_COM_INSTAGRAM_ACCESS_TOKEN=...
```

### ✅ Validation des Credentials
```bash
# Vérifier tous les credentials
curl http://localhost:8090/credentials

# Vérifier un site spécifique
curl http://localhost:8090/credentials/stuffgaming.fr/twitter

# Tester la connexion
curl -X POST "http://localhost:8090/test/credentials" \
  -F "site_web=stuffgaming.fr" \
  -F "platform=twitter"
```

## 📚 API Reference

### 🌐 Endpoints Principaux

#### Base URLs
- **API Principale** : `http://localhost:8090`
- **Documentation** : `http://localhost:8090/docs`
- **Monitoring** : `http://localhost:5555` (Flower)

---

### 📝 Publication Simple

#### `POST /publish`
Publication basique multi-plateformes (rétrocompatible)

```bash
curl -X POST "http://localhost:8090/publish" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "🎮 Nouveau jeu disponible maintenant !",
    "site_web": "stuffgaming.fr",
    "plateformes": ["twitter", "instagram", "facebook"],
    "hashtags": ["#Gaming", "#NewGame", "#StuffGaming"],
    "mentions": ["@stuffgaming"],
    "lien_source": "https://stuffgaming.fr/nouveau-jeu"
  }'
```

**Réponse :**
```json
{
  "request_id": "uuid-1234-5678",
  "status": "accepted",
  "message": "Demande de publication acceptée, traitement en cours"
}
```

---

### 🚀 Publication Avancée

#### `POST /publish/advanced`
Publication avec types spécifiques et contrôle de visibilité

##### ✅ Publication Immédiate
```bash
curl -X POST "http://localhost:8090/publish/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "🎮 Découvrez notre nouveau jeu révolutionnaire !",
    "site_web": "stuffgaming.fr",
    "platforms_config": [
      {
        "platform": "facebook",
        "content_type": "post",
        "hashtags": ["#Gaming", "#NewGame"],
        "lien_source": "https://stuffgaming.fr/news"
      },
      {
        "platform": "instagram",
        "content_type": "post", 
        "hashtags": ["#Gaming", "#StuffGaming"],
        "image_s3_url": "s3://bucket/image.jpg"
      },
      {
        "platform": "twitter",
        "content_type": "post",
        "hashtags": ["#Gaming"],
        "image_s3_url": "s3://bucket/twitter_image.jpg"
      }
    ]
  }' \
  -F "published=true"
```

##### 📝 Création de Drafts
```bash
curl -X POST "http://localhost:8090/publish/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "Contenu à vérifier avant publication",
    "site_web": "stuffgaming.fr",
    "platforms_config": [
      {
        "platform": "facebook",
        "content_type": "post",
        "hashtags": ["#Gaming", "#Draft"]
      },
      {
        "platform": "instagram",
        "content_type": "post",
        "hashtags": ["#Gaming", "#Preview"]
      },
      {
        "platform": "twitter",
        "content_type": "post",
        "hashtags": ["#Gaming", "#Review"]
      }
    ]
  }' \
  -F "published=false"
```

##### 🔀 Publication Mixte
```bash
curl -X POST "http://localhost:8090/publish/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "Annonce importante pour nos fans !",
    "site_web": "stuffgaming.fr",
    "platforms_config": [
      {
        "platform": "facebook",
        "content_type": "post",
        "published": true,
        "hashtags": ["#Annonce"]
      },
      {
        "platform": "instagram",
        "content_type": "post",
        "published": false,
        "hashtags": ["#Preview"]
      },
      {
        "platform": "twitter",
        "content_type": "post",
        "published": false,
        "hashtags": ["#Draft"]
      }
    ]
  }'
```

---

### 🐦 Twitter Spécialisé

#### `POST /publish/twitter/with-image`
Publication Twitter avec image S3

##### Publication Immédiate
```bash
curl -X POST "http://localhost:8090/publish/twitter/with-image" \
  -F "texte_source=🎮 Nouveau jeu disponible maintenant !" \
  -F "site_web=stuffgaming.fr" \
  -F "image_s3_url=s3://matrix-reloaded-rss-img-bucket/games/new_release.jpg" \
  -F 'hashtags=["#Gaming", "#NewRelease", "#StuffGaming"]' \
  -F "published=true"
```

##### Draft Twitter avec Analyse
```bash
curl -X POST "http://localhost:8090/publish/twitter/with-image" \
  -F "texte_source=🎮 Nouveau jeu disponible maintenant !" \
  -F "site_web=stuffgaming.fr" \
  -F "image_s3_url=s3://matrix-reloaded-rss-img-bucket/games/new_release.jpg" \
  -F 'hashtags=["#Gaming", "#NewRelease"]' \
  -F "published=false"
```

**Réponse Draft Twitter :**
```json
{
  "status": "success",
  "post_id": "twitter_draft_a1b2c3d4",
  "post_url": "internal://drafts/twitter/twitter_draft_a1b2c3d4",
  "platform": "twitter",
  "published": false,
  "content_preview": {
    "tweet_text": "🎮 Nouveau jeu disponible maintenant !",
    "character_count": 45,
    "character_remaining": 235,
    "has_image": true,
    "analysis": {
      "quality_score": {
        "score": 85,
        "quality": "bon",
        "recommendations": ["Ajouter plus de détails"]
      }
    }
  }
}
```

---

### 📸 Instagram Spécialisé

#### `POST /publish/instagram/with-image`
Publication Instagram avec support de tous les types

##### Post Instagram avec Image S3
```bash
curl -X POST "http://localhost:8090/publish/instagram/with-image" \
  -F "texte_source=🎮 Découvrez notre nouveau jeu révolutionnaire !" \
  -F "site_web=stuffgaming.fr" \
  -F "image_s3_url=s3://matrix-reloaded-rss-img-bucket/games/new_collection.jpg" \
  -F "content_type=post" \
  -F 'hashtags=["#Gaming", "#NewGame", "#StuffGaming"]' \
  -F "published=true"
```

##### Story Instagram
```bash
curl -X POST "http://localhost:8090/publish/instagram/with-image" \
  -F "texte_source=Nouveau jeu disponible maintenant !" \
  -F "site_web=stuffgaming.fr" \
  -F "image_s3_url=s3://matrix-reloaded-rss-img-bucket/games/story_banner.jpg" \
  -F "content_type=story" \
  -F 'hashtags=["#Gaming"]' \
  -F "published=true"
```

##### Carrousel Instagram avec Images S3
```bash
curl -X POST "http://localhost:8090/publish/instagram/with-image" \
  -F "texte_source=Top 5 des fonctionnalités du nouveau jeu" \
  -F "site_web=stuffgaming.fr" \
  -F "content_type=carousel" \
  -F "nb_slides=5" \
  -F 'images_urls=["s3://bucket/feat1.jpg", "s3://bucket/feat2.jpg", "s3://bucket/feat3.jpg", "s3://bucket/feat4.jpg", "s3://bucket/feat5.jpg"]' \
  -F 'hashtags=["#Gaming", "#Features"]' \
  -F "published=true"
```

##### Carrousel Instagram en Draft
```bash
curl -X POST "http://localhost:8090/publish/instagram/with-image" \
  -F "texte_source=Guide pour débuter le jeu" \
  -F "site_web=stuffgaming.fr" \
  -F "content_type=carousel" \
  -F "nb_slides=4" \
  -F 'hashtags=["#Gaming", "#Guide"]' \
  -F "published=false"
```

---

### 🖼️ Cropping d'Images

#### `POST /images/unified-crop`
Cropping intelligent d'images selon la plateforme

```bash
curl -X POST "http://localhost:8090/images/unified-crop" \
  -F "s3_url=s3://matrix-reloaded-rss-img-bucket/blizzard_news/banner_Diablo_Immortal_Corrections_.jpg" \
  -F "platform=instagram" \
  -F "content_type=post"
```

**Réponse :**
```json
{
  "task_id": "crop-task-uuid",
  "status": "submitted",
  "message": "Crop intelligent unifié en cours pour instagram post",
  "original_url": "s3://bucket/image.jpg",
  "cropping_method": "unified_intelligent"
}
```

**Types supportés :**
- `platform=instagram` + `content_type=post` → 1080x1080
- `platform=instagram` + `content_type=story` → 1080x1920  
- `platform=twitter` + `content_type=post` → 1200x675
- `platform=facebook` + `content_type=post` → 1200x630

---

### 📊 Statut et Monitoring

#### `GET /status/{request_id}`
Récupérer le statut d'une publication

```bash
curl "http://localhost:8090/status/uuid-1234-5678"
```

**Réponse :**
```json
{
  "request_id": "uuid-1234-5678",
  "status": "completed",
  "platforms_results": [
    {
      "task_id": "uuid-1234-5678_twitter",
      "status": "completed",
      "platform": "twitter",
      "content_type": "post",
      "result": {
        "status": "success",
        "post_id": "1234567890",
        "post_url": "https://twitter.com/i/web/status/1234567890"
      }
    }
  ],
  "created_at": "2025-07-25T14:30:00Z",
  "completed_at": "2025-07-25T14:31:00Z"
}
```

#### `GET /tasks`
Lister toutes les tâches

```bash
curl "http://localhost:8090/tasks"
```

---

## 📝 Gestion des Drafts

### 📋 Lister tous les Drafts

```bash
curl "http://localhost:8090/drafts"
```

**Réponse :**
```json
{
  "instagram": [
    {
      "draft_id": "instagram_draft_post_a1b2c3d4",
      "content": {
        "legende": "🎮 Découvrez notre nouveau jeu révolutionnaire !",
        "hashtags": ["#Gaming", "#NewGame"]
      },
      "site_web": "stuffgaming.fr",
      "account": "StuffGaming Instagram",
      "content_type": "post",
      "created_at": "2025-07-25T14:30:00Z",
      "status": "draft",
      "platform": "instagram"
    }
  ],
  "twitter": [
    {
      "draft_id": "twitter_draft_e5f6g7h8",
      "content": {
        "tweet": "🎮 Nouveau jeu disponible maintenant !",
        "image_s3_url": "s3://bucket/image.jpg"
      },
      "analysis": {
        "character_count": 45,
        "character_remaining": 235,
        "quality_score": {
          "score": 85,
          "quality": "bon"
        }
      },
      "created_at": "2025-07-25T14:31:00Z",
      "status": "draft"
    }
  ],
  "facebook": [],
  "total": 2
}
```

### 👀 Voir un Draft Spécifique

```bash
curl "http://localhost:8090/drafts/twitter_draft_e5f6g7h8"
```

**Réponse Twitter :**
```json
{
  "draft_id": "twitter_draft_e5f6g7h8",
  "content": {
    "tweet": "🎮 Nouveau jeu disponible maintenant !",
    "image_s3_url": "s3://bucket/image.jpg"
  },
  "site_web": "stuffgaming.fr",
  "account": "StuffGaming Twitter",
  "created_at": "2025-07-25T14:31:00Z",
  "analysis": {
    "character_count": 45,
    "character_limit": 280,
    "character_remaining": 235,
    "is_valid_length": true,
    "hashtags": ["#Gaming"],
    "mentions": [],
    "emojis_count": 1,
    "quality_score": {
      "score": 85,
      "quality": "bon",
      "recommendations": [
        "Ajouter plus de détails",
        "Considérer ajouter des mentions pertinentes"
      ]
    }
  },
  "actions": {
    "publish": "POST /publish/draft/twitter_draft_e5f6g7h8",
    "preview": "GET /drafts/twitter_draft_e5f6g7h8/preview",
    "edit": "PUT /drafts/twitter_draft_e5f6g7h8",
    "delete": "DELETE /drafts/twitter_draft_e5f6g7h8"
  },
  "limitations": [
    "Draft simulé - non visible dans l'app Twitter",
    "Pour publication immédiate: utiliser published=true"
  ]
}
```

### ✅ Publier un Draft

```bash
curl -X POST "http://localhost:8090/publish/draft/twitter_draft_e5f6g7h8"
```

**Réponse :**
```json
{
  "draft_id": "twitter_draft_e5f6g7h8",
  "status": "published",
  "platform": "twitter",
  "publication_request_id": "new-uuid-5678",
  "result": {
    "request_id": "new-uuid-5678",
    "status": "accepted",
    "message": "Draft publié avec succès"
  }
}
```

### 🗑️ Supprimer un Draft

```bash
curl -X DELETE "http://localhost:8090/drafts/twitter_draft_e5f6g7h8"
```

**Réponse :**
```json
{
  "draft_id": "twitter_draft_e5f6g7h8",
  "status": "deleted",
  "platform": "twitter",
  "message": "Draft twitter supprimé avec succès"
}
```

---

## 🎯 Exemples d'Usage par Cas

### 🏢 Publication d'Entreprise avec Vérification

#### 1. Créer des drafts pour révision
```bash
curl -X POST "http://localhost:8090/publish/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "🚀 Annonce officielle : Partenariat stratégique avec Microsoft Gaming pour développer les prochaines expériences de jeu révolutionnaires !",
    "site_web": "stuffgaming.fr",
    "platforms_config": [
      {
        "platform": "facebook",
        "content_type": "post",
        "hashtags": ["#Microsoft", "#Partnership", "#Gaming"],
        "lien_source": "https://stuffgaming.fr/microsoft-partnership"
      },
      {
        "platform": "instagram",
        "content_type": "post",
        "hashtags": ["#Microsoft", "#Gaming", "#StuffGaming"],
        "image_s3_url": "s3://bucket/microsoft_partnership_banner.jpg"
      },
      {
        "platform": "twitter",
        "content_type": "post",
        "hashtags": ["#Microsoft", "#Gaming", "#Partnership"]
      }
    ]
  }' \
  -F "published=false"
```

#### 2. Réviser les drafts créés
```bash
# Lister tous les drafts
curl "http://localhost:8090/drafts"

# Examiner le draft Twitter
curl "http://localhost:8090/drafts/twitter_draft_abc123"

# Examiner le draft Instagram  
curl "http://localhost:8090/drafts/instagram_draft_def456"
```

#### 3. Publier après validation
```bash
# Publier le draft Facebook (natif)
curl -X POST "http://localhost:8090/publish/draft/facebook_draft_ghi789"

# Publier le draft Instagram (simulé)
curl -X POST "http://localhost:8090/publish/draft/instagram_draft_def456"

# Publier le draft Twitter (simulé)
curl -X POST "http://localhost:8090/publish/draft/twitter_draft_abc123"
```

### 🎮 Publication Gaming avec Images

#### Publication immédiate multi-plateformes
```bash
curl -X POST "http://localhost:8090/publish/advanced" \
  -H "Content-Type: application/json" \
  -d '{
    "texte_source": "🔥 EXCLUSIVITÉ MONDIALE : Premières images du nouveau Assassins Creed ! Les graphismes sont époustouflants et lhistoire sannonce captivante. Que pensez-vous de ces premières révélations ?",
    "site_web": "stuffgaming.fr", 
    "platforms_config": [
      {
        "platform": "facebook",
        "content_type": "post",
        "hashtags": ["#AssassinsCreed", "#Gaming", "#Exclusivité"],
        "lien_source": "https://stuffgaming.fr/assassins-creed-exclusif"
      },
      {
        "platform": "instagram",
        "content_type": "carousel",
        "nb_slides": 4,
        "hashtags": ["#AssassinsCreed", "#Gaming", "#Screenshots"],
        "images_urls": [
          "s3://bucket/ac_screenshot1.jpg",
          "s3://bucket/ac_screenshot2.jpg", 
          "s3://bucket/ac_screenshot3.jpg",
          "s3://bucket/ac_screenshot4.jpg"
        ]
      },
      {
        "platform": "twitter",
        "content_type": "post",
        "hashtags": ["#AssassinsCreed", "#Gaming", "#Exclusivité"],
        "image_s3_url": "s3://bucket/ac_main_screenshot.jpg"
      }
    ]
  }' \
  -F "published=true"
```

### ⚽ Publication Football avec Stories

#### Story Instagram + Tweet immédiat
```bash
# Story Instagram
curl -X POST "http://localhost:8090/publish/instagram/with-image" \
  -F "texte_source=🔥 TRANSFERT CHOC ! Mbappé au Real Madrid !" \
  -F "site_web=football.com" \
  -F "image_s3_url=s3://bucket/mbappe_real_story.jpg" \
  -F "content_type=story" \
  -F 'hashtags=["#Mbappé", "#RealMadrid", "#TransferNews"]' \
  -F "published=true"

# Tweet immédiat
curl -X POST "http://localhost:8090/publish/twitter/with-image" \
  -F "texte_source=🚨 OFFICIEL : Kylian Mbappé signe au Real Madrid pour 5 ans ! Un transfert historique qui marque le football européen. #Mbappé #RealMadrid #TransferNews" \
  -F "site_web=football.com" \
  -F "image_s3_url=s3://bucket/mbappe_real_announce.jpg" \
  -F 'hashtags=["#Mbappé", "#RealMadrid", "#TransferNews"]' \
  -F "published=true"
```

---

## 🔧 Cropping et Optimisation d'Images

### 📏 Dimensions par Plateforme

| Plateforme | Type | Dimensions | Ratio |
|------------|------|------------|-------|
| Instagram | Post | 1080x1080 | 1:1 |
| Instagram | Story | 1080x1920 | 9:16 |
| Instagram | Carousel | 1080x1080 | 1:1 |
| Twitter | Post | 1200x675 | 16:9 |
| Facebook | Post | 1200x630 | 1.91:1 |

### 🎨 Cropping Intelligent

#### Cropper pour Instagram
```bash
# Post Instagram (carré)
curl -X POST "http://localhost:8090/images/unified-crop" \
  -F "s3_url=s3://bucket/landscape_image.jpg" \
  -F "platform=instagram" \
  -F "content_type=post"

# Story Instagram (vertical)
curl -X POST "http://localhost:8090/images/unified-crop" \
  -F "s3_url=s3://bucket/portrait_image.jpg" \
  -F "platform=instagram" \
  -F "content_type=story"
```

#### Cropper pour Twitter
```bash
curl -X POST "http://localhost:8090/images/unified-crop" \
  -F "s3_url=s3://bucket/wide_banner.jpg" \
  -F "platform=twitter" \
  -F "content_type=post"
```

#### Vérifier le résultat du cropping
```bash
# Utiliser l'ID de tâche retourné
curl "http://localhost:8090/workflow/crop-task-uuid"
```

**Réponse cropping réussi :**
```json
{
  "task_id": "crop-task-uuid",
  "status": "completed",
  "original_s3_url": "s3://bucket/landscape_image.jpg",
  "cropped_s3_url": "s3://bucket/landscape_image_cropped_instagram_post.jpg", 
  "platform": "instagram",
  "content_type": "post",
  "target_dimensions": [1080, 1080],
  "cropping_method": "intelligent_center"
}
```

---

## 📊 Monitoring et Observabilité

### 🌸 Interface Flower (Celery)
```bash
# Accéder à Flower
open http://localhost:5555
# Login: admin / admin

# Endpoints utiles
curl "http://admin:admin@localhost:5555/api/workers"
curl "http://admin:admin@localhost:5555/api/tasks"
```

### 📈 Métriques de Performance

#### Status des Queues
```bash
curl "http://localhost:8090/queue/status"
```

**Réponse :**
```json
{
  "queues": {
    "content_generation": 0,
    "content_formatting": 2,
    "content_publishing": 1,
    "image_generation": 0
  },
  "workers": {
    "active_tasks": {
      "worker1@hostname": [
        {
          "id": "task-uuid",
          "name": "content_formatting.format_for_platform",
          "args": ["content", "stuffgaming.fr", "instagram"],
          "state": "PROGRESS"
        }
      ]
    }
  },
  "status": "connected"
}
```

#### Métriques Workflows
```bash
curl "http://localhost:8090/metrics/workflows"
```

**Réponse :**
```json
{
  "total_workflows": 156,
  "status_distribution": {
    "completed": 142,
    "processing": 3,
    "failed": 8,
    "pending": 3
  },
  "site_distribution": {
    "stuffgaming.fr": 89,
    "gaming.com": 35,
    "football.com": 32
  },
  "platform_distribution": {
    "instagram": 78,
    "twitter": 45,
    "facebook": 33
  }
}
```

### 🏥 Health Checks

#### API Health
```bash
curl "http://localhost:8090/health"
```

#### Celery Health
```bash
curl "http://localhost:8090/health/celery"
```

#### Credentials Health
```bash
curl "http://localhost:8090/credentials"
```

---

## 🔍 Troubleshooting

### 🚨 Problèmes Courants

#### 1. Erreur Credentials
```bash
# Symptôme
{"detail":"Erreur: Credentials manquants pour stuffgaming.fr/twitter"}

# Solution
# Vérifier les variables d'environnement
echo $STUFFGAMING_FR_TWITTER_API_KEY

# Recharger les variables
source .env
docker-compose restart social-media-api
```

#### 2. Erreur Claude LLM
```bash
# Symptôme  
{"error": "LLM service not available"}

# Solution
# Vérifier la clé API
echo $ANTHROPIC_API_KEY

# Tester la connexion
curl -X POST "http://localhost:8090/test/format/advanced" \
  -d "texte_source=Test" \
  -d "site_web=stuffgaming.fr" \
  -d "platform=twitter"
```

#### 3. Erreur Upload S3
```bash
# Symptôme
{"error": "AWS credentials manquantes"}

# Solution  
# Vérifier AWS credentials
echo $AWS_ACCESS_KEY_ID
echo $AWS_SECRET_ACCESS_KEY

# Tester S3
aws s3 ls s3://your-bucket-name --region eu-west-3
```

#### 4. Worker Celery Inactif
```bash
# Symptôme
curl "http://localhost:8090/queue/status"
# {"workers": {"active_tasks": {}}}

# Solution
docker-compose logs social-media-worker-content
docker-compose restart social-media-worker-content social-media-worker-publishing
```

### 📋 Commandes de Debug

#### Logs en Temps Réel
```bash
# Logs API principale
docker-compose logs -f social-media-api

# Logs workers
docker-compose logs -f social-media-worker-content social-media-worker-publishing

# Logs Redis
docker-compose logs -f social-media-redis

# Tous les logs
docker-compose logs -f
```

#### Reset Complet
```bash
# Arrêter tous les services
docker-compose down

# Nettoyer les volumes
docker-compose down -v

# Rebuild complet
./rebuild_social_media_system.sh
```

#### Test des Composants

##### Test LLM
```bash
curl -X POST "http://localhost:8090/test/format/advanced" \
  -F "texte_source=Test de génération de contenu" \
  -F "site_web=stuffgaming.fr" \
  -F "platform=twitter" \
  -F "content_type=post"
```

##### Test Credentials
```bash
curl -X POST "http://localhost:8090/test/credentials" \
  -F "site_web=stuffgaming.fr" \
  -F "platform=twitter"
```

##### Test Redis
```bash
docker-compose exec social-media-redis redis-cli ping
docker-compose exec social-media-redis redis-cli llen content_generation
```

---

## 🚀 Production et Scaling

### 🏭 Configuration Production

#### Variables d'Environnement
```bash
# Production
ENVIRONMENT=production
DEBUG=false
API_HOST=0.0.0.0
API_PORT=8090

# Scaling Celery
CELERY_WORKERS_CONTENT=4
CELERY_WORKERS_PUBLISHING=2
CELERY_MAX_TASKS_PER_CHILD=1000
```

#### Scaling Workers
```bash
# Augmenter les workers
docker-compose up -d --scale social-media-worker-content=4
docker-compose up -d --scale social-media-worker-publishing=2

# Monitoring
curl "http://admin:admin@localhost:5555/api/workers"
```

### 🔒 Sécurité

#### Variables Sensibles
```bash
# Utiliser des secrets managers
export ANTHROPIC_API_KEY=$(aws ssm get-parameter --name "/social-publisher/anthropic-key" --with-decryption --query Parameter.Value --output text)

# Rotation automatique des tokens
# Implémenter un système de renouvellement des tokens Facebook/Instagram
```

#### Rate Limiting
- Facebook: 200 appels/heure/page
- Instagram: 200 appels/heure/compte  
- Twitter: 300 tweets/3h/compte

---

## 📚 Ressources Additionnelles

### 🔗 Documentation APIs
- [Facebook Graph API](https://developers.facebook.com/docs/graph-api/)
- [Instagram Graph API](https://developers.facebook.com/docs/instagram-api/)
- [Twitter API v2](https://developer.twitter.com/en/docs/twitter-api)
- [Claude API](https://docs.anthropic.com/claude/reference/getting-started-with-the-api)

### 🛠️ Outils de Développement
- [FastAPI Docs](https://fastapi.tiangolo.com/)
- [LangGraph](https://python.langchain.com/docs/langgraph)
- [Celery](https://docs.celeryproject.org/en/stable/)
- [Pydantic](https://docs.pydantic.dev/)

### 📖 Guides
- [Configuration Multi-Sites](./app/config/README.md)
- [Architecture LangGraph](./docs/architecture.md)
- [Gestion des Images S3](./docs/s3-images.md)

---

## 🤝 Support

### 🐛 Rapporter un Bug
1. Vérifier les [issues existantes](https://github.com/your-org/social-media-publisher/issues)
2. Créer une nouvelle issue avec :
   - Description du problème
   - Étapes pour reproduire
   - Logs pertinents
   - Configuration (sans credentials)

### 💡 Demande de Fonctionnalité
Ouvrir une [feature request](https://github.com/your-org/social-media-publisher/issues/new?template=feature_request.md)

### 📧 Contact
- **Email** : support@yourcompany.com
- **Slack** : #social-media-publisher
- **Documentation** : [Wiki interne](https://wiki.yourcompany.com/social-media-publisher)

---

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 🎉 Changelog

### v1.2.0 (2025-07-25)
- ✅ Ajout du paramètre `published` pour contrôle des drafts
- ✅ Support drafts natifs Facebook  
- ✅ Drafts simulés Instagram/Twitter avec analyse
- ✅ Cropping intelligent d'images S3
- ✅ Endpoints de gestion des drafts
- ✅ Amélioration du monitoring

### v1.1.0 (2025-07-20)
- ✅ Support des images S3
- ✅ Carrousels Instagram
- ✅ Stories Instagram
- ✅ Optimisation Celery

### v1.0.0 (2025-07-15)
- ✅ Publication multi-plateformes
- ✅ Integration LangGraph + Claude
- ✅ Workers Celery distribués
- ✅ Architecture microservices

---

*Made with ❤️ by Seiro10