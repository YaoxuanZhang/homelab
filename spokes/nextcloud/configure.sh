# Use this script to configure nextcloud to use authentik as the default provider

# 1. Enable the automatic redirect
docker exec --user www-data -it nextcloud-aio-nextcloud php occ config:app:set user_oidc auto_redirect --value="1"

# 2. Tell Nextcloud WHICHI provider to redirect to (this name must match your Identifier)
docker exec --user www-data -it nextcloud-aio-nextcloud php occ config:app:set user_oidc default_provider --value="authentik"

# 3. Clean up the login page just in case the redirect is slow
docker exec --user www-data -it nextcloud-aio-nextcloud php occ config:app:set user_oidc hide_login_form --value="1"

# 4. Disable multiple user backends
docker exec --user www-data -it nextcloud-aio-nextcloud php occ config:app:set user_oidc allow_multiple_user_backends --value="0"

# 5. Disable the "Login with username and password" button
docker exec --user www-data -it nextcloud-aio-nextcloud php occ config:app:set user_oidc hide_login_form --value="1"