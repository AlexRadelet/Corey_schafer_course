# Séance 04 — Pydantic Schemas : Request and Response Validation

## Code de la séance
- [`main.py`](main.py) — routes `GET/POST /api/posts` et `GET /api/posts/{post_id}` avec `response_model`
- [`schemas.py`](schemas.py) — schémas Pydantic `PostBase`, `PostCreate`, `PostResponse`

## Ce qu'on a fait
- Découverte de **Pydantic**, la librairie de validation de données utilisée par FastAPI sous le capot. Elle est déjà incluse dans un projet FastAPI de base.
- Avant cette séance, la doc auto-générée ne décrivait pas la forme des réponses (juste "successful response", sans détail des champs). Avec un `response_model`, FastAPI documente précisément ce que chaque route renvoie.
- Création de `schemas.py` avec 3 modèles :
  - `PostBase` : les champs communs et leurs règles de validation (longueur min/max).
  - `PostCreate(PostBase)` : ce que le client doit envoyer pour créer un post (pas d'`id`, pas de `date_posted` — c'est le serveur qui les attribue).
  - `PostResponse(PostBase)` : ce que l'API renvoie au client, avec en plus `id` et `date_posted`.
- Utilisation de `response_model=...` sur les routes pour ne renvoyer **que** les champs désirés (limite les erreurs : pas de champ en trop, pas de champ vide qui passerait inaperçu).
- Ajout d'une route `POST /api/posts` pour créer un nouveau post, en typant le corps de la requête avec `PostCreate` — FastAPI valide automatiquement les données reçues.
- Utilisation de `status_code=status.HTTP_201_CREATED` sur la route de création : bonne pratique pour signaler la création d'une ressource plutôt qu'un simple 200.

## Points techniques à retenir

### Définir des schémas avec des règles de validation
```python
from pydantic import BaseModel, ConfigDict, Field

class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)
    author: str = Field(min_length=1, max_length=50)

class PostCreate(PostBase):
    pass

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)
    # champs supplémentaires non fournis par le client, attribués par le serveur
    id: int
    date_posted: str
```
- `Field(min_length=..., max_length=...)` ajoute des contraintes de validation ET enrichit la documentation auto-générée.
- Séparer `PostCreate` (entrée) de `PostResponse` (sortie) évite que le client puisse fournir/lire des champs qu'il ne devrait pas (ex: imposer un `id`).
- `model_config = ConfigDict(from_attributes=True)` permet de construire le modèle à partir d'un objet avec attributs (utile plus tard avec un ORM comme SQLAlchemy), pas seulement depuis un dict.

### Documenter et restreindre une réponse
```python
@app.get("/api/posts", response_model=list[PostResponse])
def get_posts():
    return posts
```

### Créer une ressource (validation automatique du body)
```python
@app.post(
    "/api/posts",
    response_model=PostResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_post(post: PostCreate):
    # id temporaire car pas de DB
    new_id = max(p["id"] for p in posts) + 1 if posts else 1
    new_post = {
        "id": new_id,
        "author": post.author,
        "title": post.title,
        "content": post.content,
        "date_posted": "April 23, 2025",
    }
    posts.append(new_post)
    return new_post
```
- FastAPI déduit automatiquement que `post: PostCreate` doit être lu dans le corps (body) de la requête, et valide les données avant même d'entrer dans la fonction.
- `status_code=status.HTTP_201_CREATED` (201) est la convention REST pour signaler qu'une ressource a été créée, plutôt que le 200 par défaut.

## Limite identifiée (à résoudre en séance 5)
La route `POST /api/posts` fonctionne, mais les posts créés ne sont stockés qu'en mémoire (`list[dict]`) : ils disparaissent dès que le serveur redémarre. Il faut une vraie base de données pour persister les données — sujet de la prochaine séance (SQLAlchemy).

## Remarques / questions à creuser
- Pour aller plus loin sur Pydantic en général (au-delà de l'usage FastAPI), il existe un tuto dédié : [Python Pydantic Tutorial: Complete Data Validation Course](https://www.youtube.com/watch?v=M81pfi64eeM).
- À voir en séance 5 : remplacer la liste `posts` par des modèles SQLAlchemy + une vraie base, et faire le lien entre schémas Pydantic (validation API) et modèles SQLAlchemy (persistance).
