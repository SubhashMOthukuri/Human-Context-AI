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
    that a family with this id belongs to someone else. This is a boundary
    between USERS, not between a user's own families — someone's own
    families can freely link to each other (a marriage connects two
    lineages), since it's all still only visible to them."""
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


def _user_ancestors_by_id(user: User, db: Session) -> dict[int, AncestorProfile]:
    """Every ancestor across every one of this user's families — the scope
    for both generation math and link validation, since links are allowed
    to cross a user's own family boundaries."""
    rows = (
        db.query(AncestorProfile)
        .join(Family, Family.id == AncestorProfile.family_id)
        .filter(Family.owner_user_id == user.id)
        .all()
    )
    return {a.id: a for a in rows}


def _validate_link(
    by_id: dict[int, AncestorProfile], linked_id: int | None, self_id: int | None, what: str
) -> None:
    if linked_id is None:
        return
    if linked_id == self_id:
        raise HTTPException(status_code=400, detail=f"Someone can't be their own {what}.")
    if linked_id not in by_id:
        raise HTTPException(status_code=400, detail=f"That {what} isn't one of your own people.")


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
        family_id=a.family_id,
        family_name=by_id[a.id].family.name if a.id in by_id else None,
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


@router.get("/ancestors/all", response_model=list[AncestorSummaryResponse])
def list_all_ancestors(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Every person across every one of the user's families — used by the
    Add/Edit form to let a parent/spouse/second-parent link point at
    someone in a *different* family than the one currently being edited."""
    by_id = _user_ancestors_by_id(user, db)
    ancestors = sorted(by_id.values(), key=lambda a: a.created_at)
    return [_summary(a, by_id) for a in ancestors]


@router.post("/{family_id}/ancestors", response_model=AncestorSummaryResponse)
def create_ancestor(
    family_id: int,
    body: AncestorCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = _get_owned_family(family_id, user, db)
    by_id = _user_ancestors_by_id(user, db)
    _validate_link(by_id, body.parent_ancestor_id, None, "parent")
    _validate_link(by_id, body.parent2_ancestor_id, None, "second parent")
    _validate_link(by_id, body.spouse_ancestor_id, None, "spouse")
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
    by_id[ancestor.id] = ancestor
    return _summary(ancestor, by_id)


@router.get("/{family_id}/ancestors", response_model=list[AncestorSummaryResponse])
def list_ancestors(family_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = _get_owned_family(family_id, user, db)
    by_id = _user_ancestors_by_id(user, db)  # user-wide, so cross-family links resolve
    ancestors = sorted(
        (a for a in by_id.values() if a.family_id == family.id), key=lambda a: a.created_at
    )
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
    by_id = _user_ancestors_by_id(user, db)
    _validate_link(by_id, body.parent_ancestor_id, ancestor.id, "parent")
    _validate_link(by_id, body.parent2_ancestor_id, ancestor.id, "second parent")
    _validate_link(by_id, body.spouse_ancestor_id, ancestor.id, "spouse")
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
    by_id[ancestor.id] = ancestor
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
