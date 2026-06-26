from fastapi import FastAPI, Request
#On utilise plus HTMLResponse, jinja2 est mieux
#from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
#On dit ou se trouvent les templates
templates = Jinja2Templates(directory="templates")

posts: list[dict] = [
    {
        "id": 1,
        "author": "Corey Schafer",
        "title": "FastAPI is Awesome",
        "content": "This framework is really easy to use and super fast.",
        "date_posted": "April 20, 2025",
    },
    {
        "id": 2,
        "author": "Jane Doe",
        "title": "Python is Great for Web Development",
        "content": "Python is a great language for web development, and FastAPI makes it even better.",
        "date_posted": "April 21, 2025",
    },
]

@app.get("/", include_in_schema = False, name="home")
@app.get("/posts", include_in_schema = False , name="posts")
#jinja2 a besoin qu'on passe une request dans la fonction
def home(request: Request):
    #get the title of first post
    #on lui passe posts pour que le template ait accès aux données
    return templates.TemplateResponse(
        request, "home.html",
        {"posts": posts, "title": "Home"},
    )


@app.get("/api/posts")
def get_posts():
    return posts


