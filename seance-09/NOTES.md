# Séance 09 — Frontend Forms : Connexion JavaScript ↔ API

## Code de cette séance
- [`templates/layout.html`](templates/layout.html) — 3 modals Bootstrap ajoutés : Create Post, Success, Error + script JS de création
- [`templates/post.html`](templates/post.html) — modals Edit et Delete + script JS de mise à jour et suppression
- [`static/js/utils.js`](static/js/utils.js) — fonctions utilitaires partagées : `getErrorMessage`, `showModal`, `hideModal`
- [`main.py`](main.py) — tri par date décroissante sur la route home et user_posts
- [`routers/posts.py`](routers/posts.py) — tri par date décroissante sur `GET /api/posts`
- [`routers/users.py`](routers/users.py) — tri par date décroissante sur `GET /api/users/{user_id}/posts`

## Ce qu'on a fait
- Branché le frontend HTML aux routes API via JavaScript (fetch API) — sans rechargement de page.
- Créé trois fonctionnalités utilisateur : **créer** un post (modal dans le layout), **éditer** et **supprimer** un post (modals dans `post.html`).
- Ajouté des modals Bootstrap de **succès** et d'**erreur** réutilisables sur toutes les pages (dans `layout.html`).
- Centralisé les utilitaires JS communs dans `static/js/utils.js` (module ES6, importé là où nécessaire).
- Ajouté un tri des posts par **date décroissante** (les plus récents en premier) dans toutes les routes qui renvoient des listes de posts.
- `user_id` hardcodé à `1` pour l'instant — remplacé par l'authentification réelle en séance 10.

## Points techniques à retenir

### Architecture : logique métier dans le backend

Le tri des posts par date se fait **côté backend** (SQLAlchemy), pas côté JavaScript :

```python
# routers/posts.py
result = await db.execute(
    select(models.Post)
    .options(selectinload(models.Post.author))
    .order_by(models.Post.date_posted.desc()),
)
```

Règle générale : tout ce qui concerne les données (tri, filtrage, calcul) appartient au backend. Le JavaScript frontend ne gère que l'**interaction utilisateur** (soumettre un formulaire, afficher un message).

### `static/js/utils.js` — module ES6 partagé

```javascript
// utils.js
export function getErrorMessage(error) {
  if (typeof error.detail === "string") return error.detail;
  else if (Array.isArray(error.detail)) return error.detail.map(e => e.msg).join(". ");
  return "An error occurred. Please try again.";
}

export function showModal(modalId) {
  const modal = bootstrap.Modal.getOrCreateInstance(document.getElementById(modalId));
  modal.show();
  return modal;
}

export function hideModal(modalId) {
  const modal = bootstrap.Modal.getInstance(document.getElementById(modalId));
  if (modal) modal.hide();
}
```

Importé dans chaque script avec `type="module"` :
```html
<script type="module">
  import { getErrorMessage, hideModal, showModal } from "/static/js/utils.js";
</script>
```

### Modals Bootstrap dans `layout.html`

Trois modals définis une fois dans le layout, accessibles sur toutes les pages :
- **`#createPostModal`** : formulaire de création de post
- **`#successModal`** : confirmation de succès (message dynamique via `#successMessage`)
- **`#errorModal`** : affichage d'erreur (message dynamique via `#errorMessage`)

La page `post.html` ajoute ses propres modals (`#editModal`, `#deleteModal`) dans son bloc `{% block content %}`.

### Pattern fetch API : POST pour créer un post

```javascript
const formData = new FormData(createForm);
const postData = Object.fromEntries(formData.entries());
postData.user_id = 1; // TEMPORARY - remplacé par auth en séance 10

const response = await fetch("/api/posts", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(postData),
});

if (response.ok) {
  const data = await response.json();
  // afficher succès...
} else {
  const error = await response.json();
  document.getElementById("errorMessage").textContent = getErrorMessage(error);
  showModal("errorModal");
}
```

### Pattern fetch API : PATCH pour éditer un post

```javascript
// post_id vient du template Jinja2, résolu côté serveur avant envoi au navigateur
const postId = {{ post.id }};

const response = await fetch(`/api/posts/${postId}`, {
  method: "PATCH",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(postData), // seulement title et content
});
```

### Pattern fetch API : DELETE

```javascript
const response = await fetch(`/api/posts/${postId}`, { method: "DELETE" });

if (response.status === 204) {
  // 204 = No Content = succès, pas de corps JSON à lire
  window.location.href = "/";
}
```

⚠️ On vérifie `response.status === 204` (et non `response.ok`) car `response.ok` est `true` pour tous les 2xx, mais un DELETE réussi ne renvoie pas de JSON — tenter `response.json()` sur un 204 lèverait une erreur.

### Enchaîner modals : hide → show

Quand une action déclenche un modal (ex: Edit) puis un autre (Success ou Error), il faut fermer le premier avant d'ouvrir le second :

```javascript
hideModal("editModal");
showModal("successModal");
```

Pour recharger la page seulement après fermeture du modal de succès :
```javascript
document.getElementById("successModal").addEventListener(
  "hidden.bs.modal",
  () => { window.location.reload(); },
  { once: true }, // important : écouter une seule fois pour éviter les doublons
);
```

### Faux positif PyCharm : `{{ post.id }}` dans un `<script>`

```javascript
const postId = {{ post.id }};
```

PyCharm signale une erreur de syntaxe JavaScript sur cette ligne car il voit le fichier brut, sans comprendre que `{{ post.id }}` est une **expression Jinja2** résolue côté serveur avant que le navigateur ne reçoive la page. Au moment de l'exécution, le navigateur voit simplement `const postId = 42;` — syntaxe JavaScript parfaitement valide. C'est un faux positif de l'IDE, le code fonctionne correctement.

## Remarques / questions à creuser
- `user_id = 1` est hardcodé dans le JavaScript en attendant l'authentification (séance 10). En prod, cette valeur viendrait du token JWT de l'utilisateur connecté.
- Le `{% block scripts %}{% endblock scripts %}` en bas de `layout.html` permet aux pages filles d'injecter leur propre JavaScript après le script du layout — `post.html` l'utilise pour ses handlers edit/delete spécifiques à la page.
- `{ once: true }` sur l'event listener du modal succès est important : sans ça, chaque action successive sur la page enregistrerait un nouveau listener, et le rechargement se déclencherait plusieurs fois.
