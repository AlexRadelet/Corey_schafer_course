# Séance 10 — Authentication : Inscription, Connexion et JWT

## Code de cette séance
- [`auth.py`](auth.py) — hachage de mots de passe, création et vérification de tokens JWT
- [`config.py`](config.py) — configuration centralisée via `pydantic-settings` (lit le fichier `.env`)
- [`schemas.py`](schemas.py) — `UserCreate` avec mot de passe, `UserPublic`/`UserPrivate`, `Token`
- [`models.py`](models.py) — ajout du champ `password_hash` sur `User`
- [`routers/users.py`](routers/users.py) — routes `/token`, `/me`, unicité case-insensitive
- [`static/js/auth.js`](static/js/auth.js) — gestion du token côté frontend (localStorage)
- [`templates/register.html`](templates/register.html) — formulaire d'inscription
- [`templates/login.html`](templates/login.html) — formulaire de connexion
- [`templates/layout.html`](templates/layout.html) — navbar mise à jour (Login/Register ou nom d'utilisateur)

## Ce qu'on a fait
- Ajouté le hachage de mots de passe avec **argon2** (via `pwdlib`) — les mots de passe ne sont jamais stockés en clair.
- Implémenté l'authentification **JWT** (JSON Web Token) : login → token → accès aux routes protégées.
- Créé `config.py` pour centraliser la configuration sensible (`SECRET_KEY`, algorithme, durée du token) lue depuis un fichier `.env`.
- Séparé `UserResponse` en deux schémas : `UserPublic` (sans email, pour les données publiques) et `UserPrivate` (avec email, pour l'utilisateur connecté).
- Créé trois nouveaux endpoints : `POST /api/users/token` (login), `GET /api/users/me` (utilisateur courant), et mis à jour `POST /api/users` (inscription avec mot de passe).
- Créé les pages d'inscription et de connexion et mis à jour la navbar.
- Stocké le JWT dans le `localStorage` du navigateur via `auth.js`.

## Points techniques à retenir

### Packages installés

```bash
uv add pwdlib[argon2]   # hachage de mots de passe (argon2 = algorithme recommandé)
uv add pyjwt            # création et vérification de tokens JWT
uv add pydantic-settings # configuration typée depuis .env
```

### `config.py` — configuration centralisée avec `pydantic-settings`

```python
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    secret_key: SecretStr       # lu depuis .env, jamais loggué (SecretStr)
    algorithm: str = "HS256"    # valeur par défaut
    access_token_expire_minutes: int = 30

settings = Settings()
```

- `pydantic-settings` lit automatiquement le fichier `.env` et valide les types.
- `SecretStr` empêche l'affichage accidentel de la valeur dans les logs ou les erreurs.
- Générer une clé secrète robuste : `python -c "import secrets; print(secrets.token_hex(32))"`

Le fichier `.env` (ne jamais committer ce fichier) :
```
SECRET_KEY=<valeur_générée>
```

### `auth.py` — hachage et JWT

```python
from pwdlib import PasswordHash
password_hash = PasswordHash.recommended()  # utilise argon2 par défaut

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return password_hash.verify(plain_password, hashed_password)
```

```python
import jwt

def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key.get_secret_value(), algorithm=settings.algorithm)

def verify_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.secret_key.get_secret_value(),
                             algorithms=[settings.algorithm], options={"require": ["exp", "sub"]})
        return payload.get("sub")
    except jwt.InvalidTokenError:
        return None
```

**Structure d'un JWT** : trois parties encodées en base64 séparées par des `.`
- **Header** : algorithme utilisé (`HS256`)
- **Payload** : données (ici `sub` = user id, `exp` = expiration)
- **Signature** : HMAC du header + payload avec la `SECRET_KEY` — garantit l'intégrité

### Schémas : `UserPublic` vs `UserPrivate`

```python
class UserPublic(BaseModel):        # données visibles par tous
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    image_file: str | None
    image_path: str                 # @property du modèle SQLAlchemy

class UserPrivate(UserPublic):      # données de l'utilisateur connecté uniquement
    email: EmailStr                 # l'email n'est pas public

class UserCreate(UserBase):
    password: str = Field(min_length=8)  # reçu à l'inscription, jamais stocké tel quel

class Token(BaseModel):
    access_token: str
    token_type: str                 # toujours "bearer"
```

`UserPublic` est utilisé dans `PostResponse.author` — l'email de l'auteur n'est pas exposé dans les listes de posts.

### Endpoints d'authentification

**Inscription** — `POST /api/users` :
```python
new_user = models.User(
    username=user.username,
    email=user.email.lower(),           # stocké en minuscules
    password_hash=hash_password(user.password),
)
```

**Login** — `POST /api/users/token` :
```python
@router.post("/token", response_model=Token)
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], ...):
    # OAuth2PasswordRequestForm utilise le champ "username" — on le traite comme un email
    result = await db.execute(
        select(models.User).where(func.lower(models.User.email) == form_data.username.lower())
    )
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password",
                            headers={"WWW-Authenticate": "Bearer"})
    access_token = create_access_token(data={"sub": str(user.id)}, ...)
    return Token(access_token=access_token, token_type="bearer")
```

⚠️ Ne pas révéler si c'est l'email ou le mot de passe qui est incorrect — message générique volontaire.

**Utilisateur courant** — `GET /api/users/me` :
```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")

@router.get("/me", response_model=UserPrivate)
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], ...):
    user_id = verify_access_token(token)
    # ... valide et retourne l'utilisateur
```

⚠️ `/me` doit être déclaré **avant** `/{user_id}` dans le router — sinon FastAPI interpréterait `/me` comme un `user_id` entier et renverrait une erreur de validation.

### `OAuth2PasswordBearer` et le bouton "Authorize" dans Swagger

```python
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/users/token")
```

Ce simple déclarateur fait apparaître automatiquement le bouton **"Authorize"** dans `/docs`, permettant de se connecter et de tester les routes protégées directement depuis la documentation.

### Unicité case-insensitive avec `func.lower()`

```python
from sqlalchemy import func

# Cherche "Alice", "alice", "ALICE" → même résultat
result = await db.execute(
    select(models.User).where(func.lower(models.User.username) == user.username.lower())
)
```

### `auth.js` — gestion du token côté frontend

```javascript
export function setToken(token) { localStorage.setItem("access_token", token); }
export function getToken() { return localStorage.getItem("access_token"); }
export function logout() {
    localStorage.removeItem("access_token");
    currentUser = null;
    window.location.href = "/";
}

export async function getCurrentUser() {
    // Cache en mémoire + déduplique les appels concurrents
    if (currentUser) return currentUser;
    const token = getToken();
    if (!token) return null;
    const response = await fetch("/api/users/me", {
        headers: { Authorization: `Bearer ${token}` }
    });
    if (response.ok) { currentUser = await response.json(); return currentUser; }
    localStorage.removeItem("access_token");
    return null;
}
```

Le token est stocké dans `localStorage` (persiste entre sessions). `getCurrentUser()` met en cache le résultat et évite les appels dupliqués si plusieurs scripts l'appellent en parallèle.

## Remarques / questions à creuser
- `.env` est dans `.gitignore` — ne jamais le committer. En prod, les variables d'environnement sont injectées par l'infrastructure (Docker, Heroku, etc.), pas lues depuis un fichier.
- L'API accepte encore n'importe qui pour modifier/supprimer les posts — ce sera corrigé en séance 11 (Authorization : protection des routes).
- `argon2` est plus lent que `bcrypt` volontairement — c'est une résistance aux attaques par force brute. La lenteur est une feature, pas un bug.
- Le token JWT est visible dans les DevTools (onglet Application → Local Storage). En production, on préfère parfois les cookies `HttpOnly` pour éviter les attaques XSS, mais ça complexifie la gestion CSRF.
