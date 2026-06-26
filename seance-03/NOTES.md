# Séance 03 — Path Parameters : Validation and Error Handling

## Code de la séance
- [`main.py`](main.py) — route `/api/posts/{post_id}`, route `/posts/{post_id}`, gestionnaires d'exceptions
- [`templates/post.html`](templates/post.html) — page de détail d'un post
- [`templates/error.html`](templates/error.html) — page d'erreur générique
- [`templates/home.html`](templates/home.html) — mis à jour pour rendre les titres cliquables
- `templates/layout.html` n'a pas changé depuis la séance 2, voir [`seance-02/templates/layout.html`](../seance-02/templates/layout.html)

## Ce qu'on a fait
- Découverte des **path parameters** : une variable dans l'URL elle-même (ex: `/api/posts/1`), qui permet de cibler une ressource précise.
- Gestion propre des erreurs avec `HTTPException` + `status` plutôt qu'un simple dict `{"error": ...}` retourné en 200.
- Typage du path parameter (`post_id: int`) : FastAPI valide automatiquement le type et renvoie une erreur 422 si ce n'est pas un entier.
- Création d'une route HTML `/posts/{post_id}` (page de détail d'un post, template `post.html`) en plus de la route API JSON `/api/posts/{post_id}`.
- Liens cliquables vers cette page de détail depuis `home.html`, via `url_for('post_page', post_id=post.id)` plutôt que des `href="#"` en dur.
- Mise en place de **gestionnaires d'exceptions globaux** (`@app.exception_handler(...)`) pour que les erreurs (404, validation...) rendent soit du JSON (routes `/api/...`), soit une page HTML (`error.html`) selon le contexte — alors qu'avant, toute erreur renvoyait du JSON brut même sur les pages HTML.
- Distinction entre deux familles d'erreurs : les erreurs HTTP "métier" (`StarletteHTTPException`, ex: 404) et les erreurs de validation de FastAPI (`RequestValidationError`, ex: 422 quand le type d'un paramètre est invalide) — elles n'ont pas la même forme (`detail` string vs liste d'objets d'erreur).

## Bug rencontré et corrigé (séance précédente, repéré ici)
Dans `/api/posts/{post_id}`, le `return {"error": "Post not found"}` était indenté **dans** la boucle `for`, donc exécuté dès la 1ère itération où l'id ne correspondait pas — empêchant de jamais vérifier les posts suivants. `/api/posts/2` ne retournait donc jamais le 2e post.
```python
# ❌ avant : le return d'erreur est dans le for, exécuté à la 1ère non-correspondance
for post in posts:
    if post.get("id") == post_id:
        return post
    return {"error": "Post not found"}

# ✅ après : le return d'erreur est hors du for, atteint seulement si aucun post n'a matché
for post in posts:
    if post.get("id") == post_id:
        return post
raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
```

## Points techniques à retenir

### Path parameter avec gestion d'erreur propre
```python
from fastapi import FastAPI, Request, HTTPException, status

@app.get("/api/posts/{post_id}")
def get_post(post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            return post
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
```
- Typer `post_id: int` permet à FastAPI de valider automatiquement l'entrée. Une requête comme `/api/posts/hello` renvoie une 422 avec le détail de l'erreur de parsing, sans qu'on ait à coder cette validation nous-même.

### Route HTML pour une ressource précise
```python
@app.get("/posts/{post_id}", include_in_schema=False)
def post_page(request: Request, post_id: int):
    for post in posts:
        if post.get("id") == post_id:
            title = post["title"][:50]
            return templates.TemplateResponse(
                request, "post.html",
                {"post": post, "title": title},
            )
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
```

### Lien cliquable vers une route avec paramètre
```jinja
<a class="article-title" href="{{ url_for('post_page', post_id=post.id) }}">{{ post.title }}</a>
```
`url_for` accepte les paramètres de la route en argument nommé (`post_id=post.id`).

### Gestionnaires d'exceptions globaux
FastAPI est construit sur Starlette — c'est Starlette qui lève l'exception HTTP de base. Il faut donc importer `HTTPException` de Starlette (renommé pour éviter le conflit avec celui de FastAPI) pour l'intercepter globalement :
```python
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler(request: Request, exception: StarletteHTTPException):
    message = exception.detail or "An error occurred. Please check your request and try again."
    if request.url.path.startswith("/api"):
        return JSONResponse(status_code=exception.status_code, content={"detail": message})
    return templates.TemplateResponse(
        request, "error.html",
        {"status_code": exception.status_code, "title": exception.status_code, "message": message},
        status_code=exception.status_code,  # important pour avoir le bon status code
    )
```
Et séparément pour les erreurs de validation (422), qui ont une structure différente (liste d'erreurs plutôt qu'un message) :
```python
@app.exception_handler(RequestValidationError)
def validation_exception_handler(request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
    return templates.TemplateResponse(
        request, "error.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )
```
- Logique commune aux deux handlers : si la route appelée commence par `/api`, on répond en JSON (client API) ; sinon on rend le template `error.html` (utilisateur dans le navigateur).
- Ne pas oublier de repasser `status_code=...` à `TemplateResponse` : sans ça, la réponse HTML serait quand même envoyée avec un code 200, ce qui fausserait le comportement côté client/SEO/monitoring.

## Remarques / questions à creuser
- Pour l'instant les gestionnaires d'erreurs sont définis directement dans `main.py` — à voir si une séance future propose de les déplacer dans un module dédié quand le projet grossira (cf. séance "Routers - Organizing Routes into Modules").
- `post.html` contient déjà des boutons "Edit"/"Delete" avec des `TODO` (auth pas encore implémentée) — normal, ça vient du template de référence, à activer plus tard avec l'authentification (séance JWT).
- À creuser en séance 4 : Pydantic Schemas pour valider proprement les requêtes/réponses (actuellement on travaille encore avec des dicts bruts).
