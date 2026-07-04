# Séance 08 — Routers : Organisation des routes en modules avec APIRouter

## Code de cette séance
- [`main.py`](main.py) — allégé : ne contient plus que les routes frontend et les exception handlers
- [`routers/users.py`](routers/users.py) — toutes les routes API `/api/users`
- [`routers/posts.py`](routers/posts.py) — toutes les routes API `/api/posts`
- [`routers/__init__.py`](routers/__init__.py) — marque le dossier comme package Python

## Ce qu'on a fait
- Extrait toutes les routes API de `main.py` vers deux fichiers dédiés : `routers/users.py` et `routers/posts.py`.
- `main.py` ne contient désormais plus que les routes **frontend** (templates HTML) et les **exception handlers** — beaucoup plus lisible.
- Découverte de `APIRouter` : l'équivalent FastAPI des Blueprints Flask — permet de déclarer des routes dans un module séparé et de les connecter à l'app principale.
- Compris le mécanisme de **préfixe** : le chemin dans chaque router est relatif au préfixe défini dans `app.include_router(...)`, ce qui évite la duplication de `/api/users` dans chaque route.
- Ajout des **tags** pour organiser la documentation Swagger (`/docs`) en sections distinctes par ressource.

## Points techniques à retenir

### `APIRouter` : déclarer des routes hors de `main.py`

```python
# routers/users.py
from fastapi import APIRouter

router = APIRouter()

@router.post("", ...)          # correspond à POST /api/users
@router.get("/{user_id}", ...) # correspond à GET /api/users/{user_id}
```

On remplace `@app.get(...)` par `@router.get(...)`. Le router est ensuite connecté à l'app dans `main.py`.

### Connecter un router dans `main.py`

```python
from routers import posts, users

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])
```

- **`prefix`** : préfixe ajouté devant chaque route du router. Une route déclarée `""` dans le router correspond à `/api/users`, une route `"/{user_id}"` correspond à `/api/users/{user_id}`.
- **`tags`** : regroupe les routes sous un même titre dans la doc Swagger — facilite la navigation quand les routes sont nombreuses.

### Le chemin des routes devient relatif au préfixe

```python
# Avant (dans main.py)
@app.post("/api/users", ...)
@app.get("/api/users/{user_id}", ...)

# Après (dans routers/users.py, avec prefix="/api/users" dans main.py)
@router.post("", ...)
@router.get("/{user_id}", ...)
```

Le préfixe est défini **une seule fois** dans `app.include_router(...)`. Les routes du router n'ont plus à le répéter.

### `__init__.py` : rendre le dossier importable comme package

```python
# routers/__init__.py  (fichier vide)
```

Ce fichier vide indique à Python que `routers/` est un **package**, ce qui permet l'import `from routers import users`. Ce n'est pas obligatoire en Python moderne (namespace packages), mais c'est une bonne pratique pour la clarté.

### Attention aux conflits de noms entre routes

Si deux fonctions dans des routers différents portent le même nom, FastAPI peut les confondre (notamment pour `url_for()`). Il faut nommer les fonctions de façon précise et unique à travers tous les fichiers :

```python
# Bon
async def create_user(...)   # dans users.py
async def create_post(...)   # dans posts.py

# Risque de conflit
async def create(...)        # dans users.py
async def create(...)        # dans posts.py
```

### `main.py` après refactoring

```python
from routers import posts, users

app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(posts.router, prefix="/api/posts", tags=["posts"])

# Seules les routes frontend restent dans main.py
@app.get("/", include_in_schema=False, name="home")
@app.get("/posts", include_in_schema=False, name="posts")
async def home(...): ...

@app.get("/posts/{post_id}", include_in_schema=False)
async def post_page(...): ...

@app.get("/users/{user_id}/posts", include_in_schema=False, name="user_posts")
async def user_posts_page(...): ...
```

## Remarques / questions à creuser
- Cette organisation par ressource (`users.py`, `posts.py`) est le pattern standard en FastAPI. Pour un projet plus grand, on pourrait aussi regrouper par feature (ex: `auth/`, `blog/`) plutôt que par type de ressource.
- Les routes frontend (templates HTML) restent dans `main.py` car elles ont besoin de `templates` — pour un projet plus grand, on pourrait aussi les déplacer dans un router dédié en passant `templates` en dépendance.
- À venir en séance 9 : formulaires frontend et connexion JavaScript → API.
