# SÃ©ance 13 â€” Pagination : Chargement des donnÃ©es par pages

## Code de cette sÃ©ance
- [`schemas.py`](../../schemas.py) â€” ajout de `PaginatedPostsResponse`
- [`config.py`](../../config.py) â€” ajout de `posts_per_page`
- [`routers/posts.py`](../../routers/posts.py) â€” `get_posts` mis Ã  jour avec `skip`/`limit`
- [`routers/users.py`](../../routers/users.py) â€” `get_user_posts` paginÃ©
- [`main.py`](../../main.py) â€” route `/` mise Ã  jour avec pagination
- [`static/js/utils.js`](../../static/js/utils.js) â€” ajout de `escapeHtml` et `formatDate`
- [`templates/home.html`](../../templates/home.html) â€” bouton "Load More Posts" et JS de pagination
- [`populate_db.py`](../../populate_db.py) â€” script de peuplement de la DB pour les tests
- [`populate_images/`](../../populate_images/) â€” images utilisÃ©es par `populate_db.py`

## Ce qu'on a fait
- AjoutÃ© le schÃ©ma `PaginatedPostsResponse` pour dÃ©finir le contrat entre frontend et backend.
- Mis Ã  jour `get_posts` pour accepter les query parameters `skip` et `limit`, et renvoyer les mÃ©tadonnÃ©es de pagination.
- AjoutÃ© `posts_per_page` dans `config.py` pour avoir une valeur configurable.
- Mis Ã  jour la route `/` dans `main.py` pour ne rendre que la premiÃ¨re page cÃ´tÃ© serveur.
- ImplÃ©mentÃ© le bouton "Load More Posts" dans `home.html` : le premier chargement est rendu cÃ´tÃ© serveur (Jinja2), les pages suivantes sont chargÃ©es dynamiquement via l'API.
- AjoutÃ© `escapeHtml` et `formatDate` dans `utils.js` pour le rendu JS sÃ©curisÃ© des posts chargÃ©s dynamiquement.
- AjoutÃ© la pagination sur `get_user_posts` dans `routers/users.py`.
- CrÃ©Ã© `populate_db.py` pour remplir la DB avec des utilisateurs et posts de test.

## Points techniques Ã  retenir

### Pourquoi paginer ?

Renvoyer tous les posts d'un coup pose problÃ¨me quand la base grandit â€” charge rÃ©seau, charge DB, lenteur d'affichage. La pagination coupe les rÃ©sultats en pages : on charge les 10 premiers, puis les 10 suivants sur demande.

### `PaginatedPostsResponse` : le contrat frontend/backend

```python
# schemas.py
class PaginatedPostsResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    skip: int
    limit: int
    has_more: bool
```

`has_more` est calculÃ© cÃ´tÃ© serveur pour Ã©viter que le frontend n'ait Ã  le dÃ©duire lui-mÃªme :

```python
# routers/posts.py
has_more = skip + len(posts) < total
```

### `skip` et `limit` : les query parameters de pagination

```python
@router.get("", response_model=PaginatedPostsResponse)
async def get_posts(
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = settings.posts_per_page,
):
    count_result = await db.execute(select(func.count()).select_from(models.Post))
    total = count_result.scalar() or 0

    result = await db.execute(
        select(models.Post)
        .options(selectinload(models.Post.author))
        .order_by(models.Post.date_posted.desc())
        .offset(skip)
        .limit(limit),
    )
    posts = result.scalars().all()
    has_more = skip + len(posts) < total

    return PaginatedPostsResponse(
        posts=[PostResponse.model_validate(post) for post in posts],
        total=total, skip=skip, limit=limit, has_more=has_more,
    )
```

- `skip` : nombre de rÃ©sultats Ã  ignorer (l'offset en DB).
- `limit` : nombre de rÃ©sultats Ã  renvoyer.
- `Query(ge=0)` et `Query(ge=1, le=100)` : validation automatique des paramÃ¨tres.

Pour la pagination des posts d'un utilisateur spÃ©cifique, la mÃªme logique s'applique dans `get_user_posts` de `routers/users.py`.

### `posts_per_page` dans `config.py`

```python
# config.py
class Settings(BaseSettings):
    posts_per_page: int = 10
```

La valeur par dÃ©faut (`10`) est centralisÃ©e dans la configuration â€” modifiable via variable d'environnement `POSTS_PER_PAGE` sans toucher au code.

### Approche hybride : SSR + JS "Load More"

La premiÃ¨re page est rendue cÃ´tÃ© serveur (Jinja2) â€” ce qui est rapide et SEO-friendly. Les pages suivantes sont chargÃ©es dynamiquement via l'API au clic sur "Load More".

**Route `/` mise Ã  jour :**
```python
# main.py
async def home(request: Request, db: ...):
    total = count_result.scalar() or 0
    posts = result.scalars().all()  # seulement la premiÃ¨re page
    has_more = len(posts) < total

    return templates.TemplateResponse(request, "home.html", {
        "posts": posts,
        "limit": settings.posts_per_page,
        "has_more": has_more,
    })
```

**`home.html` â€” initialisation des variables JS depuis Jinja2 :**

```javascript
// home.html â€” les {{ }} sont rÃ©solus cÃ´tÃ© serveur avant que le navigateur voie le fichier
let currentOffset = {{ limit }};  // commence aprÃ¨s les posts dÃ©jÃ  rendus
const limit = {{ limit }};
let hasMore = {{ 'true' if has_more else 'false' }};
```

Jinja2 remplace `{{ limit }}` et `{{ 'true' if has_more else 'false' }}` cÃ´tÃ© serveur â€” le navigateur reÃ§oit directement les valeurs numÃ©riques et boolÃ©ennes. L'apparence de rouge dans PyCharm Ã  l'intÃ©rieur des balises `<script>` est un faux positif : PyCharm ne comprend pas Jinja2 dans le JS (mÃªme phÃ©nomÃ¨ne qu'en sÃ©ance 9 avec `{{ post.id }}`).

**Le bouton "Load More" n'est rendu que si `has_more` est `true` :**
```html
{% if has_more %}
  <button type="button" class="btn btn-outline-primary" id="loadMoreBtn">Load More Posts</button>
{% endif %}
```

**JS â€” appel API au clic :**
```javascript
async function loadMorePosts() {
    const response = await fetch(`/api/posts?skip=${currentOffset}&limit=${limit}`);
    const data = await response.json();

    for (const post of data.posts) {
        postsContainer.insertAdjacentHTML('beforeend', createPostHTML(post));
    }

    currentOffset += data.posts.length;
    hasMore = data.has_more;

    if (!hasMore) {
        loadMoreBtn.classList.add('d-none');
    }
}
```

### `escapeHtml` et `formatDate` dans `utils.js`

Lors du rendu cÃ´tÃ© serveur, Jinja2 Ã©chappe automatiquement le HTML. En JS, il faut le faire manuellement pour Ã©viter les failles XSS :

```javascript
// utils.js
export function escapeHtml(text) {
    const div = document.createElement("div");
    div.textContent = text;
    return div.innerHTML;
}

export function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString("en-US", {
        year: "numeric", month: "long", day: "2-digit",
    });
}
```

`createPostHTML` dans `home.html` utilise `escapeHtml` sur tous les champs issus de l'API pour que le rendu dynamique soit aussi sÃ»r que le rendu serveur.

### `populate_db.py` â€” peuplement de la DB pour les tests

CrÃ©Ã© pour avoir suffisamment de donnÃ©es pour tester la pagination (44 posts, 6 utilisateurs). Il utilise `httpx.AsyncClient` avec `ASGITransport` pour appeler l'API directement sans lancer un vrai serveur HTTP :

```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
    response = await client.post("/api/users", json={...})
```

```bash
uv run python populate_db.py
```

Il rÃ©initialise la DB Ã  chaque exÃ©cution (supprime les donnÃ©es existantes et les images de profil).

### Cache navigateur et fichiers JS

Quand on modifie un fichier JS servi comme fichier statique, le navigateur peut conserver l'ancienne version en cache. Si un changement ne se reflÃ¨te pas dans le comportement de la page, faire un **hard refresh** : `Ctrl + Shift + R` (vide le cache et recharge tous les assets).

### Pagination FastAPI intÃ©grÃ©e (pour info)

FastAPI propose un utilitaire `Params` de la librairie `fastapi-pagination` pour standardiser la pagination en production. Pour ce cours, on a implÃ©mentÃ© la logique manuellement pour bien comprendre le mÃ©canisme.

## Remarques / questions Ã  creuser
- Le script `populate_db.py` utilise `ASGITransport` de `httpx` â€” cela permet de tester l'application entiÃ¨re (y compris la validation Pydantic et la logique des routes) sans dÃ©marrer un vrai serveur, ce qui le rend utile autant pour les tests que pour le peuplement.
- `has_more = skip + len(posts) < total` : on compare `skip + len(posts)` (le dernier index traitÃ©) au total. Si des posts sont crÃ©Ã©s ou supprimÃ©s entre deux requÃªtes, `total` peut changer â€” c'est acceptable pour ce cas d'usage.
- La pagination par `skip`/`limit` (aussi appelÃ©e offset pagination) est simple Ã  implÃ©menter, mais peut Ãªtre inefficace sur de trÃ¨s grandes tables (la DB doit scanner les `skip` premiÃ¨res lignes). En production Ã  grande Ã©chelle, la pagination par curseur (keyset pagination) est plus performante.
- Ã€ venir en sÃ©ance 14 : rÃ©initialisation de mot de passe par email, tokens et background tasks.

