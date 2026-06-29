# Séance 05 — Adding a Database : SQLAlchemy Models and Relationships

## Code de la séance
- [`database.py`](database.py) — configuration de la connexion SQLAlchemy (`engine`, `SessionLocal`, `get_db`)
- [`models.py`](models.py) — modèles SQLAlchemy `User` et `Post` (avec relation)
- [`schemas.py`](schemas.py) — schémas `UserBase`/`UserCreate`/`UserResponse` ajoutés, `PostCreate`/`PostResponse` mis à jour pour la DB
- [`main.py`](main.py) — toutes les routes utilisent maintenant la DB via dependency injection
- [`templates/home.html`](templates/home.html), [`templates/post.html`](templates/post.html), [`templates/user_posts.html`](templates/user_posts.html)

## Ce qu'on a fait
- Remplacement de la liste Python `posts` (en mémoire, perdue à chaque redémarrage) par une vraie base de données avec **SQLAlchemy**, l'ORM le plus utilisé en Python.
- Choix de **SQLite** pour le développement (fichier `blog.db`, simple à utiliser) — SQLAlchemy permet de basculer vers PostgreSQL plus tard en prod en changeant uniquement l'URL de connexion.
- Mise en place des **3 couches** d'une application FastAPI typique :
  1. **Database models** (`models.py`) : ce qu'on stocke réellement en base.
  2. **Pydantic schemas** (`schemas.py`) : ce que l'API accepte/renvoie (déjà vu en séance 4).
  3. **API routes** (`main.py`) : les endpoints FastAPI.
  - Une librairie comme **SQLModel** (du même auteur que FastAPI) permettrait de fusionner ces couches, mais cette séparation reste la norme en entreprise car chaque couche a un rôle différent.
- Création de deux modèles avec une **relation** : `User` (1) → `Post` (plusieurs), via `relationship(back_populates=...)` et une `ForeignKey`.
- Séparation des fichiers statiques (`static/`, fournis par le dev) et **médias** (`media/`, uploadés par les utilisateurs) — pratique pour gérer ces deux types de fichiers différemment (ex: sauvegardes, CDN).
- Utilisation de la **dependency injection** de FastAPI (`Depends`) pour fournir une session DB à chaque route qui en a besoin.
- Mise à jour des templates pour utiliser les nouveaux objets : `post.author` (objet `User`, plus un dict) et `post.date_posted` (un vrai `datetime`, qu'on formate avec `.strftime(...)`).
- Nouveau template `user_posts.html` : liste des posts d'un utilisateur donné.

## Points techniques à retenir

### Configuration de la base de données
```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./blog.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    with SessionLocal() as db:
        yield db
```
- `get_db` est un générateur : FastAPI s'en sert comme dépendance, ouvre une session, la fournit à la route, puis la ferme automatiquement après la requête.

### Modèles avec relation 1-N
```python
# models.py
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    posts: Mapped[list["Post"]] = relationship(back_populates="author")

class Post(Base):
    __tablename__ = "posts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    author: Mapped[User] = relationship(back_populates="posts")
```
- `relationship(back_populates=...)` permet de naviguer dans les deux sens : `user.posts` et `post.author`.
- Une `@property` sur le modèle (ex: `image_path`) permet d'exposer une valeur calculée qui n'est pas une colonne en base, mais qui sera lisible par Pydantic grâce à `from_attributes=True`.

### Créer les tables au démarrage
```python
# main.py
Base.metadata.create_all(bind=engine)
```
- Idempotent : peut être appelé plusieurs fois sans problème, même si les tables existent déjà.

### Dependency injection d'une session DB dans une route
```python
from typing import Annotated
from sqlalchemy.orm import Session
from sqlalchemy import select
from fastapi import Depends

@app.get("/api/posts", response_model=list[PostResponse])
def get_posts(db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post))
    return result.scalars().all()
```
- `Annotated[Session, Depends(get_db)]` est la syntaxe moderne pour déclarer une dépendance : FastAPI appelle `get_db`, injecte la session obtenue dans le paramètre `db`.

### Vérifier l'existence avant d'agir
Sur les routes qui touchent un utilisateur ou un post précis, on vérifie d'abord que la ressource existe avant de continuer (sinon `None` se propagerait silencieusement) :
```python
result = db.execute(select(models.User).where(models.User.id == user_id))
user = result.scalars().first()
if not user:
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
```

### Templates avec de vrais objets (et plus des dicts)
```jinja
<img src="{{ post.author.image_path }}" alt="{{ post.author.username }}'s profile picture">
<small>{{ post.date_posted.strftime('%B %d, %Y') }}</small>
```
- `post.author` est maintenant un objet `User` (accès par attribut, comme avec un dict grâce à Jinja2, mais ici c'est un vrai objet Python).
- `post.date_posted` est un objet `datetime` réel : on peut appeler `.strftime(...)` directement dans le template pour le formater.

## Remarques / questions à creuser
- `UserResponse` hérite actuellement de `UserBase`, donc renvoie aussi `email` au client — une faille potentielle (l'email d'un utilisateur ne devrait sans doute pas être public). À corriger dans une séance future, probablement en repensant la hiérarchie des schémas Pydantic.
- Les dates suivent le format **ISO 8601** par défaut dans les réponses JSON (géré automatiquement par Pydantic pour un champ `datetime`).
- Pour visualiser le contenu de `blog.db` pendant le développement, il existe des outils dédiés (ex: DB Browser for SQLite) — pratique pour vérifier que les données sont bien persistées entre deux redémarrages du serveur.
- À creuser en séance 6 : compléter le CRUD avec les opérations de mise à jour et de suppression (PUT, PATCH, DELETE).
