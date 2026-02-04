from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator


class Entity(str, Enum):
    video = "video"
    video_snapshots = "video_snapshots"


class Operation(str, Enum):
    sum = "sum"
    count_ = "count"


class LogicalOp(str, Enum):
    and_ = "and"
    or_ = "or"


class CompareOp(str, Enum):
    eq = "="
    ne = "!="
    gt = ">"
    gte = ">="
    lt = "<"
    lte = "<="


class Condition(BaseModel):
    type: str = Field("condition", frozen=True)
    field: str
    operator: CompareOp
    value: int | str


class ConditionGroup(BaseModel):
    type: str = Field("group", frozen=True)
    op: LogicalOp
    conditions: list[FilterNode]

    @field_validator("conditions")
    @classmethod
    def conditions_not_empty(cls, v: list[FilterNode]):
        if not v:
            raise ValueError("conditions must not be empty")
        return v


class DateFilter(BaseModel):
    from_: datetime = Field(alias="from")
    to: datetime

    @model_validator(mode="after")
    def validate_range(self):
        if self.from_ > self.to:
            raise ValueError("date_filter.from must be <= date_filter.to")
        return self


FilterNode = Condition | ConditionGroup


VIDEO_FIELDS = {
    "id",
    "creator_id",
    "video_created_at",
    "views_count",
    "likes_count",
    "comments_count",
    "reports_count",
}

SNAPSHOT_FIELDS = {
    "id",
    "video_id",
    "views_count",
    "likes_count",
    "comments_count",
    "reports_count",
    "delta_views_count",
    "delta_likes_count",
    "delta_comments_count",
    "delta_reports_count",
    "created_at",
}


class Answer(BaseModel):
    entity: Entity
    operation: Operation
    field: str
    distinct: bool
    where: FilterNode | None = None
    date_filter: DateFilter | None = None

    @model_validator(mode="after")
    def validate_plan(self):
        allowed_fields = (
            VIDEO_FIELDS if self.entity == Entity.video else SNAPSHOT_FIELDS
        )

        if self.field not in allowed_fields:
            raise ValueError(
                f"field '{self.field}' not allowed for entity '{self.entity}'"
            )

        if self.field.startswith("delta_") and self.entity != Entity.video_snapshots:
            raise ValueError("delta_* fields allowed only for video_snapshots")

        if self.operation == Operation.count and self.field.startswith("delta_"):
            if not (self.distinct and self.field == "video_id"):
                raise ValueError(
                    "count with delta_* allowed only for DISTINCT video_id"
                )

        def validate_filter(node: FilterNode):
            if isinstance(node, Condition):
                if node.field not in allowed_fields:
                    raise ValueError(
                        f"filter field '{node.field}' not allowed for entity '{self.entity}'"
                    )
            else:
                for c in node.conditions:
                    validate_filter(c)

        if self.where:
            validate_filter(self.where)

        return self
