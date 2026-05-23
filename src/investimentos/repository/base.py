from typing import Generic, TypeVar
from sqlalchemy.orm import Session

T = TypeVar("T")

class BaseRepository(Generic[T]):
    def __init__(self, session: Session):
        self.session = session

    def _commit(self):
        self.session.commit()
