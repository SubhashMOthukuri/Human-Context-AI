from enum import IntEnum

from pydantic import BaseModel, Field


class EvidenceLevel(IntEnum):
    """Handbook Volume 1, Ch. 6 — Evidence Hierarchy.

    Every claim the engine produces is tagged with the weakest level it
    actually rests on, not the strongest level available anywhere.
    """

    DIRECT = 1  # letters, interviews, journals, footage
    HISTORICAL_RECORD = 2  # official records, verified secondary sources
    CONTEMPORARY_OBSERVATION = 3  # secondhand accounts, later biographies
    AI_INFERENCE = 4  # the model's own inference from the above


class SourceRef(BaseModel):
    title: str
    url: str | None = None  # family-provided sources (a memory, a letter) have no URL


class EvidencedClaim(BaseModel):
    claim: str
    evidence_level: EvidenceLevel
    sources: list[SourceRef] = Field(default_factory=list)
    uncertainty_note: str | None = None


class TimelineEvent(BaseModel):
    date_label: str
    title: str
    description: str
    evidence: EvidencedClaim


class EnvironmentContext(BaseModel):
    place: str
    period: str
    political_climate: str | None = None
    economic_conditions: str | None = None
    technology_available: str | None = None
    culture_and_norms: str | None = None
    evidence: EvidencedClaim


class Relationship(BaseModel):
    name: str
    relation_type: str  # e.g. "Mentored By", "Competed With", "Inspired By"
    description: str
    evidence: EvidencedClaim


class DecisionAnalysis(BaseModel):
    """The actual unit of analysis. Not a trait — a specific decision,
    split into the reasoning that produced it and the behavior that
    carried it out, which is where a thinking pattern actually lives."""

    decision: str  # the specific choice, concretely
    situation: str  # the pressure/constraint/information at the moment of choice
    decision_making_style: str  # HOW the choice was reached — process, not outcome
    execution_style: str  # HOW it was carried out once decided
    thinking_pattern: str  # a specific mechanism this reveals, named for this person
    pattern_strength: int  # 1-10 — how strongly/consistently this recurs elsewhere
    evidence: EvidencedClaim


class DimensionDefinition(BaseModel):
    """A recurring mechanism observed across 2+ decisions — not asserted
    from a single instance. Named specifically for this person, never a
    generic personality-test label."""

    name: str
    description: str


class DimensionScore(BaseModel):
    dimension: str
    score: int  # 1-10
    justification: str
    evidence: EvidencedClaim


class LifeStage(BaseModel):
    """Handbook Volume 1, Ch. 7 — Personality Modeling, made concrete: a
    thinking pattern is a hypothesis inferred from actual decisions, not
    an abstract trait floating free of what the person did."""

    stage_label: str
    date_range: str
    decisions: list[DecisionAnalysis] = Field(default_factory=list)


class TrajectoryPoint(BaseModel):
    stage_label: str
    date_range: str
    score: int  # 1-10
    note: str
    evidence: EvidencedClaim


class DimensionTrajectory(BaseModel):
    """One line on the trajectory chart: how strongly a `dimensions` entry
    showed up at each life stage, in order — the rise/fall over time."""

    dimension: str
    points: list[TrajectoryPoint] = Field(default_factory=list)


class PatternProfile(BaseModel):
    dimensions: list[DimensionDefinition] = Field(default_factory=list)
    overall_scores: list[DimensionScore] = Field(default_factory=list)
    stages: list[LifeStage] = Field(default_factory=list)
    trajectories: list[DimensionTrajectory] = Field(default_factory=list)


class PersonProfile(BaseModel):
    name: str
    summary: str
    birth: str | None = None
    death: str | None = None
    occupations: list[str] = Field(default_factory=list)
    timeline: list[TimelineEvent] = Field(default_factory=list)
    environment: EnvironmentContext | None = None
    relationships: list[Relationship] = Field(default_factory=list)
    pattern_profile: PatternProfile | None = None
    narrative: list[EvidencedClaim] = Field(default_factory=list)
    source_urls: list[SourceRef] = Field(default_factory=list)
    generated_at: str | None = None
