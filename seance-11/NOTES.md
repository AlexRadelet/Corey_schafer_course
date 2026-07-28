# Séance 11 — Authorization : Protection des routes et utilisateur courant

## Code de cette séance
- [`auth.py`](auth.py) — `get_current_user` déplacé ici comme dépendance partagée, alias `CurrenUser`
- [`schemas.py`](schemas.py) — `PostCreate` simplifié : suppression de `user_id` (vient du token)
- [`routers/posts.py`](routers/posts.py) — routes protégées, vérification de propriété (403)
- [`routers/users.py`](routers/users.py) — `/me` simplifié via `CurrenUser`, `update_user` et `delete_user` protégés
- [`main.py`](main.py) — ajout de la route `/account`
- [`templates/account.html`](templates/account.html) — page de compte utilisateur
- [`templates/layout.html`](templates/layout.html) — navbar conditionnelle selon l'état de connexion, bouton New Post conditionnel
- [`templates/post.html`](templates/post.html) — boutons Edit/Delete affichés uniquement au propriétaire du post

## Ce qu'on a fait
- Déplacé `get_current_user` de `routers/users.py` vers `auth.py` pour en faire une **dépendance réutilisable** dans tous les routers.
- Créé l'alias de type `CurrenUser` pour simplifier les signatures de fonctions.
- Supprimé `user_id` de `PostCreate` — l'ID de l'auteur vient désormais du token JWT (l'utilisateur connecté), plus du corps de la requête.
- Ajouté la vérification de **propriété** sur les routes d'édition et de suppression : seul l'auteur d'un post peut le modifier/supprimer (erreur 403 sinon).
- Fait pareil pour les routes utilisateur : seul l'utilisateur lui-même peut modifier ou supprimer son compte.
- Mis à jour le frontend : boutons Edit/Delete affichés uniquement au propriétaire, bouton "New Post" conditionnel selon connexion.

## Points techniques à retenir

### `get_current_user` comme dépendance partagée dans `auth.py`

En séance 10, `get_current_user` était un endpoint (`GET /api/users/me`) dans `routers/users.py`. Il est maintenant **séparé** : c'est une fonction de dépendance dans `auth.py`, utilisable par n'importe quel router.

```python
# auth.py
async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> models.User:
    user_id = verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token",
                            headers={"WWW-Authenticate": "Bearer"})
    # ... charge et retourne l'utilisateur depuis la DB

CurrenUser = Annotated[models.User, Depends(get_current_user)]
```

L'alias `CurrenUser` permet d'écrire `current_user: CurrenUser` dans les signatures plutôt que de répéter `Annotated[models.User, Depends(get_current_user)]` à chaque fois.

### `PostCreate` sans `user_id`

```python
# Avant (séance 10)
class PostCreate(PostBase):
    user_id: int  # le client envoyait son propre ID — non sécurisé

# Après (séance 11)
class PostCreate(PostBase):
    pass  # user_id vient du token, pas du corps de la requête
```

Le client ne peut plus se faire passer pour quelqu'un d'autre — l'ID de l'auteur est extrait du JWT signé par le serveur.

### Protection des routes : 401 vs 403

```python
# 401 Unauthorized : non authentifié (pas de token ou token invalide)
raise HTTPException(status_code=401, detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"})

# 403 Forbidden : authentifié, mais pas autorisé à agir sur cette ressource
if post.user_id != current_user.id:
    raise HTTPException(status_code=403, detail="Not authorized to update this post")
```

- **401** : tu n'es pas connecté (ou ton token est expiré).
- **403** : tu es connecté, mais ce n'est pas ta ressource.

### `create_post` : plus de vérification d'existence du user

```python
# Avant (séance 10) : on vérifiait que le user_id envoyé existait bien en DB
result = await db.execute(select(models.User).where(models.User.id == post.user_id))
user = result.scalars().first()
if not user:
    raise HTTPException(404, "User not found")

# Après (séance 11) : le user vient du token, donc il existe forcément
async def create_post(post: PostCreate, current_user: CurrenUser, db: ...):
    new_post = models.Post(title=post.title, content=post.content, user_id=current_user.id)
```

Si le token est valide, l'utilisateur existe en base — `get_current_user` l'a déjà vérifié.

### Endpoint `/me` simplifié dans `routers/users.py`

```python
# Avant : logique complète de vérification du token dans l'endpoint
@router.get("/me", response_model=UserPrivate)
async def get_current_user(token: ..., db: ...):
    user_id = verify_access_token(token)
    # ... vérification manuelle

# Après : toute la logique est dans la dépendance auth.py
@router.get("/me", response_model=UserPrivate)
async def get_me(current_user: CurrenUser):
    return current_user  # une seule ligne
```

### Frontend : affichage conditionnel selon le propriétaire

Dans `post.html`, les boutons Edit/Delete ne sont affichés qu'après vérification côté JS que l'utilisateur connecté est bien l'auteur du post :

```javascript
const user = await getCurrentUser();
if (user && user.id === postAuthorId) {
    document.getElementById("postActions").classList.remove("d-none");
}
```

La vérification côté backend (403) reste indispensable — le JS côté client n'est pas une vraie protection (n'importe qui peut l'outrepasser avec les DevTools).

## Remarques / questions à creuser
- `CurrenUser` (avec une seule `r`) était un typo dans le code — corrigé en `CurrentUser` en séance 12.
- La protection des routes utilisateur (`PATCH /api/users/{user_id}`, `DELETE /api/users/{user_id}`) est maintenant en place, mais il n'y a pas de rôle "admin" — un utilisateur ne peut modifier que son propre compte. Un système de rôles (admin/user) pourrait être ajouté plus tard.
- À venir en séance 12 : upload de fichiers (photos de profil).
