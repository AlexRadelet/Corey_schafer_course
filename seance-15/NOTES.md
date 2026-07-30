# Séance 15 — PostgreSQL et Alembic : Migrations de base de données

## Code de cette séance
- [`config.py`](../../config.py) — ajout de `database_url` dans `Settings`
- [`database.py`](../../database.py) — connexion via `settings.database_url` (plus de SQLite hardcodé)
- [`models.py`](../../models.py) — ajout du champ `likes` sur `Post`
- [`routers/users.py`](../../routers/users.py) — suppression de `.replace(tzinfo=UTC)` (PostgreSQL gère les timezones nativement)
- [`populate_db.py`](../../populate_db.py) — fix Windows `ProactorEventLoop`
- [`main.py`](../../main.py) — suppression de `Base.metadata.create_all` du lifespan (Alembic gère les tables)
- [`alembic.ini`](../../alembic.ini) — configuration Alembic
- [`alembic/env.py`](../../alembic/env.py) — intégration avec les modèles et settings, fix Windows
- [`alembic/versions/`](../../alembic/versions/) — migrations générées automatiquement

## Ce qu'on a fait
- Remplacé SQLite par PostgreSQL comme base de données.
- Déplacé l'URL de connexion dans `config.py` / `.env` (plus rien de hardcodé dans `database.py`).
- Installé Alembic et configuré `env.py` pour qu'il lise les modèles et l'URL depuis les settings.
- Généré la migration initiale (`initial schema`) et appliqué les tables en base.
- Ajouté un champ `likes` au modèle `Post`, généré une deuxième migration et appliqué.
- Adapté deux points spécifiques à Windows (voir ci-dessous).
- Supprimé le `.replace(tzinfo=UTC)` désormais inutile avec PostgreSQL.

## Points techniques à retenir

### Pourquoi passer de SQLite à PostgreSQL ?

SQLite est idéal en développement (un simple fichier, zéro configuration). Mais il ne supporte pas les migrations proprement, ni les accès concurrents en écriture, ni certains types de données avancés. PostgreSQL est la référence pour la production.

Seule la chaîne de connexion change — tout le code SQLAlchemy reste identique :

```
# SQLite (développement, séances 1–14)
sqlite+aiosqlite:///./blog.db

# PostgreSQL (production)
postgresql+psycopg://bloguser:password@localhost/blog
```

### `database_url` dans `config.py`

```python
# config.py
class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./blog.db"
    # ...
```

Et dans `database.py` :
```python
engine = create_async_engine(settings.database_url)
```

Pydantic Settings expose les champs en **minuscules** — la variable d'environnement correspondante est `DATABASE_URL` (majuscules), mais l'attribut Python est `settings.database_url`.

Pour passer à PostgreSQL, il suffit d'ajouter dans `.env` :
```
DATABASE_URL=postgresql+psycopg://bloguser:password@localhost/blog
```

### Pourquoi Alembic plutôt que `create_all` ?

`Base.metadata.create_all()` crée les tables qui n'existent pas — mais si une table existe déjà et qu'on a ajouté une colonne, elle ne fait **rien**. Il n'y a pas de suivi des changements.

Alembic est un système de **migration** : il compare l'état actuel de la DB avec les modèles SQLAlchemy et génère un fichier de migration (l'équivalent d'un `git commit` pour le schéma de la base).

```
alembic/
├── env.py          # configuration : comment Alembic se connecte et trouve les modèles
├── versions/       # un fichier par migration
│   ├── 73a8574bfacd_initial_schema.py
│   └── 2966c971ebab_add_likes_to_posts.py
alembic.ini         # configuration générale (logging, chemin des versions)
```

### Installation et initialisation

```bash
uv add alembic
uv add "psycopg[binary]"  # driver PostgreSQL async

# Sur Windows : AppLocker bloque l'exécutable alembic, passer par Python
uv run python -m alembic init -t async alembic
```

`-t async` génère un `env.py` prêt pour SQLAlchemy async (avec `async_engine_from_config`).

### Configuration de `alembic/env.py`

```python
# alembic/env.py — les 3 lignes clés à ajouter/modifier
import models
from config import settings
from database import Base

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata  # permet à --autogenerate de détecter les modèles
```

`target_metadata = Base.metadata` est ce qui permet à Alembic de comparer les modèles avec la DB pour générer les migrations automatiquement.

### Fix Windows : `ProactorEventLoop` incompatible avec psycopg

Sur Windows, Python utilise `ProactorEventLoop` par défaut pour `asyncio.run()`, mais psycopg (le driver PostgreSQL async) exige `SelectorEventLoop`. Ce problème n'existe pas sur Mac/Linux.

**Dans `alembic/env.py` :**
```python
def run_migrations_online() -> None:
    # ProactorEventLoop (Windows default) est incompatible avec psycopg async
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_async_migrations())
```

**Dans `populate_db.py` :**
```python
if __name__ == "__main__":
    if hasattr(asyncio, "WindowsSelectorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(populate())
```

`hasattr(asyncio, "WindowsSelectorEventLoopPolicy")` vérifie qu'on est bien sur Windows avant d'appliquer la politique — le code reste portable sur Mac/Linux.

### Commandes Alembic essentielles

```bash
# Générer une migration automatiquement depuis les modèles
uv run python -m alembic revision --autogenerate -m "description"

# Appliquer toutes les migrations en attente
uv run python -m alembic upgrade head

# Revenir à la migration précédente
uv run python -m alembic downgrade -1

# Voir où on en est
uv run python -m alembic current

# Voir l'historique des migrations
uv run python -m alembic history
```

Sur Windows, toujours utiliser `uv run python -m alembic` (AppLocker bloque `uv run alembic`).

### Workflow Alembic pour les modifications de schéma

1. Modifier le modèle SQLAlchemy dans `models.py`
2. Générer la migration : `uv run python -m alembic revision --autogenerate -m "description"`
3. **Relire le fichier généré** dans `alembic/versions/` pour vérifier que la migration est correcte
4. Appliquer : `uv run python -m alembic upgrade head`

Exemple — ajout du champ `likes` sur `Post` :

```python
# models.py
likes: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
```

`default=0` : valeur côté Python (pour les objets créés via SQLAlchemy).
`server_default="0"` : valeur par défaut côté base de données (pour les lignes existantes lors d'un `ALTER TABLE`). Les deux sont nécessaires : sans `server_default`, PostgreSQL refuserait d'ajouter une colonne `NOT NULL` sur une table non vide.

### PostgreSQL et les timezones

PostgreSQL stocke et renvoie les datetimes avec leurs informations de timezone. SQLite les stockait sans timezone (datetimes "naïfs"), ce qui nécessitait un `.replace(tzinfo=UTC)` pour les comparer à `datetime.now(UTC)`.

```python
# Avant (SQLite) — dans routers/users.py
if reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):

# Après (PostgreSQL) — comparaison directe possible
if reset_token.expires_at < datetime.now(UTC):
```

### Vérification dans PostgreSQL

```bash
psql blog -U bloguser     # connexion à la DB
\dt                        # liste les tables
\d posts                   # détail des colonnes d'une table
\q                         # quitter
```

### Setup sur un nouveau poste

Pour initialiser le projet sur une nouvelle machine :
1. Créer la DB : `createdb blog -U bloguser`
2. Configurer `.env` avec `DATABASE_URL`
3. Appliquer toutes les migrations : `uv run python -m alembic upgrade head`
4. Peupler (optionnel) : `uv run python populate_db.py`

Plus de suppression/recréation manuelle de la base — Alembic gère tout.

## Remarques / questions à creuser
- Les fichiers de migration dans `alembic/versions/` doivent être commités dans git — ils font partie de l'historique du schéma et permettent à n'importe quel développeur de reconstruire la base.
- `--autogenerate` ne détecte pas tout : les index, les contraintes complexes, certains changements de type peuvent nécessiter une intervention manuelle dans le fichier de migration généré. Toujours relire la migration avant de l'appliquer.
- À venir en séance 16 : stockage des images sur AWS S3.
