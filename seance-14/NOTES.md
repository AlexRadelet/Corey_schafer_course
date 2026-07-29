# Séance 14 — Réinitialisation de mot de passe : Email, Tokens et Background Tasks

## Code de cette séance
- [`auth.py`](../../auth.py) — ajout de `generate_reset_token()` et `hash_reset_token()` (sha256)
- [`config.py`](../../config.py) — ajout des settings mail, `reset_token_expire_minutes`, `frontend_url`
- [`email_utils.py`](../../email_utils.py) — NOUVEAU : envoi d'emails async avec aiosmtplib
- [`models.py`](../../models.py) — ajout du modèle `PasswordResetToken`
- [`schemas.py`](../../schemas.py) — ajout de `ForgotPasswordRequest`, `ResetPasswordRequest`, `ChangePasswordRequest`
- [`routers/users.py`](../../routers/users.py) — 3 nouveaux endpoints : `forgot-password`, `reset-password`, `PATCH /me/password`
- [`main.py`](../../main.py) — routes frontend pour les pages forgot/reset password
- [`templates/email/password_reset.html`](../../templates/email/password_reset.html) — NOUVEAU : template HTML de l'email
- [`templates/forgot_password.html`](../../templates/forgot_password.html) — NOUVEAU : formulaire de demande de reset
- [`templates/reset_password.html`](../../templates/reset_password.html) — NOUVEAU : formulaire de nouveau mot de passe
- [`templates/login.html`](../../templates/login.html) — lien "Forgot password?" ajouté
- [`templates/account.html`](../../templates/account.html) — section changement de mot de passe
- [`populate_db.py`](../../populate_db.py) — mis à jour pour la nouvelle séance

## Ce qu'on a fait
- Ajouté le modèle `PasswordResetToken` en base de données pour stocker les tokens de reset (hachés, jamais en clair).
- Créé `email_utils.py` avec `send_email` (async via aiosmtplib) et `send_password_reset_email`.
- Ajouté 3 endpoints dans `routers/users.py` : demande de reset (`POST /forgot-password`), validation et reset (`POST /reset-password`), changement de mot de passe connecté (`PATCH /me/password`).
- Utilisé `BackgroundTasks` de FastAPI pour envoyer l'email de manière non bloquante.
- Créé le template HTML de l'email de reset et les pages frontend associées.
- Configuré Mailtrap comme serveur mail de développement.

## Points techniques à retenir

### Pourquoi hacher les tokens de reset ?

Les tokens de reset ne sont jamais stockés en clair en base de données. Si quelqu'un accède à la DB, il ne peut pas utiliser les tokens.

```python
# auth.py
import hashlib, secrets

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)  # token aléatoire imprédictible

def hash_reset_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()
```

**sha256 ici, pas argon2** — contrairement aux mots de passe (faibles → besoin d'un hash lent contre le bruteforce), les tokens sont de longues chaînes aléatoires imprédictibles : sha256 (rapide) suffit car il n'y a rien à bruteforcer.

### `PasswordResetToken` — modèle en base

```python
# models.py
class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
    )
    user: Mapped[User] = relationship(back_populates="reset_tokens")
```

Et sur `User`, la relation inverse avec cascade delete :
```python
reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
    back_populates="user", cascade="all, delete-orphan",
)
```

Les tokens sont supprimés en cascade à la suppression du compte.

### Nouveaux schémas Pydantic

```python
# schemas.py
class ForgotPasswordRequest(BaseModel):
    email: EmailStr = Field(max_length=120)

class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)
```

### Settings mail dans `config.py`

```python
reset_token_expire_minutes: int = 60
mail_server: str = "localhost"
mail_port: int = 587
mail_username: str = ""
mail_password: SecretStr = SecretStr("")
mail_from: str = "noreply@example.com"
mail_use_tls: bool = True
frontend_url: str = "http://localhost:8000"
```

`frontend_url` est utilisé pour construire le lien de reset dans l'email — bonne pratique pour éviter les attaques de redirection ouverte : le backend ne construit jamais l'URL depuis les données de la requête.

### `email_utils.py` — envoi async avec aiosmtplib

La librairie standard `smtplib` est **synchrone** — l'appeler dans une route async bloquerait la boucle d'événements. `aiosmtplib` est son équivalent async :

```bash
uv add aiosmtplib
```

```python
# email_utils.py
async def send_email(to_email, subject, plain_text, html_content=None):
    message = EmailMessage()
    message["From"] = settings.mail_from
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(plain_text)
    if html_content:
        message.add_alternative(html_content, subtype="html")  # version HTML du mail

    await aiosmtplib.send(
        message,
        hostname=settings.mail_server,
        port=settings.mail_port,
        username=settings.mail_username or None,
        password=settings.mail_password.get_secret_value() or None,
        start_tls=settings.mail_use_tls,
    )
```

`add_alternative(..., subtype="html")` ajoute le HTML comme alternative au texte brut — les clients mail qui ne supportent pas le HTML affichent le texte brut.

### `BackgroundTasks` — envoyer l'email sans bloquer la réponse

Envoyer un email prend du temps. Avec `BackgroundTasks`, FastAPI renvoie immédiatement la réponse au client et exécute l'envoi après :

```python
# routers/users.py
@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(
    request_data: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # ... crée le token, l'enregistre en DB ...

    background_tasks.add_task(
        send_password_reset_email,
        to_email=user.email,
        username=user.username,
        token=token,
    )

    return {"message": "If an account exists with this email, you will receive password reset instructions."}
```

Pour des tâches critiques (paiements, notifications importantes), on utiliserait une file d'attente dédiée comme Celery + Redis. Pour un reset de mot de passe, `BackgroundTasks` suffit.

### 202 Accepted + message générique : sécurité

L'endpoint retourne **toujours** 202 avec le même message, que l'email existe ou non en base :

```python
return {"message": "If an account exists with this email, you will receive password reset instructions."}
```

Si on renvoyait "Email not found" quand le compte n'existe pas, un attaquant pourrait énumérer les emails valides d'une application (user enumeration attack).

### `POST /reset-password` — vérification et expiration

```python
@router.post("/reset-password")
async def reset_password(request_data: ResetPasswordRequest, db: ...):
    token_hash = hash_reset_token(request_data.token)  # on hache avant la recherche

    reset_token = await db.execute(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == token_hash,
        )
    )

    # Check expiration — timezone important !
    if reset_token.expires_at.replace(tzinfo=UTC) < datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(400, "Invalid or expired reset token")

    user.password_hash = hash_password(request_data.new_password)

    # Supprimer TOUS les tokens du user après le reset (invalide les autres sessions)
    await db.execute(sql_delete(models.PasswordResetToken).where(
        models.PasswordResetToken.user_id == user.id,
    ))
    await db.commit()
```

**Pourquoi `.replace(tzinfo=UTC)` ?** SQLite ne stocke pas les informations de timezone dans les colonnes `DateTime` — il renvoie des datetimes "naïfs" (sans timezone). `datetime.now(UTC)` est "aware" (avec timezone). Comparer un datetime naïf et un datetime aware lève une `TypeError` en Python. `.replace(tzinfo=UTC)` ajoute la timezone à l'objet SQLite sans convertir la valeur. Ce problème disparaît avec PostgreSQL (qui gère les timezones nativement).

### `PATCH /me/password` — changement de mot de passe connecté

```python
@router.patch("/me/password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: CurrentUser,
    db: ...
):
    if not verify_password(password_data.current_password, current_user.password_hash):
        raise HTTPException(400, "Current password is incorrect")

    current_user.password_hash = hash_password(password_data.new_password)

    # Invalider les tokens de reset existants
    await db.execute(sql_delete(models.PasswordResetToken).where(
        models.PasswordResetToken.user_id == current_user.id,
    ))
    await db.commit()
```

On vérifie l'ancien mot de passe avant d'autoriser le changement — même si l'utilisateur est connecté. On invalide aussi les tokens de reset en attente : si quelqu'un avait demandé un reset, il ne peut plus l'utiliser après un changement de mot de passe.

### Template HTML de l'email

Les emails HTML ont des contraintes très différentes des pages web :
- **Pas de JavaScript** — bloqué par pratiquement tous les clients mail.
- **CSS inline uniquement** (`style="..."`) — les balises `<style>` et les feuilles de style externes ne sont pas supportées partout.
- **Layout avec `<table>`** — les propriétés CSS modernes (flexbox, grid) ne sont pas supportées par la plupart des clients mail.

```html
<!-- templates/email/password_reset.html -->
<!-- Jinja2 variables : username et reset_url -->
<p>Hi {{ username }},</p>
<a href="{{ reset_url }}">Reset Password</a>
```

Le template est rendu côté serveur avec `templates.env.get_template("email/password_reset.html").render(...)` — accès direct au moteur Jinja2 plutôt qu'à `TemplateResponse`, car on construit une chaîne HTML, pas une réponse HTTP.

### Mailtrap — serveur mail de développement

En développement, on ne veut pas envoyer de vrais emails. Mailtrap est un "email sandbox" : il intercepte les emails et les affiche dans une interface web. 100 emails gratuits par mois.

Configuration dans `.env` :
```
MAIL_SERVER=sandbox.smtp.mailtrap.io
MAIL_PORT=587
MAIL_USERNAME=<mailtrap_username>
MAIL_PASSWORD=<mailtrap_password>
MAIL_FROM=noreply@fastapiblog.com
MAIL_USE_TLS=True
```

En production, on remplacerait par SendGrid, AWS SES, ou un autre service SMTP.

## Remarques / questions à creuser
- Les tokens de reset sont à usage unique : dès qu'un reset réussit, **tous** les tokens du user sont supprimés. Cela empêche la réutilisation du même lien.
- `backend_tasks` de FastAPI s'exécutent dans le même processus que le serveur — si le serveur crash juste après avoir renvoyé la réponse, l'email ne sera pas envoyé. Pour une fiabilité garantie, il faudrait une queue externe (Celery, Redis Queue, etc.).
- À venir en séance 15 : migration vers PostgreSQL avec Alembic.
