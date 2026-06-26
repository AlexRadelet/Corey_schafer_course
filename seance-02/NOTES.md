# Séance 02 — HTML Frontend for Your API : Jinja2 Templates

## Code de la séance
- [`main.py`](main.py)
- [`templates/layout.html`](templates/layout.html) — template "mère" (layout commun à toutes les pages)
- [`templates/home.html`](templates/home.html) — template "fille" qui hérite du layout
- Fichiers statiques (CSS, JS, icônes, images) : voir [`static/`](../static) à la racine du repo — ils sont communs à tout le projet et ne sont donc pas dupliqués séance par séance.

## Ce qu'on a fait
- Remplacement du HTML codé en dur en Python (`HTMLResponse`, vu en séance 1) par des **templates Jinja2** : plus maintenable dès que le projet grossit.
- Jinja2 est déjà inclus avec FastAPI (`fastapi[standard]`) — c'est le moteur de templates utilisé par défaut (le même que Flask). Sinon : `uv add jinja2`.
- Mise en place de `Jinja2Templates(directory="templates")` et `app.mount("/static", StaticFiles(directory="static"), name="static")` pour servir les fichiers statiques (CSS, JS, images, icônes — tout ce qui ne change pas dynamiquement).
- Passage des données (`posts`) au template via le contexte de `TemplateResponse`, pour que le HTML reste dynamique.
- Mise en place de l'**héritage de templates** (`layout.html` + `home.html`) pour éviter de réécrire la structure commune (header, footer, styles) sur chaque page.
- Intégration de Bootstrap (fichiers de template fournis par Corey Schafer) pour le style.
- Utilisation de `url_for(...)` pour générer les URLs (routes ET fichiers statiques) plutôt que de les écrire en dur — si les routes changent, tout se met à jour automatiquement.

## Points techniques à retenir

### Une route qui rend un template
```python
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/", include_in_schema=False, name="home")
def home(request: Request):
    return templates.TemplateResponse(
        request, "home.html",
        {"posts": posts, "title": "Home"},
    )
```
- Jinja2 a besoin qu'on lui passe l'objet `request` dans la fonction de route — c'est obligatoire pour `TemplateResponse`.
- Donner un `name=` à la route (ex: `name="home"`) permet ensuite d'utiliser `url_for('home')` dans les templates au lieu d'écrire l'URL en dur.

### Boucler sur les données dans un template
```jinja
{% for post in posts %}
  <h2>{{ post.title }}</h2>
  <p>{{ post.content }}</p>
{% endfor %}
```
Jinja2 permet d'écrire `post.title` même si `post` est un dictionnaire Python — l'accès à une clé fonctionne aussi avec la notation pointée.

### Condition dans un template
```jinja
{% if title %}
  FastAPI Blog - {{ title }}
{% else %}
  FastAPI Blog
{% endif %}
```

### Héritage de templates
Le fichier "mère" (`layout.html`) définit un bloc que les fichiers "filles" viennent remplir :
```jinja
{# layout.html #}
{% block content %}
{% endblock content %}
```
```jinja
{# home.html #}
{% extends "layout.html" %}
{% block content %}
  {% for post in posts %}
    <h2>{{ post.title }}</h2>
    <p>{{ post.content }}</p>
  {% endfor %}
{% endblock content %}
```

### `url_for` : deux usages
- Navigation vers une route : `{{ url_for('home') }}` (utilise le `name=` défini dans le décorateur `@app.get`).
- Fichier statique : `{{ url_for('static', path='css/main.css') }}`.

⚠️ **Piège à éviter (rencontré pendant cette séance) :** dans un attribut HTML déjà délimité par des guillemets doubles (`href="..."`), il faut utiliser des guillemets **simples** à l'intérieur de l'appel Jinja, sinon le HTML est invalide (PyCharm/l'IDE le signale comme erreur, même si le rendu final fonctionne grâce à Jinja) :
```html
<!-- ❌ invalide : les guillemets doubles internes ferment l'attribut trop tôt -->
<a href="{{ url_for("home") }}">Home</a>

<!-- ✅ correct -->
<a href="{{ url_for('home') }}">Home</a>
```

## Remarques / questions à creuser
- Les fichiers statiques (CSS, JS, icônes, polices) sont à part : ils ne changent pas dynamiquement, donc on les sert avec `StaticFiles` plutôt que via Jinja2.
- Il existe 2 grandes catégories d'URL dans ce projet : les routes de navigation (`url_for('nom_de_route')`) et les fichiers statiques (`url_for('static', path=...)`). Bien faire la distinction.
- À creuser en séance 3 : la gestion des paramètres dans l'URL (path parameters), la validation et la gestion des erreurs.
