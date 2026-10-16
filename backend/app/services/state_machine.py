from typing import Dict, Set, Tuple
from fastapi import HTTPException, status
from app.models.enums import WorkItemStatus, TeamRole

# Transition graph: (current_status, target_status) -> Required minimum role or allowed roles
ALLOWED_TRANSITIONS: Dict[Tuple[WorkItemStatus, WorkItemStatus], Set[TeamRole]] = {
    (WorkItemStatus.OPEN, WorkItemStatus.IN_PROGRESS): {
        TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN
    },
    (WorkItemStatus.IN_PROGRESS, WorkItemStatus.AWAITING_APPROVAL): {
        TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN
    },
    (WorkItemStatus.IN_PROGRESS, WorkItemStatus.OPEN): {
        TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN
    },
    # CRITICAL APPROVAL STEP: Only Lead or Admin can approve and mark Resolved!
    (WorkItemStatus.AWAITING_APPROVAL, WorkItemStatus.RESOLVED): {
        TeamRole.LEAD, TeamRole.ADMIN
    },
    (WorkItemStatus.AWAITING_APPROVAL, WorkItemStatus.IN_PROGRESS): {
        TeamRole.MEMBER, TeamRole.LEAD, TeamRole.ADMIN
    },
    (WorkItemStatus.RESOLVED, WorkItemStatus.CLOSED): {
        TeamRole.LEAD, TeamRole.ADMIN
    },
    (WorkItemStatus.RESOLVED, WorkItemStatus.IN_PROGRESS): {
        TeamRole.LEAD, TeamRole.ADMIN
    },
    (WorkItemStatus.CLOSED, WorkItemStatus.OPEN): {
        TeamRole.ADMIN
    },
}


def validate_transition(current_status_str: str, target_status_str: str, user_role_str: str) -> None:
    try:
        current_status = WorkItemStatus(current_status_str)
        target_status = WorkItemStatus(target_status_str)
        user_role = TeamRole(user_role_str)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status or role value: {str(e)}"
        )

    if current_status == target_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Item is already in status '{target_status.value}'"
        )

    transition_pair = (current_status, target_status)
    if transition_pair not in ALLOWED_TRANSITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Forbidden workflow transition: Cannot move directly from '{current_status.value}' to '{target_status.value}'."
        )

    allowed_roles = ALLOWED_TRANSITIONS[transition_pair]
    if user_role not in allowed_roles:
        if current_status == WorkItemStatus.AWAITING_APPROVAL and target_status == WorkItemStatus.RESOLVED:
            detail_msg = "Workflow policy violation: Only a team Lead or Admin can approve work items and mark them Resolved."
        else:
            detail_msg = f"Insufficient permissions: Role '{user_role.value}' cannot transition items from '{current_status.value}' to '{target_status.value}'."
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail_msg
        )
