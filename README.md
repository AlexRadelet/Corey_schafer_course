# Corey Schafer â€” Cours FastAPI

Suivi de la sÃ©rie de cours FastAPI de Corey Schafer : code et notes, sÃ©ance par sÃ©ance, pour pouvoir y replonger rapidement en cas de besoin.

## Sommaire des sÃ©ances

| SÃ©ance | Sujet | Notes | Code |
|---|---|---|---|
| 01 | Setup du projet, premiÃ¨re route API, HTML vs JSON, doc auto-gÃ©nÃ©rÃ©e | [NOTES.md](seance-01/NOTES.md) | [main.py](seance-01/main.py) |
| 02 | Frontend HTML avec templates Jinja2, fichiers statiques, hÃ©ritage de templates | [NOTES.md](seance-02/NOTES.md) | [main.py](seance-02/main.py) |
| 03 | Path parameters, validation automatique, gestion d'erreurs (HTTPException, exception handlers) | [NOTES.md](seance-03/NOTES.md) | [main.py](seance-03/main.py) |
| 04 | Pydantic Schemas : validation des requÃªtes/rÃ©ponses, response_model, crÃ©ation de posts | [NOTES.md](seance-04/NOTES.md) | [main.py](seance-04/main.py) |
| 05 | Base de donnÃ©es avec SQLAlchemy : modÃ¨les, relations, dependency injection | [NOTES.md](seance-05/NOTES.md) | [main.py](seance-05/main.py) |
| 06 | CRUD complet : PUT/PATCH/DELETE, mise Ã  jour partielle, cascade delete | [NOTES.md](seance-06/NOTES.md) | [main.py](seance-06/main.py) |
| 07 | Sync vs Async : conversion de l'app en asynchrone, eager loading | [NOTES.md](seance-07/NOTES.md) | [main.py](seance-07/main.py) |
| 08 | Routers : organisation des routes en modules avec APIRouter | [NOTES.md](seance-08/NOTES.md) | [main.py](seance-08/main.py) |
| 09 | Frontend Forms : formulaires Bootstrap connectÃ©s Ã  l'API via JavaScript | [NOTES.md](seance-09/NOTES.md) | [main.py](seance-09/main.py) |
| 10 | Authentication : inscription, connexion et JWT (argon2 + pyjwt) | [NOTES.md](seance-10/NOTES.md) | [main.py](seance-10/main.py) |
| 11 | Authorization : protection des routes et vÃ©rification du propriÃ©taire | [NOTES.md](seance-11/NOTES.md) | [main.py](seance-11/main.py) |
| 12 | File Uploads : traitement d'images avec Pillow, stockage et sÃ©curitÃ© | [NOTES.md](seance-12/NOTES.md) | [main.py](seance-12/main.py) |
| 13 | Pagination : chargement des données par pages avec query parameters | [NOTES.md](seance-13/NOTES.md) | [main.py](seance-13/main.py) |
| 14 | Réinitialisation de mot de passe : email, tokens et background tasks | [NOTES.md](seance-14/NOTES.md) | [main.py](seance-14/main.py) |

## Installation

Le projet utilise [uv](https://docs.astral.sh/uv/) comme gestionnaire de paquets.

```bash
uv sync
```

## Lancer le projet (Ã  la racine)

Mode dev (auto-reload) :
```bash
uv run fastapi dev main.py
```

Mode prod :
```bash
uv run fastapi run main.py
```

Documentation auto-gÃ©nÃ©rÃ©e une fois le serveur lancÃ© :
- Swagger UI : `http://localhost:<port>/docs`
- ReDoc : `http://localhost:<port>/redoc`

## Organisation du repo

Chaque sÃ©ance a son propre dossier `seance-XX/` contenant :
- une copie du code Ã©crit pendant la sÃ©ance,
- un fichier `NOTES.md` avec ce qui a Ã©tÃ© appris, les commandes utiles, et mes remarques.

Le fichier `main.py` Ã  la racine contient toujours la version la plus Ã  jour du code (celle avec laquelle on continue de coder), tandis que les dossiers `seance-XX/` servent d'archive figÃ©e de chaque Ã©tape.

