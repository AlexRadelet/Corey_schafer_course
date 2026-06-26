# Corey Schafer — Cours FastAPI

Suivi de la série de cours FastAPI de Corey Schafer : code et notes, séance par séance, pour pouvoir y replonger rapidement en cas de besoin.

## Sommaire des séances

| Séance | Sujet | Notes | Code |
|---|---|---|---|
| 01 | Setup du projet, première route API, HTML vs JSON, doc auto-générée | [NOTES.md](seance-01/NOTES.md) | [main.py](seance-01/main.py) |
| 02 | Frontend HTML avec templates Jinja2, fichiers statiques, héritage de templates | [NOTES.md](seance-02/NOTES.md) | [main.py](seance-02/main.py) |
| 03 | Path parameters, validation automatique, gestion d'erreurs (HTTPException, exception handlers) | [NOTES.md](seance-03/NOTES.md) | [main.py](seance-03/main.py) |

## Installation

Le projet utilise [uv](https://docs.astral.sh/uv/) comme gestionnaire de paquets.

```bash
uv sync
```

## Lancer le projet (à la racine)

Mode dev (auto-reload) :
```bash
uv run fastapi dev main.py
```

Mode prod :
```bash
uv run fastapi run main.py
```

Documentation auto-générée une fois le serveur lancé :
- Swagger UI : `http://localhost:<port>/docs`
- ReDoc : `http://localhost:<port>/redoc`

## Organisation du repo

Chaque séance a son propre dossier `seance-XX/` contenant :
- une copie du code écrit pendant la séance,
- un fichier `NOTES.md` avec ce qui a été appris, les commandes utiles, et mes remarques.

Le fichier `main.py` à la racine contient toujours la version la plus à jour du code (celle avec laquelle on continue de coder), tandis que les dossiers `seance-XX/` servent d'archive figée de chaque étape.
