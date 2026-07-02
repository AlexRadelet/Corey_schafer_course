# Séance 07 — Sync vs Async : Conversion de l'app en asynchrone

## Code de cette séance
- [`main.py`](main.py) — toutes les routes converties en `async def`, eager loading avec `selectinload`
- [`database.py`](database.py) — moteur et session entièrement asynchrones (`create_async_engine`, `async_sessionmaker`)

## Ce qu'on a fait
- Converti toutes les routes de `def` synchrone en `async def`.
- Remplacé le moteur SQLAlchemy synchrone par un moteur **asynchrone** (`create_async_engine`) et la session par `async_sessionmaker`.
- Changé l'URL de la base de données : `sqlite:///` → `sqlite+aiosqlite:///` (driver async pour SQLite).
- Installé `aiosqlite` (driver async SQLite) : `uv add aiosqlite`.
- Remplacé `Base.metadata.create_all(bind=engine)` (appel synchrone au démarrage) par un **`lifespan`** contextmanager asynchrone.
- Découvert que le **lazy loading** ne fonctionne pas en async SQLAlchemy → remplacement par de l'**eager loading** avec `selectinload`.

## Points techniques à retenir

### Async vs Sync — quand utiliser quoi ?

| Situation | Recommandation |
|---|---|
| Requête DB, appel réseau, lecture de fichier | `async def` + `await` |
| Calcul CPU pur, traitement d'image, lib sync | `def` classique |
| Opérations simples et rapides | `def` classique suffit |

**La règle clé** : async aide pour les opérations **I/O** (attente d'une réponse externe), pas pour le calcul CPU. Dans notre cas, toutes les routes font des requêtes SQL → `async def` est pertinent.

> FastAPI peut gérer des routes `def` et `async def` dans la même appli — l'important est de choisir en fonction du besoin de chaque route, pas d'uniformiser pour uniformiser.

### `database.py` — passage au mode async

```python
# Avant (sync)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
engine = create_engine("sqlite:///./blog.db", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    with SessionLocal() as db:
        yield db
```

```python
# Après (async)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./blog.db"

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

Points à noter :
- Le préfixe de l'URL passe de `sqlite` à `sqlite+aiosqlite` (indique à SQLAlchemy d'utiliser le driver `aiosqlite`).
- `expire_on_commit=False` : évite que SQLAlchemy ne "désactive" les objets après un `commit` (nécessaire en async car recharger depuis la DB serait une opération async supplémentaire à gérer).

### Lifespan : remplacement de `Base.metadata.create_all`

En sync, on appelait `Base.metadata.create_all(bind=engine)` directement au niveau module. En async, cet appel ne peut pas se faire au niveau module — il faut passer par le système de **lifespan** de FastAPI :

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Startup : création des tables si elles n'existent pas
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown : fermeture propre du moteur
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

- `engine.begin()` ouvre une connexion async pour les opérations DDL (création de tables).
- `run_sync(Base.metadata.create_all)` : `create_all` est une fonction synchrone — `run_sync` permet de l'exécuter dans le contexte async sans bloquer la boucle d'événements.
- `engine.dispose()` au shutdown ferme proprement toutes les connexions.

### Conversion des routes : `await` sur toutes les opérations DB

```python
# Avant (sync)
def get_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    db.commit()
    db.refresh(post)
    return post
```

```python
# Après (async)
async def get_post(post_id: int, db: Annotated[AsyncSession, Depends(get_db)]):
    result = await db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    await db.commit()
    await db.refresh(post)
    return post
```

`db.add()` est la seule opération DB qui **ne prend pas `await`** — c'est une opération en mémoire (ajoute l'objet à la session locale), pas une opération I/O.

### Lazy loading vs Eager loading

En SQLAlchemy **synchrone**, accéder à `post.author` charge automatiquement l'auteur depuis la DB (lazy loading). En **async**, ce chargement implicite n'est pas possible (une opération SQL async nécessite un `await`).

Solution : **eager loading** avec `selectinload` — on indique à SQLAlchemy de charger la relation dans la même requête SQL (ou une requête supplémentaire immédiate) :

```python
from sqlalchemy.orm import selectinload

# Charge les posts ET leurs auteurs en une seule opération
result = await db.execute(
    select(models.Post).options(selectinload(models.Post.author))
)
```

Pour `db.refresh()` après un `commit`, il faut aussi préciser quelles relations recharger :

```python
await db.refresh(new_post, attribute_names=["author"])
```

Sans `attribute_names=["author"]`, `refresh` recharge l'objet mais pas ses relations — `post.author` serait alors inaccessible.

## Remarques / questions à creuser
- `aiosqlite` est le driver async pour SQLite. Pour PostgreSQL en async, l'équivalent est `asyncpg` (ou `psycopg` v3 en mode async).
- En prod avec beaucoup de trafic concurrent, async fait une vraie différence. Avec SQLite en dev et peu de requêtes, la différence est imperceptible — mais prendre l'habitude d'écrire async prépare bien pour le passage en PostgreSQL.
- `selectinload` génère une seconde requête SQL séparée pour charger la relation (SELECT ... WHERE id IN (...)). C'est différent d'un JOIN SQL classique, mais plus simple à gérer en ORM.
- À venir en séance 8 : `APIRouter` pour organiser les routes en modules séparés (éviter que `main.py` grossisse indéfiniment).
