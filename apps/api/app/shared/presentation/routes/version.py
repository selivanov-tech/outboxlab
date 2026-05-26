from fastapi import APIRouter, Depends

from app.config import Settings, get_settings

router = APIRouter()


@router.get("/version")
async def version(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    return {
        "version": "0.0.1",
        "git_sha": settings.git_sha,
        "app_env": settings.app_env,
    }
