import uuid

from sqlalchemy import Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Transformation(Base):
    __tablename__ = "transformations"

    source: Mapped[str] = mapped_column(Text, primary_key=True)
    result: Mapped[str] = mapped_column(Text)


class Payload(Base):
    __tablename__ = "payloads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    output: Mapped[str] = mapped_column(Text)
