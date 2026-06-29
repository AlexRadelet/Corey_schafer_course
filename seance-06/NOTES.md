# Séance 06 — Completing CRUD : Update and Delete (PUT, PATCH, DELETE)

## Code de la séance
- [`main.py`](main.py) — routes `PUT/PATCH/DELETE` pour `posts` et `users`
- [`schemas.py`](schemas.py) — `UserUpdate` et `PostUpdate` ajoutés
- [`models.py`](models.py) — relation `User.posts` avec `cascade="all, delete-orphan"`

## Ce qu'on a fait
- Complété le CRUD (Create/Read déjà faits en séances 4-5) avec **Update** et **Delete** pour les posts et les utilisateurs.
- Distinction entre deux façons de mettre à jour une ressource :
  - **`PUT`** = mise à jour complète : le client doit renvoyer **tous** les champs (on réutilise `PostCreate` comme schéma d'entrée).
  - **`PATCH`** = mise à jour partielle : le client n'envoie que les champs qu'il veut changer (nouveau schéma `PostUpdate`/`UserUpdate`, tous les champs optionnels).
- Découverte de `model_dump(exclude_unset=True)` : ne récupère que les champs **réellement envoyés** par le client dans la requête PATCH, pour ne pas écraser les autres champs avec leurs valeurs par défaut (`None`).
- Sur `DELETE`, retour d'un statut **204 No Content** : convention REST pour signaler qu'une suppression a réussi, sans contenu à renvoyer.
- Réflexion sur le **cascade delete** : si on supprime un utilisateur, qu'advient-il de ses posts ? Réponse choisie ici : `cascade="all, delete-orphan"` sur la relation `User.posts` → supprimer un utilisateur supprime automatiquement tous ses posts.
- Vérifications d'unicité avant modification (`PATCH /api/users/{user_id}`) : si le client change le `username` ou l'`email`, on vérifie qu'aucun autre utilisateur ne les utilise déjà avant d'appliquer le changement.

## Points techniques à retenir

### PUT : mise à jour complète
```python
@app.put("/api/posts/{post_id}", response_model=PostResponse)
def update_post_full(post_id: int, post_data: PostCreate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    post.title = post_data.title
    post.content = post_data.content
    post.user_id = post_data.user_id

    db.commit()
    db.refresh(post)
    return post
```
On réutilise `PostCreate` (qui exige tous les champs) comme schéma d'entrée du `PUT`, puisque le client doit fournir l'objet complet.

### PATCH : mise à jour partielle avec `exclude_unset`
```python
# schemas.py
class PostUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)
```
```python
# main.py
@app.patch("/api/posts/{post_id}", response_model=PostResponse)
def update_post_partial(post_id: int, post_data: PostUpdate, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    # on ne veut update que les infos données par le client (pas écraser avec des None)
    update_data = post_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)

    db.commit()
    db.refresh(post)
    return post
```
- `exclude_unset=True` : ne garde que les champs **présents dans la requête JSON**, même si leur valeur est `None`.
- `exclude_unset=False` (comportement par défaut) : renverrait tous les champs du modèle, y compris ceux non précisés par le client, avec leur valeur par défaut (`None`) — ce qui écraserait par erreur les champs non modifiés.

⚠️ **Piège pratique côté tests Swagger UI** : sur `PATCH`, Swagger pré-remplit le corps JSON avec des valeurs d'exemple pour tous les champs (y compris ceux qu'on ne veut pas changer). Pour un champ `EmailStr | None`, la valeur d'exemple `"string"` n'est pas un email valide → 422, même si le champ est optionnel. Solution : remplacer par `null` (ou supprimer la ligne) les champs qu'on ne veut pas modifier avant d'exécuter la requête.

### DELETE et le statut 204
```python
@app.delete("/api/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_post(post_id: int, db: Annotated[Session, Depends(get_db)]):
    result = db.execute(select(models.Post).where(models.Post.id == post_id))
    post = result.scalars().first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")

    db.delete(post)
    db.commit()
```
Pas de `response_model` ni de `return` utile ici : un 204 ne doit pas avoir de corps de réponse.

### Cascade delete sur la relation
```python
# models.py
class User(Base):
    ...
    posts: Mapped[list["Post"]] = relationship(back_populates="author", cascade="all, delete-orphan")
```
Supprimer un `User` supprime désormais automatiquement tous ses `Post` associés (plutôt que de laisser des posts orphelins en base, ou de bloquer la suppression).

### Vérifier l'unicité avant une mise à jour
```python
if user_update.username is not None and user_update.username != user.username:
    result = db.execute(select(models.User).where(models.User.username == user_update.username))
    if result.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
```
On ne vérifie l'unicité que si le client a effectivement demandé à changer ce champ (`is not None`) et que la nouvelle valeur diffère de l'actuelle — évite une requête DB inutile si rien n'a changé sur ce champ.

## Remarques / questions à creuser
- Les fichiers uploadés par les utilisateurs (dossier `media/`, ex: `profile_pics/`) sont désormais ignorés par git, comme `blog.db` — ce sont des données locales/de dev, pas du code de cours.
- `UserResponse` continue d'hériter de `UserBase` et expose donc encore l'email publiquement (limite déjà notée en séance 5, toujours pas résolue — à surveiller si une séance future revient sur la sécurité/auth).
- À creuser en séance 7 : passage en asynchrone (`async def`), pour voir l'impact sur les performances et la façon d'écrire les routes.
