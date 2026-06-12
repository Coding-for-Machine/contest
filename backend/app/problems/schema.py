from ninja import Schema
from typing import Optional, List
from enum import Enum


class DifficultyEnum(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class CategoryOut(Schema):
    id: int
    name: str
    slug: str


class TagOut(Schema):
    id: int
    name: str


class ProblemListOut(Schema):
    id: int
    title: str
    slug: str
    difficulty: DifficultyEnum
    category: Optional[CategoryOut] = None
    xp: int
    acceptance_rate: float
    tags: List[TagOut] = []
    is_solved: bool
    submission_count: int
    has_video: bool


class ProblemDetailOut(Schema):
    id: int
    title: str
    slug: str
    difficulty: DifficultyEnum
    category: Optional[CategoryOut] = None
    xp: int
    acceptance_rate: float
    tags: List[TagOut] = []
    is_solved: bool
    submission_count: int
    has_video: bool
    description: str
    examples: Optional[str] = None
    constraints: Optional[str] = None
    hints: Optional[str] = None


class CategoryListOut(Schema):
    id: int
    name: str
    slug: str
    problem_count: int


class TagListOut(Schema):
    id: int
    name: str
    problem_count: int


class ProblemFilters(Schema):
    difficulty: Optional[DifficultyEnum] = None
    category_id: Optional[int] = None
    tag_id: Optional[int] = None
    search: Optional[str] = None
    solved: Optional[bool] = None