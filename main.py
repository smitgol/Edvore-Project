from fastapi import Depends, FastAPI, HTTPException, Request, status, WebSocket, WebSocketDisconnect, Header
from fastapi.responses import HTMLResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from Auth.models import Token, UserInDB, User, UserToken
from Auth.jwt_handler import authenticate_user, fake_users_db, create_access_token, get_password_hash, get_current_active_user, get_current_user, delete_other_session
from datetime import timedelta
from typing import List, Optional

ACCESS_TOKEN_EXPIRE_MINUTES = 5

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <h2>Your ID: <span id="ws-id"></span></h2>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" autocomplete="off"/>
            <button>Send</button>
        </form>
        <ul id='messages'>
        </ul>
        <script>
            var client_id = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzbWl0IiwiZXhwIjoxNjU2MTA0MjYwfQ.RFRnROzpC-P6IwyuNUq8NUhoW6Lq5aqT_QPHKrPkw4U'
            document.querySelector("#ws-id").textContent = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJzbWl0IiwiZXhwIjoxNjU2MTA0MjYwfQ.RFRnROzpC-P6IwyuNUq8NUhoW6Lq5aqT_QPHKrPkw4U';
            var ws = new WebSocket(`ws://localhost:8000/ws/${client_id}`);
            ws.onmessage = function(event) {
                var messages = document.getElementById('messages')
                var message = document.createElement('li')
                var content = document.createTextNode(event.data)
                message.appendChild(content)
                messages.appendChild(message)
            };
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/")
async def get():
    return HTMLResponse(html)

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post('/signup')
def create_user(formdata:UserInDB):
    user_obj = {'username':formdata.username, 'hashed_password':get_password_hash(formdata.hashed_password)}
    fake_users_db[formdata.username] = user_obj
    return {'status': "user created"}

@app.websocket("/ws/{token}")
async def websocket_endpoint(websocket: WebSocket, token: str):
    await manager.connect(websocket)
    try:
        while True:
            user_auth = await get_current_user(token)
            data = await websocket.receive_text()
            await manager.broadcast(f"Client #{user_auth.username} says: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{user_auth.username} left the chat")

@app.get("/clear_sessions")
def remove_sessions(user: User=Depends(get_current_active_user), Authorization: Optional[str] = Header(default=None)):
    delete_other_session(user.username, Authorization.split(' ')[1])
    return {"status": "Other session deleted"}
