from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    #pas besoin de validation grâce à EmailStr
    email: EmailStr = Field(max_length=120)


class UserCreate(UserBase):
    password:str = Field(min_length=8)

class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    image_file: str | None
    #fonction définie dans le modèle ( propriété)
    image_path: str

class UserPrivate(UserPublic):
    email: EmailStr

class UserUpdate(BaseModel):
    username: str | None = Field(default = None, min_length=1, max_length=50)
    #pas besoin de validation grâce à EmailStr
    email: EmailStr | None = Field(default = None,max_length=120)
    image_file: str | None = Field(default=None, min_length=1, max_length=200)

class Token(BaseModel):
    access_token: str
    token_type: str

class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    pass

class PostUpdate(BaseModel):
    #Les 2 attributs sont devenus optionnels, il faut donc une valeur par défaut
    title: str | None= Field(default = None, min_length=1, max_length=100)
    content: str | None= Field(default = None, min_length=1)

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    #réponses qui ne sont pas vues par le client
    id: int
    user_id: int
    #follow ISO 8601
    date_posted: datetime
    author: UserPublic

