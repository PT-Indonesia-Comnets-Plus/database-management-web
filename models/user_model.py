from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime


class User(BaseModel):
    uid: str
    email: str
    username: str
    role: Literal["Admin", "User"]
    status: Literal["Pending", "Verified"]
    created_at: str  # pakai ISO string atau bisa juga pakai datetime

    # Optional tambahan
    verified: Optional[bool] = None
