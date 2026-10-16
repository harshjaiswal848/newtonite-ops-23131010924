from enum import Enum


class TeamRole(str, Enum):
    VIEWER = "Viewer"
    MEMBER = "Member"
    LEAD = "Lead"
    ADMIN = "Admin"


class WorkItemType(str, Enum):
    INCIDENT = "incident"
    CUSTOMER_ISSUE = "customer_issue"
    PAYMENT = "payment"
    COMPLIANCE = "compliance"
    TASK = "task"


class WorkItemPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class WorkItemStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    AWAITING_APPROVAL = "Awaiting Approval"
    RESOLVED = "Resolved"
    CLOSED = "Closed"


class ActivityEventType(str, Enum):
    CREATED = "created"
    STATUS_CHANGED = "status_changed"
    ASSIGNED = "assigned"
    UNASSIGNED = "unassigned"
    PRIORITY_CHANGED = "priority_changed"
    UPDATED = "updated"
    COMMENTED = "commented"


class OutboxJobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
