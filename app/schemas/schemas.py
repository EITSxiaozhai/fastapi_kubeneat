from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    turnstile_token: str | None = Field(default=None, max_length=2048)


class LoginResponse(BaseModel):
    status: str
    type: str = "account"
    currentAuthority: str


class CurrentUserData(BaseModel):
    name: str
    avatar: str = ""
    userid: str
    email: str | None = None
    access: str


class CurrentUserResponse(BaseModel):
    success: bool = True
    data: CurrentUserData


class TaskCreate(BaseModel):
    task_id: str
    original_filename: str = Field(min_length=1, max_length=255)
    submission_type: str = Field(pattern="^(file|manual)$")
    user_id: str | None = None


class TaskRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    task_id: str
    original_filename: str
    created_at: datetime
    submission_type: str
