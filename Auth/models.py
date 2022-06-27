from pydantic import BaseModel
from typing import Union, List

class Token(BaseModel):
    access_token: str
    token_type: str

class UserToken(BaseModel):
    access_token: str
class TokenData(BaseModel):
    username: Union[str, None] = None
    
class User(BaseModel):
    username: str

class UserInDB(User):
    hashed_password: str
