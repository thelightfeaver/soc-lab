"""Lógica de negocio del laboratorio (sin dependencias de Qt)."""

import shutil
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path

from peewee import SqliteDatabase, fn

from soclab import flags
from soclab.db import Challenge, Hint, HintReveal, Solve, Submission, utcnow
from soclab.importer import install_challenge
from soclab.manifest import Difficulty, Manifest, ManifestError, discover

SUBMIT_COOLDOWN = timedelta(seconds=2)


class SubmitResult(StrEnum):
    CORRECT = "correct"
    INCORRECT = "incorrect"
    INVALID_FORMAT = "invalid_format"
    ALREADY_SOLVED = "already_solved"
    RATE_LIMITED = "rate_limited"


@dataclass(frozen=True, slots=True)
class DifficultyStats:
    difficulty: Difficulty
    total: int
    solved: int


@dataclass(frozen=True, slots=True)
class Stats:
    total: int
    solved: int
    points_earned: int
    points_available: int
    by_difficulty: tuple[DifficultyStats, ...]

    @property
    def percent(self) -> int:
        return round(100 * self.solved / self.total) if self.total else 0


@dataclass(frozen=True, slots=True)
class ChallengeView:
    """Proyección inmutable de un reto + progreso, pensada para la UI."""

    slug: str
    title: str
    category: str
    difficulty: Difficulty
    points: int
    summary: str
    description: str
    flag_format: str
    author: str
    source: str
    root: Path
    has_container: bool
    solved: bool
    awarded_points: int | None
    attempts: int
    hints: tuple[tuple[int, str | None, int], ...]  # (posición, texto si revelada, coste)

    @property
    def files_dir(self) -> Path:
        return self.root / "files"


class LabService:
    def __init__(self, db: SqliteDatabase, *, clock: Callable[[], datetime] = utcnow) -> None:
        self.db = db
        self.clock = clock

    # ------------------------------------------------------------ sincronización
    def sync(self, manifests: Iterable[Manifest], source: str) -> None:
        """Inserta/actualiza retos conservando el progreso del usuario."""
        with self.db.atomic():
            for m in manifests:
                values = {
                    "title": m.title,
                    "category": m.category,
                    "difficulty": m.difficulty.value,
                    "points": m.points,
                    "summary": m.summary,
                    "description": m.description,
                    "flag_format": m.flag_format,
                    "flag_hash": m.flag_hash,
                    "case_sensitive": m.case_sensitive,
                    "author": m.author,
                    "source": source,
                    "path": str(m.root),
                    "containerfile": m.containerfile,
                    "updated_at": self.clock(),
                }
                challenge = Challenge.get_or_none(Challenge.slug == m.slug)
                if challenge is None:
                    challenge = Challenge.create(slug=m.slug, **values)
                else:
                    Challenge.update(**values).where(Challenge.id == challenge.id).execute()
                self._sync_hints(challenge, m)

    @staticmethod
    def _sync_hints(challenge: Challenge, manifest: Manifest) -> None:
        existing = {h.position: h for h in challenge.hints}
        for position, spec in enumerate(manifest.hints, start=1):
            hint = existing.pop(position, None)
            if hint is None:
                Hint.create(challenge=challenge, position=position, text=spec.text, cost=spec.cost)
            elif (hint.text, hint.cost) != (spec.text, spec.cost):
                Hint.update(text=spec.text, cost=spec.cost).where(Hint.id == hint.id).execute()
        for orphan in existing.values():
            orphan.delete_instance(recursive=True)

    def load_directory(self, root: Path, source: str) -> list[ManifestError]:
        manifests, errors = discover(root)
        self.sync(manifests, source)
        return errors

    def import_challenge(self, source: Path, destination: Path, *, replace: bool = False) -> str:
        reserved = {
            c.slug for c in Challenge.select(Challenge.slug).where(Challenge.source == "builtin")
        }
        manifest = install_challenge(source, destination, reserved_slugs=reserved, replace=replace)
        self.sync([manifest], "imported")
        return manifest.slug

    def delete_imported(self, slug: str) -> None:
        challenge = self._get(slug)
        if challenge.source != "imported":
            raise PermissionError("Solo se pueden eliminar retos importados.")
        root = challenge.root
        challenge.delete_instance(recursive=True)
        if root.is_dir():
            shutil.rmtree(root)

    # ------------------------------------------------------------ consultas
    @staticmethod
    def _get(slug: str) -> Challenge:
        challenge = Challenge.get_or_none(Challenge.slug == slug)
        if challenge is None:
            raise KeyError(f"No existe el reto '{slug}'")
        return challenge

    def _view(self, c: Challenge) -> ChallengeView:
        solve = Solve.get_or_none(Solve.challenge == c)
        revealed = {r.hint_id for r in HintReveal.select().join(Hint).where(Hint.challenge == c)}
        hints = tuple(
            (h.position, h.text if h.id in revealed else None, h.cost)
            for h in c.hints.order_by(Hint.position)
        )
        return ChallengeView(
            slug=c.slug,
            title=c.title,
            category=c.category,
            difficulty=Difficulty(c.difficulty),
            points=c.points,
            summary=c.summary,
            description=c.description,
            flag_format=c.flag_format,
            author=c.author,
            source=c.source,
            root=c.root,
            has_container=bool(c.containerfile),
            solved=solve is not None,
            awarded_points=solve.awarded_points if solve else None,
            attempts=c.submissions.count(),
            hints=hints,
        )

    def get(self, slug: str) -> ChallengeView:
        return self._view(self._get(slug))

    def list(self) -> list[ChallengeView]:
        views = [self._view(c) for c in Challenge.select()]
        return sorted(views, key=lambda v: (v.difficulty.rank, v.slug))

    def categories(self) -> list[str]:
        query = Challenge.select(Challenge.category).distinct().order_by(Challenge.category)
        return [c.category for c in query]

    def stats(self) -> Stats:
        views = self.list()
        by_diff = tuple(
            DifficultyStats(
                difficulty=d,
                total=sum(1 for v in views if v.difficulty is d),
                solved=sum(1 for v in views if v.difficulty is d and v.solved),
            )
            for d in Difficulty
        )
        return Stats(
            total=len(views),
            solved=sum(1 for v in views if v.solved),
            points_earned=sum(v.awarded_points or 0 for v in views),
            points_available=sum(v.points for v in views),
            by_difficulty=by_diff,
        )

    # ------------------------------------------------------------ acciones
    def reveal_hint(self, slug: str, position: int) -> str:
        challenge = self._get(slug)
        hint = Hint.get_or_none((Hint.challenge == challenge) & (Hint.position == position))
        if hint is None:
            raise KeyError(f"El reto '{slug}' no tiene la pista {position}")
        HintReveal.get_or_create(hint=hint, defaults={"revealed_at": self.clock()})
        return hint.text

    def _hint_penalty(self, challenge: Challenge) -> int:
        total = (
            Hint.select(fn.COALESCE(fn.SUM(Hint.cost), 0))
            .join(HintReveal)
            .where(Hint.challenge == challenge)
            .scalar()
        )
        return int(total or 0)

    def submit_flag(self, slug: str, flag: str) -> SubmitResult:
        challenge = self._get(slug)
        if Solve.get_or_none(Solve.challenge == challenge) is not None:
            return SubmitResult.ALREADY_SOLVED
        if not flags.is_valid_format(flag):
            return SubmitResult.INVALID_FORMAT
        now = self.clock()
        last = (
            Submission.select()
            .where((Submission.challenge == challenge) & (~Submission.correct))
            .order_by(Submission.submitted_at.desc())
            .first()
        )
        if last is not None and now - _aware(last.submitted_at) < SUBMIT_COOLDOWN:
            return SubmitResult.RATE_LIMITED
        correct = flags.verify(flag, challenge.flag_hash, case_sensitive=challenge.case_sensitive)
        with self.db.atomic():
            Submission.create(challenge=challenge, submitted_at=now, correct=correct)
            if correct:
                awarded = max(0, challenge.points - self._hint_penalty(challenge))
                Solve.create(challenge=challenge, solved_at=now, awarded_points=awarded)
        return SubmitResult.CORRECT if correct else SubmitResult.INCORRECT

    def reset_progress(self) -> None:
        with self.db.atomic():
            Solve.delete().execute()
            Submission.delete().execute()
            HintReveal.delete().execute()


def _aware(value: datetime | str) -> datetime:
    """SQLite devuelve fechas sin zona; las tratamos como UTC."""
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value
