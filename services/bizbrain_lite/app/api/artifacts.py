from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_api_token
from app.schemas.artifact import ArtifactCreate, ArtifactRecord
from app.services.registry_service import registry_service

router = APIRouter(prefix="/artifacts", tags=["artifacts"], dependencies=[Depends(require_api_token)])


@router.post("", response_model=ArtifactRecord)
async def create_artifact(payload: ArtifactCreate) -> ArtifactRecord:
    return await registry_service.create_artifact(payload)


@router.get("", response_model=list[ArtifactRecord])
async def list_artifacts() -> list[ArtifactRecord]:
    return await registry_service.list_artifacts()


@router.get("/{artifact_id}", response_model=ArtifactRecord)
async def get_artifact(artifact_id: str) -> ArtifactRecord:
    artifact = await registry_service.get_artifact(artifact_id)
    if not artifact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Artifact not found")
    return artifact


@router.get("/by-task/{task_id}", response_model=list[ArtifactRecord])
async def get_task_artifacts(task_id: str) -> list[ArtifactRecord]:
    return await registry_service.list_task_artifacts(task_id)

