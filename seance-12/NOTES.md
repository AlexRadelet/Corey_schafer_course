# Séance 12 — File Uploads : Traitement d'images et stockage

## Code de cette séance
- [`image_utils.py`](image_utils.py) — traitement et suppression des images de profil (Pillow)
- [`routers/users.py`](routers/users.py) — route `PATCH /{user_id}/picture`, suppression de l'image à la suppression du compte, `image_file` retiré de `update_user`
- [`config.py`](config.py) — ajout de `max_upload_size_bytes` (5 MB)
- [`schemas.py`](schemas.py) — `image_file` retiré de `UserUpdate`
- [`templates/account.html`](templates/account.html) — formulaire d'upload de photo de profil
- Correction du typo `CurrenUser` → `CurrentUser` dans `auth.py` et tous les routers

## Ce qu'on a fait
- Créé `image_utils.py` pour le traitement des images avec Pillow : redimensionnement carré 300×300, correction de l'orientation EXIF, conversion en JPEG, nom unique via UUID.
- Ajouté un endpoint dédié `PATCH /api/users/{user_id}/picture` pour l'upload de photo de profil (séparé de `PATCH /{user_id}` car on travaille avec un fichier, pas du JSON).
- Suppression automatique de l'ancienne image lors d'un nouvel upload ou de la suppression du compte.
- Retiré `image_file` de `UserUpdate` — le champ n'est plus modifiable manuellement (sécurité : on ne peut plus se pointer vers n'importe quel fichier).
- Limite de taille configurable dans `config.py` (`max_upload_size_bytes = 5 MB`).
- Correction du typo `CurrenUser` → `CurrentUser` dans `auth.py` et tous les routers.

## Points techniques à retenir

### `image_utils.py` — pourquoi une fonction sync, pas async ?

```python
from PIL import Image, ImageOps

def process_profile_image(content: bytes) -> str:
    with Image.open(BytesIO(content)) as original:
        img = ImageOps.exif_transpose(original)          # corrige l'orientation EXIF
        img = ImageOps.fit(img, (300, 300), method=Image.Resampling.LANCZOS)  # crop carré
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")                     # JPEG ne supporte pas la transparence
        filename = f"{uuid.uuid4().hex}.jpg"             # nom unique garanti
        filepath = PROFILE_PICS_DIR / filename
        PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)
        img.save(filepath, "JPEG", quality=85, optimize=True)
    return filename
```

Pillow est une librairie **synchrone** — elle ne supporte pas `await`. Le traitement d'image est aussi du **CPU work** (redimensionnement, compression), pas de l'I/O réseau. On ne peut pas l'appeler directement dans une route `async def` sans bloquer la boucle d'événements.

Solution : `run_in_threadpool` de Starlette, qui exécute une fonction synchrone dans un thread séparé sans bloquer :

```python
from starlette.concurrency import run_in_threadpool

filename = await run_in_threadpool(process_profile_image, content)
```

Règle générale séance 7 rappelée : **async pour l'I/O, sync pour le CPU** — et `run_in_threadpool` pour appeler du code sync depuis une route async.

### Endpoint dédié à l'upload : `PATCH /{user_id}/picture`

L'upload de fichier utilise `multipart/form-data`, pas `application/json` — il mérite donc sa propre route plutôt que d'être intégré à `PATCH /{user_id}` :

```python
from fastapi import UploadFile

@router.patch("/{user_id}/picture", response_model=UserPrivate)
async def upload_profile_picture(
    user_id: int,
    file: UploadFile,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    content = await file.read()

    # Vérification de la taille avant traitement
    if len(content) > settings.max_upload_size_bytes:
        raise HTTPException(400, detail=f"File too large. Maximum size is 5MB")

    try:
        filename = await run_in_threadpool(process_profile_image, content)
    except UnidentifiedImageError:
        raise HTTPException(400, detail="Invalid image file")

    # Supprimer l'ancienne image avant d'enregistrer la nouvelle
    old_filename = user.image_file
    user.image_file = filename
    await db.commit()
    await db.refresh(user)

    if old_filename:
        delete_profile_image(old_filename)

    return user
```

`UnidentifiedImageError` est levée par Pillow si le fichier uploadé n'est pas une image valide — on la catch pour renvoyer un 400 lisible plutôt qu'une erreur 500 interne.

### Suppression de l'image à la suppression du compte

```python
@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(...):
    old_filename = user.image_file   # récupérer avant la suppression en DB
    await db.delete(user)
    await db.commit()
    if old_filename:
        delete_profile_image(old_filename)  # nettoyer le fichier sur le disque
```

Important : on récupère `user.image_file` **avant** le `db.delete()` — après la suppression, l'objet SQLAlchemy n'est plus accessible.

### Sécurité : retrait de `image_file` de `UserUpdate`

```python
# Avant (séance 11) — risque de sécurité
class UserUpdate(BaseModel):
    image_file: str | None = Field(...)  # n'importe qui pouvait pointer vers n'importe quel fichier

# Après (séance 12) — image gérée exclusivement par le endpoint dédié
class UserUpdate(BaseModel):
    username: str | None = ...
    email: EmailStr | None = ...
    # image_file supprimé
```

De même dans `update_user()`, le bloc `if user_update.image_file is not None` a été retiré.

### Orientation EXIF et `ImageOps.exif_transpose`

Les photos prises avec un smartphone encodent leur orientation dans les métadonnées EXIF (l'image est stockée "de côté" dans le fichier, avec une balise qui dit "afficher à 90°"). La plupart des navigateurs tiennent compte de cette balise, mais Pillow ne le fait pas par défaut — l'image apparaîtrait mal orientée après redimensionnement.

`ImageOps.exif_transpose` applique la rotation réelle avant tout traitement, ce qui garantit une image correctement orientée quelle que soit la source.

## Remarques / questions à creuser
- La limite de taille (5 MB) est lue dans `config.py` via `pydantic-settings`, ce qui permet de la modifier sans toucher au code (variable d'environnement `MAX_UPLOAD_SIZE_BYTES`).
- `PROFILE_PICS_DIR.mkdir(parents=True, exist_ok=True)` dans `process_profile_image` crée le dossier à la volée si nécessaire — robuste même si `media/profile_pics/` n'existe pas encore.
- Les fichiers uploadés restent dans `media/` qui est dans `.gitignore` — seul `media/.gitkeep` est tracké pour que le dossier existe dans le repo.
- À venir en séance 13 : pagination des posts avec des query parameters.
