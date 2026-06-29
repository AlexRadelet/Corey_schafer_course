from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

class UserBase(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    #pas besoin de validation grâce à EmailStr
    email: EmailStr = Field(max_length=120)

class UserCreate(UserBase):
    pass

class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    image_file: str | None
    #fonction définie dans le modèle ( propriété)
    image_path: str



class PostBase(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1)


class PostCreate(PostBase):
    user_id :int #temporary

class PostResponse(PostBase):
    model_config = ConfigDict(from_attributes=True)

    #réponses qui ne sont pas vues par le client
    id: int
    user_id: int
    #follow ISO 8601
    date_posted: datetime
    author: UserResponse

