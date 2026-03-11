from fastapi import APIRouter

router = APIRouter(prefix="/ranking", tags=["Ranking"])


@router.get("/")
def get_ranking():

    return {
        "message": "Candidate ranking endpoint"
    }