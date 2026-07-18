import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from appsec.api.deps import CurrentOrganizationIdDep, CurrentUserIdDep, get_project_service
from appsec.application.projects.schemas import CreateProjectRequest, ProjectResponse
from appsec.application.projects.service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])


def _to_response(project) -> ProjectResponse:  # noqa: ANN001
    return ProjectResponse(
        id=project.id,
        organization_id=project.organization_id,
        name=project.name,
        description=project.description,
        created_at=project.created_at,
    )


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: CreateProjectRequest,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await project_service.create(organization_id, user_id, payload.name, payload.description)
    return _to_response(project)


@router.get("", response_model=list[ProjectResponse])
async def list_projects(
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> list[ProjectResponse]:
    projects = await project_service.list_for_organization(organization_id, user_id)
    return [_to_response(p) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> ProjectResponse:
    project = await project_service.get_by_id(project_id, organization_id, user_id)
    return _to_response(project)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: uuid.UUID,
    organization_id: CurrentOrganizationIdDep,
    user_id: CurrentUserIdDep,
    project_service: Annotated[ProjectService, Depends(get_project_service)],
) -> None:
    await project_service.delete(project_id, organization_id, user_id)
