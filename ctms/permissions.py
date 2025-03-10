from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.sql import exists

from ctms.dependencies import get_db, get_enabled_api_client
from ctms.models import ApiClientRoles, Permissions, RolePermissions, Roles
from ctms.schemas import ApiClientSchema

ADMIN_ROLE_NAME = "admin"  # Define the admin role name globally


def has_permission(db: Session, api_client_id: str, permission_name: str) -> bool:
    """
    Check if an api_client has a specific permission.

    Args:
        session (Session): SQLAlchemy database session.
        api_client_id (str): The client_id of the api_client to check.
        permission_name (str): The name of the permission to check (e.g. 'delete_contact').

    Returns:
        bool: True if the api_client has the specified permission, False otherwise.
    """
    perm = db.query(
        exists()
        .where(Permissions.name == permission_name)
        .where(Permissions.id == RolePermissions.permission_id)
        .where(RolePermissions.role_id == ApiClientRoles.role_id)
        .where(ApiClientRoles.api_client_id == api_client_id)
    ).scalar()
    return bool(perm)


def has_any_permission(db: Session, api_client_id: str, permission_names: list[str]) -> bool:
    """
    Check if an api_client has at least one of the specified permissions, or is an admin.

    Args:
        db (Session): SQLAlchemy database session.
        api_client_id (str): The client_id of the api_client.
        permission_names (list[str]): A list of permission names to check.

    Returns:
        bool: True if the api_client has at least one of the specified permissions or is an admin.

    """
    # First, check if the api_client has the admin role, which has all permissions.
    is_admin = db.query(
        exists()
        .where(Roles.name == ADMIN_ROLE_NAME)
        .where(Roles.id == ApiClientRoles.role_id)
        .where(ApiClientRoles.api_client_id == api_client_id)
    ).scalar()  # fmt: skip

    if is_admin:
        return True

    # Check if the user has at least one of the requested permissions
    has_perm = db.query(
        exists()
        .where(Permissions.name.in_(permission_names))
        .where(Permissions.id == RolePermissions.permission_id)
        .where(RolePermissions.role_id == ApiClientRoles.role_id)
        .where(ApiClientRoles.api_client_id == api_client_id)
    ).scalar()

    return bool(has_perm)


def with_permission(*permission_names: str):
    """
    FastAPI dependency that checks if the api_client has at least one of the specified permissions,
    or has the admin role.

    Args:
        *permission_names (str): The permissions required.

    Returns:
        FastAPI dependency function.
    """

    def dependency(
        db: Annotated[Session, Depends(get_db)],
        api_client: Annotated[ApiClientSchema, Depends(get_enabled_api_client)],
    ):
        if not has_any_permission(db, api_client.client_id, list(permission_names)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission(s) required: {', '.join(permission_names)}",
            )
        return True

    return dependency
