import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db import get_db
from app.db_models import AncestorProfile, Family, User
from app.schemas import AncestorCreateRequest, AncestorSummaryResponse, FamilyCreateRequest, FamilyResponse
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


@router.post("/{family_id}/ancestors", response_model=AncestorSummaryResponse)
def create_ancestor(
    family_id: int,
    body: AncestorCreateRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    family = _get_owned_family(family_id, user, db)
    ancestor = AncestorProfile(
        family_id=family.id,
        name=body.name,
        relation=body.relation,
        birth_year=body.birth_year,
        birth_place=body.birth_place,
        death_year=body.death_year,
        death_place=body.death_place,
        notes=body.notes,
    )
    db.add(ancestor)
    db.commit()
    db.refresh(ancestor)
    return AncestorSummaryResponse(
        id=ancestor.id,
        name=ancestor.name,
        relation=ancestor.relation,
        created_at=ancestor.created_at,
        has_profile=False,
    )


@router.get("/{family_id}/ancestors", response_model=list[AncestorSummaryResponse])
def list_ancestors(family_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    family = _get_owned_family(family_id, user, db)
    ancestors = (
        db.query(AncestorProfile)
        .filter(AncestorProfile.family_id == family.id)
        .order_by(AncestorProfile.created_at)
        .all()
    )
    return [
        AncestorSummaryResponse(
            id=a.id,
            name=a.name,
            relation=a.relation,
            created_at=a.created_at,
            has_profile=a.generated_profile_json is not None,
        )
        for a in ancestors
    ]


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
