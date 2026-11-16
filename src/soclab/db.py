"""Modelos peewee sobre SQLite."""

from datetime import UTC, datetime
from pathlib import Path

from peewee import (
    BooleanField,
    CharField,
    DatabaseProxy,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    Model,
    SqliteDatabase,
    TextField,
)

database_proxy = DatabaseProxy()


def utcnow() -> datetime:
    return datetime.now(UTC)


class BaseModel(Model):
    class Meta:
        database = database_proxy


class Challenge(BaseModel):
    slug = CharField(max_length=64, unique=True)
    title = CharField(max_length=120)
    category = CharField(max_length=60, index=True)
    difficulty = CharField(max_length=16, index=True)
    points = IntegerField()
    summary = CharField(max_length=240)
    description = TextField()
    flag_format = CharField(max_length=120)
    flag_hash = CharField(max_length=200)
    case_sensitive = BooleanField(default=False)
    author = CharField(max_length=80)
    source = CharField(max_length=16, choices=[("builtin", "builtin"), ("imported", "imported")])
    path = TextField()
    containerfile = CharField(max_length=255, null=True)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)

    @property
    def root(self) -> Path:
        return Path(self.path)


class Hint(BaseModel):
    challenge = ForeignKeyField(Challenge, backref="hints", on_delete="CASCADE")
    position = IntegerField()
    text = TextField()
    cost = IntegerField()

    class Meta:
        indexes = ((("challenge", "position"), True),)


class HintReveal(BaseModel):
    hint = ForeignKeyField(Hint, backref="reveals", unique=True, on_delete="CASCADE")
    revealed_at = DateTimeField(default=utcnow)


class Submission(BaseModel):
    """Intento de flag. No se guarda el valor enviado, solo si fue correcto."""

    challenge = ForeignKeyField(Challenge, backref="submissions", on_delete="CASCADE")
    submitted_at = DateTimeField(default=utcnow, index=True)
    correct = BooleanField()


class Solve(BaseModel):
    challenge = ForeignKeyField(Challenge, backref="solve", unique=True, on_delete="CASCADE")
    solved_at = DateTimeField(default=utcnow)
    awarded_points = IntegerField()


MODELS = (Challenge, Hint, HintReveal, Submission, Solve)


def init_database(path: Path | str) -> SqliteDatabase:
    """Abre (o crea) la base de datos y su esquema."""
    db = SqliteDatabase(
        str(path),
        pragmas={"foreign_keys": 1, "journal_mode": "wal", "synchronous": "normal"},
    )
    database_proxy.initialize(db)
    db.connect(reuse_if_open=True)
    db.create_tables(MODELS, safe=True)
    return db
