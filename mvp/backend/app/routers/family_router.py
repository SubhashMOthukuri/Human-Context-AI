import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.db_models import AncestorProfile, Family, User
from app.genealogy import compute_generation
from app.schemas import (
    AncestorCreateRequest,
    AncestorSummaryResponse,
    AncestorUpdateRequest,
    FamilyCreateRequest,
    FamilyResponse,
    FamilyUpdateRequest,
)
from app.services.family_context_engine import build_family_profile
from app.services.llm_client import LLMNotConfigured, LLMRequestFailed

router = APIRouter(prefix="/api/families", tags=["families"])


def _get_owned_family(family_id: int, user: User, db: Session) -> Family:
    """The hard isolation boundary: a family that isn't yours doesn't exist
    as far as any request is concerned. 404, never 403 — don't even confirm
    that a family with this id belongs to someone else."""
    family = (
        db.query(Family).filter(Family.id == family_id, Family.owner_user_id == user.id).first()
    )
    if family is None:
        raise HTTPException(status_code=404, detail="Family not found.")
    return family


def _get_owned_ancestor(family_id: int, ancestor_id: int, user: User, db: Session) -> AncestorProfile:
    family = _get_owned_family(family_id, user, db)
    ancestor = (
        db.query(AncestorProfile)
        .filter(AncestorProfile.id == ancestor_id, AncestorProfile.family_id == family.id)
        .first()
    )
    if ancestor is None:
        raise HTTPException(status_code=404, detail="Ancestor not found.")
    return ancestor


def _validate_link(
    family_id: int, linked_id: int | None, self_id: int | None, db: Session, what: str
) -> None:
    if linked_id is None:
        return
    if linked_id == self_id:
        raise HTTPException(status_code=400, detail=f"Someone can't be their own {what}.")
    linked = (
        db.query(AncestorProfile)
        .filter(AncestorProfile.id == linked_id, AncestorProfile.family_id == family_id)
        .first()
    )
    if linked is None:
        raise HTTPException(status_code=400, detail=f"That {what} isn't in this family.")


def _family_ancestors_by_id(family_id: int, db: Session) -> dict[int, AncestorProfile]:
    rows = db.query(AncestorProfile).filter(AncestorProfile.family_id == family_id).all()
    return {a.id: a for a in rows}


def _summary(a: AncestorProfile, by_id: dict[int, AncestorProfile]) -> AncestorSummaryResponse:
    return AncestorSummaryResponse(
        id=a.id,
        name=a.name,
        relation=a.relation,
        created_at=a.created_at,
        has_profile=a.generated_profile_json is not None,
        parent_ancestor_id=a.parent_ancestor_id,
        parent2_ancestor_id=a.parent2_ancestor_id,
        spouse_ancestor_id=a.spouse_ancestor_id,
        generation=compute_generation(a.id, by_id),
        birth_year=a.birth_year,
        birth_place=a.birth_place,
        death_year=a.death_year,
        death_place=a.death_place,
        notes=a.notes,
    )


@router.post("", response_model=FamilyResponse)
def create_family(
    body: FamilyCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    family = Family(name=body.name, owner_user_id=user.id)
    db.add(family)
    db.commit()
    db.refresh(family)
    return family


@router.get("", response_model=list[FamilyResponse])
def list_families(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Family).filter(Family.owner_user_id == user.id).order_by(Family.created_at).all()


@router.patch("/{family_id}", response_model=FamilyResponse)
def rename_family(
    family_id: int,
    body: FamilyUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = _get_owned_family(family_id, user, db)
    family.name = body.name
    db.commit()
    db.refresh(family)
    return family


@router.delete("/{family_id}")
def delete_family(family_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = _get_owned_family(family_id, user, db)
    db.delete(family)  # cascades to its ancestors (cascade="all, delete-orphan")
    db.commit()
    return {"deleted": True}


@router.post("/{family_id}/ancestors", response_model=AncestorSummaryResponse)
def create_ancestor(
    family_id: int,
    body: AncestorCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = _get_owned_family(family_id, user, db)
    _validate_link(family.id, body.parent_ancestor_id, None, db, "parent")
    _validate_link(family.id, body.parent2_ancestor_id, None, db, "second parent")
    _validate_link(family.id, body.spouse_ancestor_id, None, db, "spouse")
    ancestor = AncestorProfile(
        family_id=family.id,
        name=body.name,
        relation=body.relation,
        birth_year=body.birth_year,
        birth_place=body.birth_place,
        death_year=body.death_year,
        death_place=body.death_place,
        notes=body.notes,
        parent_ancestor_id=body.parent_ancestor_id,
        parent2_ancestor_id=body.parent2_ancestor_id,
        spouse_ancestor_id=body.spouse_ancestor_id,
    )
    db.add(ancestor)
    db.commit()
    db.refresh(ancestor)
    by_id = _family_ancestors_by_id(family.id, db)
    return _summary(ancestor, by_id)


@router.get("/{family_id}/ancestors", response_model=list[AncestorSummaryResponse])
def list_ancestors(family_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = _get_owned_family(family_id, user, db)
    by_id = _family_ancestors_by_id(family.id, db)
    ancestors = sorted(by_id.values(), key=lambda a: a.created_at)
    return [_summary(a, by_id) for a in ancestors]


@router.patch("/{family_id}/ancestors/{ancestor_id}", response_model=AncestorSummaryResponse)
def update_ancestor(
    family_id: int,
    ancestor_id: int,
    body: AncestorUpdateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ancestor = _get_owned_ancestor(family_id, ancestor_id, user, db)
    _validate_link(family_id, body.parent_ancestor_id, ancestor.id, db, "parent")
    _validate_link(family_id, body.parent2_ancestor_id, ancestor.id, db, "second parent")
    _validate_link(family_id, body.spouse_ancestor_id, ancestor.id, db, "spouse")
    ancestor.name = body.name
    ancestor.relation = body.relation
    ancestor.birth_year = body.birth_year
    ancestor.birth_place = body.birth_place
    ancestor.death_year = body.death_year
    ancestor.death_place = body.death_place
    ancestor.notes = body.notes
    ancestor.parent_ancestor_id = body.parent_ancestor_id
    ancestor.parent2_ancestor_id = body.parent2_ancestor_id
    ancestor.spouse_ancestor_id = body.spouse_ancestor_id
    ancestor.generated_profile_json = None  # edited notes invalidate the old generated profile
    db.commit()
    db.refresh(ancestor)
    by_id = _family_ancestors_by_id(ancestor.family_id, db)
    return _summary(ancestor, by_id)


@router.get("/{family_id}/ancestors/{ancestor_id}/profile")
async def get_ancestor_profile(
    family_id: int,
    ancestor_id: int,
    regenerate: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ancestor = _get_owned_ancestor(family_id, ancestor_id, user, db)

    if ancestor.generated_profile_json and not regenerate:
        return json.loads(ancestor.generated_profile_json)

    try:
        profile = await build_family_profile(
            name=ancestor.name,
            relation=ancestor.relation,
            birth_year=ancestor.birth_year,
            birth_place=ancestor.birth_place,
            death_year=ancestor.death_year,
            death_place=ancestor.death_place,
            notes=ancestor.notes,
        )
    except LLMNotConfigured as exc:
        raise HTTPException(status_code=503, detail=str(exc))
    except LLMRequestFailed as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    data = profile.model_dump(mode="json")
    ancestor.generated_profile_json = json.dumps(data)
    db.commit()
    return data


@router.delete("/{family_id}/ancestors/{ancestor_id}")
def delete_ancestor(
    family_id: int,
    ancestor_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ancestor = _get_owned_ancestor(family_id, ancestor_id, user, db)
    db.delete(ancestor)
    db.commit()
    return {"deleted": True}
