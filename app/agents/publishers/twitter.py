async def publish_content(
        self,
        formatted_content: TwitterPostOutput,
        site_web: SiteWeb,
        account: AccountConfig,
        published: bool = True  # 🆕 Nouveau paramètre
) -> dict:
    """Publie le contenu formaté sur Twitter avec support drafts"""

    logger.info(f"🐦 Twitter pour compte: {account.account_name}")
    logger.info(f"📝 Mode: {'Publication' if published else 'Draft simulé'}")

    try:
        # 🆕 VÉRIFICATION DU PARAMÈTRE PUBLISHED EN PREMIER
        if not published:
            logger.info(f"📝 Création draft Twitter pour {account.account_name}")
            return self._create_draft_simulation(formatted_content, site_web, account)

        # Publication normale seulement si published=True
        logger.info(f"📤 Publication Twitter pour {account.account_name}")

        # Récupérer les credentials Twitter
        creds = get_platform_credentials(site_web, PlatformType.TWITTER)

        # Préparer le tweet
        tweet_text = formatted_content.tweet

        # Fonction synchrone pour Twitter (requests-oauthlib n'est pas async)
        def post_tweet_with_media():
            # Créer session OAuth 1.0a
            twitter = OAuth1Session(
                creds.api_key,
                client_secret=creds.api_secret,
                resource_owner_key=creds.access_token,
                resource_owner_secret=creds.access_token_secret,
            )

            media_id = None

            # Gérer l'image S3 si présente
            if formatted_content.image_s3_url:
                media_id = self._upload_image_to_twitter(
                    twitter,
                    formatted_content.image_s3_url
                )

            # Payload pour l'API v2
            payload = {"text": tweet_text}
            if media_id:
                payload["media"] = {"media_ids": [media_id]}

            # Poster le tweet
            response = twitter.post(
                "https://api.twitter.com/2/tweets",
                json=payload,
                headers={"Content-Type": "application/json"}
            )

            return response

        # Exécuter de manière asynchrone
        response = await asyncio.get_event_loop().run_in_executor(None, post_tweet_with_media)

        if response.status_code == 201:
            data = response.json()
            tweet_id = data["data"]["id"]

            logger.info(f"✅ Tweet publié avec succès ! ID: {tweet_id}")
            logger.info(f"📝 Contenu: {tweet_text}")

            if formatted_content.image_s3_url:
                logger.info(f"🖼️ Image: {formatted_content.image_s3_url}")

            return self._create_success_result(
                tweet_id,
                f"https://twitter.com/i/web/status/{tweet_id}",
                {
                    "tweet_text": tweet_text,
                    "image_uploaded": bool(formatted_content.image_s3_url),
                    "published": True,
                    "character_count": len(tweet_text)
                }
            )
        else:
            error_msg = f"Twitter API error: {response.status_code} - {response.text}"
            logger.error(f"❌ {error_msg}")
            return self._create_error_result(error_msg)

    except Exception as e:
        error_msg = f"Erreur lors de la publication Twitter: {str(e)}"
        logger.error(f"❌ {error_msg}")
        return self._create_error_result(error_msg)