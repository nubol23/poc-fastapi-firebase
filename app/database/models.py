import orm
import enum
from app.database import models


class Role(enum.Enum):
    ADMIN = 1
    MEMBER = 2


class User(orm.Model):
    tablename = "user"
    registry = models
    fields = {
        "id": orm.Integer(primary_key=True),
        "firebase_id": orm.String(max_length=50),
        "role": orm.Enum(Role),
        "email": orm.String(max_length=255),
        "name": orm.String(max_length=255, allow_blank=True),
    }
