# Séance 01 — Premiers pas avec FastAPI

## Code de la séance
Voir [`main.py`](main.py).

## Ce qu'on a fait
- Création du projet avec `main.py`.
- Mise en place d'une "fausse" base de données : une `list[dict]` nommée `posts`, en attendant de brancher une vraie DB plus tard.
- Première route API : `get_posts` (`GET /api/posts`) qui renvoie la liste `posts` sous forme de JSON.
- Une route `home` (`GET /` et `GET /posts`) qui renvoie un peu de HTML via `HTMLResponse`, pour lire directement dans le navigateur.
- Utilisation de `include_in_schema=False` pour cacher une route de la documentation auto-générée.

## Commandes
- Lancer en mode dev (avec auto-reload, pratique pour coder) :
  ```bash
  uv run fastapi dev main.py
  ```
- Lancer en mode prod :
  ```bash
  uv run fastapi run main.py
  ```

## Documentation auto-générée
FastAPI génère automatiquement une doc interactive, accessible sur :
- `localhost:<port>/docs` (Swagger UI)
- `localhost:<port>/redoc` (ReDoc)

Sur `/docs`, on peut tester une requête directement avec le bouton **"Try it out"** et voir ce qu'elle retourne.

## Points techniques à retenir

### Renvoyer du HTML plutôt que du JSON
```python
from fastapi.responses import HTMLResponse
```
On ajoute `response_class=HTMLResponse` dans le décorateur de la route :
```python
@app.get("/", response_class=HTMLResponse)
def home():
    return f"<h1>{posts[0]['title']}</h1>"
```

### Stacker les décorateurs
On peut empiler plusieurs décorateurs `@app.get(...)` sur la même fonction pour qu'elle réponde à plusieurs routes :
```python
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
@app.get("/posts", response_class=HTMLResponse, include_in_schema=False)
def home():
    ...
```

### Cacher une route de la doc auto-générée
On ajoute `include_in_schema=False` dans le décorateur :
```python
@app.get("/route-cachee", include_in_schema=False)
def ma_route():
    ...
```

## Remarques / questions à creuser
- Pour l'instant les données sont en mémoire (liste de dicts) — la vraie base de données arrive dans une prochaine séance.
- À vérifier dans la séance suivante : la gestion des erreurs (404 si un post n'existe pas), les modèles Pydantic pour valider les données en entrée/sortie.
