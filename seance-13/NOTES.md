# Séance 13 — Pagination : Chargement des données par pages

## Code de cette séance
- [`schemas.py`](../../schemas.py) — ajout de `PaginatedPostsResponse`
- [`config.py`](../../config.py) — ajout de `posts_per_page`
- [`routers/posts.py`](../../routers/posts.py) — `get_posts` mis à jour avec `skip`/`limit`
- [`routers/users.py`](../../routers/users.py) — `get_user_posts` paginé
- [`main.py`](../../main.py) — route `/` mise à jour avec pagination
- [`static/js/utils.js`](../../static/js/utils.js) — ajout de `escapeHtml` et `formatDate`
- [`templates/home.html`](../../templates/home.html) — bouton "Load More Posts" et JS de pagination
- [`populate_db.py`](../../populate_db.py) — script de peuplement de la DB pour les tests
- [`populate_images/`](../../populate_images/) — images utilisées par `populate_db.py`

## Ce qu'on a fait
- Ajouté le schéma `PaginatedPostsResponse` pour définir le contrat entre frontend et backend.
- Mis à jour `get_posts` pour accepter les query parameters `skip` et `limit`, et renvoyer les métadonnées de pagination.
- Ajouté `posts_per_page` dans `config.py` pour avoir une valeur configurable.
- Mis à jour la route `/` dans `main.py` pour ne rendre que la première page côté serveur.
- Implémenté le bouton "Load More Posts" dans `home.html` : le premier chargement est rendu côté serveur (Jinja2), les pages suivantes sont chargées dynamiquement via l'API.
- Ajouté `escapeHtml` et `formatDate` dans `utils.js` pour le rendu JS sécurisé des posts chargés dynamiquement.
- Ajouté la pagination sur `get_user_posts` dans `routers/users.py`.
- Créé `populate_db.py` pour remplir la DB avec des utilisateurs et posts de test.

## Points techniques à retenir

### Pourquoi paginer ?

Renvoyer tous les posts d'un coup pose problème quand la base grandit — charge réseau, charge DB, lenteur d'affichage. La pagination coupe les résultats en pages : on charge les 10 premiers, puis les 10 suivants sur demande.

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

`has_more` est calculé côté serveur pour éviter que le frontend n'ait à le déduire lui-même :

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

- `skip` : nombre de résultats à ignorer (l'offset en DB).
- `limit` : nombre de résultats à renvoyer.
- `Query(ge=0)` et `Query(ge=1, le=100)` : validation automatique des paramètres.

Pour la pagination des posts d'un utilisateur spécifique, la même logique s'applique dans `get_user_posts` de `routers/users.py`.

### `posts_per_page` dans `config.py`

```python
# config.py
class Settings(BaseSettings):
    posts_per_page: int = 10
```

La valeur par défaut (`10`) est centralisée dans la configuration — modifiable via variable d'environnement `POSTS_PER_PAGE` sans toucher au code.

### Approche hybride : SSR + JS "Load More"

La première page est rendue côté serveur (Jinja2) — ce qui est rapide et SEO-friendly. Les pages suivantes sont chargées dynamiquement via l'API au clic sur "Load More".

**Route `/` mise à jour :**
```python
# main.py
async def home(request: Request, db: ...):
    total = count_result.scalar() or 0
    posts = result.scalars().all()  # seulement la première page
    has_more = len(posts) < total

    return templates.TemplateResponse(request, "home.html", {
        "posts": posts,
        "limit": settings.posts_per_page,
        "has_more": has_more,
    })
```

**`home.html` — initialisation des variables JS depuis Jinja2 :**

```javascript
// home.html — les {{ }} sont résolus côté serveur avant que le navigateur voie le fichier
let currentOffset = {{ limit }};  // commence après les posts déjà rendus
const limit = {{ limit }};
let hasMore = {{ 'true' if has_more else 'false' }};
```

Jinja2 remplace `{{ limit }}` et `{{ 'true' if has_more else 'false' }}` côté serveur — le navigateur reçoit directement les valeurs numériques et booléennes. L'apparence de rouge dans PyCharm à l'intérieur des balises `<script>` est un faux positif : PyCharm ne comprend pas Jinja2 dans le JS (même phénomène qu'en séance 9 avec `{{ post.id }}`).

**Le bouton "Load More" n'est rendu que si `has_more` est `true` :**
```html
{% if has_more %}
  <button type="button" class="btn btn-outline-primary" id="loadMoreBtn">Load More Posts</button>
{% endif %}
```

**JS — appel API au clic :**
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

Lors du rendu côté serveur, Jinja2 échappe automatiquement le HTML. En JS, il faut le faire manuellement pour éviter les failles XSS :

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

`createPostHTML` dans `home.html` utilise `escapeHtml` sur tous les champs issus de l'API pour que le rendu dynamique soit aussi sûr que le rendu serveur.

### `populate_db.py` — peuplement de la DB pour les tests

Créé pour avoir suffisamment de données pour tester la pagination (44 posts, 6 utilisateurs). Il utilise `httpx.AsyncClient` avec `ASGITransport` pour appeler l'API directement sans lancer un vrai serveur HTTP :

```python
transport = httpx.ASGITransport(app=app)
async with httpx.AsyncClient(transport=transport, base_url="http://localhost") as client:
    response = await client.post("/api/users", json={...})
```

```bash
uv run python populate_db.py
```

Il réinitialise la DB à chaque exécution (supprime les données existantes et les images de profil).

### Cache navigateur et fichiers JS

Quand on modifie un fichier JS servi comme fichier statique, le navigateur peut conserver l'ancienne version en cache. Si un changement ne se reflète pas dans le comportement de la page, faire un **hard refresh** : `Ctrl + Shift + R` (vide le cache et recharge tous les assets).

### Pagination FastAPI intégrée (pour info)

FastAPI propose un utilitaire `Params` de la librairie `fastapi-pagination` pour standardiser la pagination en production. Pour ce cours, on a implémenté la logique manuellement pour bien comprendre le mécanisme.

## Remarques / questions à creuser
- Le script `populate_db.py` utilise `ASGITransport` de `httpx` — cela permet de tester l'application entière (y compris la validation Pydantic et la logique des routes) sans démarrer un vrai serveur, ce qui le rend utile autant pour les tests que pour le peuplement.
- `has_more = skip + len(posts) < total` : on compare `skip + len(posts)` (le dernier index traité) au total. Si des posts sont créés ou supprimés entre deux requêtes, `total` peut changer — c'est acceptable pour ce cas d'usage.
- La pagination par `skip`/`limit` (aussi appelée offset pagination) est simple à implémenter, mais peut être inefficace sur de très grandes tables (la DB doit scanner les `skip` premières lignes). En production à grande échelle, la pagination par curseur (keyset pagination) est plus performante.
- À venir en séance 14 : réinitialisation de mot de passe par email, tokens et background tasks.
