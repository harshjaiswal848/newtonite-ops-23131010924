import asyncio
import uuid
import random
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, init_db
from app.models.user import User
from app.models.team import Team, Membership
from app.models.work_item import WorkItem
from app.models.activity import ActivityEvent, Comment
from app.models.enums import (
    TeamRole,
    WorkItemType,
    WorkItemPriority,
    WorkItemStatus,
    ActivityEventType,
)
from app.services.auth_service import get_password_hash


TEAMS_DATA = [
    {
        "id": "team-payments-01",
        "name": "Payments Operations",
        "slug": "payments-ops",
        "description": "High-velocity dispute mitigation, card payment authorization escalations, and settlement discrepancies.",
    },
    {
        "id": "team-compliance-02",
        "name": "Compliance & Security",
        "slug": "compliance-security",
        "description": "AML screening, sanctions monitoring, KYC re-verification, and high-risk regulatory audits.",
    },
    {
        "id": "team-infra-03",
        "name": "Core Infrastructure",
        "slug": "core-infra",
        "description": "Distributed cloud reliability, database lock contention triage, and Kubernetes cluster health.",
    },
]

USERS_DATA = [
    {
        "id": "user-lead-payments",
        "email": "lead.payments@newtonite.internal",
        "full_name": "Aarav Sharma (Payments Lead)",
        "password": "password123",
        "roles": [("team-payments-01", TeamRole.LEAD.value), ("team-infra-03", TeamRole.MEMBER.value)],
    },
    {
        "id": "user-member-payments",
        "email": "member.payments@newtonite.internal",
        "full_name": "Priya Nair (Payments Member)",
        "password": "password123",
        "roles": [("team-payments-01", TeamRole.MEMBER.value)],
    },
    {
        "id": "user-viewer-payments",
        "email": "viewer.payments@newtonite.internal",
        "full_name": "Rohan Patel (Payments Viewer)",
        "password": "password123",
        "roles": [("team-payments-01", TeamRole.VIEWER.value)],
    },
    {
        "id": "user-lead-compliance",
        "email": "lead.compliance@newtonite.internal",
        "full_name": "Elena Rostova (Compliance Lead)",
        "password": "password123",
        "roles": [("team-compliance-02", TeamRole.LEAD.value)],
    },
    {
        "id": "user-member-compliance",
        "email": "member.compliance@newtonite.internal",
        "full_name": "Marcus Vance (Compliance Member)",
        "password": "password123",
        "roles": [("team-compliance-02", TeamRole.MEMBER.value)],
    },
    {
        "id": "user-viewer-compliance",
        "email": "viewer.compliance@newtonite.internal",
        "full_name": "Sophia Zhang (Compliance Viewer)",
        "password": "password123",
        "roles": [("team-compliance-02", TeamRole.VIEWER.value)],
    },
    {
        "id": "user-lead-infra",
        "email": "lead.infra@newtonite.internal",
        "full_name": "David Kim (Infra Lead)",
        "password": "password123",
        "roles": [("team-infra-03", TeamRole.LEAD.value)],
    },
    {
        "id": "user-member-infra",
        "email": "member.infra@newtonite.internal",
        "full_name": "Ananya Roy (Infra Member)",
        "password": "password123",
        "roles": [("team-infra-03", TeamRole.MEMBER.value)],
    },
    {
        "id": "user-viewer-infra",
        "email": "viewer.infra@newtonite.internal",
        "full_name": "Vikram Seth (Infra Viewer)",
        "password": "password123",
        "roles": [("team-infra-03", TeamRole.VIEWER.value)],
    },
    {
        "id": "user-admin-global",
        "email": "admin@newtonite.internal",
        "full_name": "Harsh Jaiswal (Ops Admin)",
        "password": "password123",
        "roles": [
            ("team-payments-01", TeamRole.ADMIN.value),
            ("team-compliance-02", TeamRole.ADMIN.value),
            ("team-infra-03", TeamRole.ADMIN.value),
        ],
    },
]

ITEM_TEMPLATES = {
    "team-payments-01": [
        ("Dispute Settlement Mismatch: Merchant #{id}", "Settlement file reconciliation reported variance between gateway journal and bank ledger.", WorkItemType.PAYMENT, WorkItemPriority.URGENT),
        ("Suspicious Velocity Spike on Card BIN {id}", "Over 40 transactions detected within 90 seconds from atypical IP subnet.", WorkItemType.INCIDENT, WorkItemPriority.HIGH),
        ("Refund Gateway Timeout for Order #{id}", "Stripe hook failed with 504 timeout; manual debit reversal required.", WorkItemType.CUSTOMER_ISSUE, WorkItemPriority.MEDIUM),
        ("Card Re-issuance Protocol Review for Tier-{id}", "Review annual compliance and scheme rules with banking partner.", WorkItemType.COMPLIANCE, WorkItemPriority.LOW),
        ("Batch Reconciliation Lock Out on Node-{id}", "Nightly cron locked on row contention during debit batch settlement.", WorkItemType.TASK, WorkItemPriority.MEDIUM),
    ],
    "team-compliance-02": [
        ("Sanctions Screening False-Positive Check: Entity #{id}", "Automated OFAC filter matched high-net-worth commercial counterparty.", WorkItemType.COMPLIANCE, WorkItemPriority.URGENT),
        ("PEP Escalation Verification for Account #{id}", "Account owner flagged as Politically Exposed Person; enhanced due diligence required.", WorkItemType.COMPLIANCE, WorkItemPriority.HIGH),
        ("SAR Filing Deadline Approaching for Case #{id}", "FinCEN submission window expires in 48 hours for suspicious wire transfer activity.", WorkItemType.TASK, WorkItemPriority.URGENT),
        ("Periodic AML Threshold Recalibration #{id}", "Review threshold rules for automated risk score classification.", WorkItemType.TASK, WorkItemPriority.MEDIUM),
        ("Customer Identity Document Mismatch #{id}", "Address proof document failed OCR validation during account onboarding.", WorkItemType.CUSTOMER_ISSUE, WorkItemPriority.MEDIUM),
    ],
    "team-infra-03": [
        ("Postgres Row Lock Contention on Cluster-{id}", "Deadlock spikes observed on work_items table during peak hours.", WorkItemType.INCIDENT, WorkItemPriority.URGENT),
        ("Redis Eviction Alert on Primary Sentinel #{id}", "Memory usage exceeded 85% with allkeys-lru eviction frequency spiking.", WorkItemType.INCIDENT, WorkItemPriority.HIGH),
        ("Kubernetes Ingress Gateway 502 Errors #{id}", "Envoy proxy dropping downstream connections due to keepalive mismatch.", WorkItemType.INCIDENT, WorkItemPriority.HIGH),
        ("Database Backup Integrity Verification #{id}", "Run automated recovery drill against standby snapshot replica.", WorkItemType.TASK, WorkItemPriority.LOW),
        ("TLS Certificate Auto-Renewal Check #{id}", "Verify Let's Encrypt certificate rotation for internal gateway domain.", WorkItemType.TASK, WorkItemPriority.MEDIUM),
    ],
}


async def seed_database(target_item_count: int = 1200):
    print("Initializing tables if needed...")
    await init_db()

    async with AsyncSessionLocal() as session:
        # Check if already seeded
        user_count = (await session.execute(select(func.count(User.id)))).scalar()
        if user_count and user_count >= len(USERS_DATA):
            print(f"Database already contains {user_count} users. Checking work items count...")
            items_count = (await session.execute(select(func.count(WorkItem.id)))).scalar()
            if items_count and items_count >= target_item_count:
                print(f"Database already seeded with {items_count} items. Skipping.")
                return

        print("Seeding Teams...")
        for t in TEAMS_DATA:
            existing = await session.get(Team, t["id"])
            if not existing:
                team = Team(
                    id=t["id"],
                    name=t["name"],
                    slug=t["slug"],
                    description=t["description"],
                )
                session.add(team)

        print("Seeding Users & Team Memberships...")
        user_instances = {}
        for u in USERS_DATA:
            existing_user = await session.get(User, u["id"])
            if not existing_user:
                hashed = get_password_hash(u["password"])
                user = User(
                    id=u["id"],
                    email=u["email"],
                    full_name=u["full_name"],
                    hashed_password=hashed,
                    is_active=True,
                )
                session.add(user)
                user_instances[u["id"]] = user

                for team_id, role in u["roles"]:
                    membership = Membership(
                        id=str(uuid.uuid4()),
                        user_id=u["id"],
                        team_id=team_id,
                        role=role,
                    )
                    session.add(membership)

        await session.flush()

        # Seed Work Items to prove scale, indexing, and cursor pagination
        current_items_count = (await session.execute(select(func.count(WorkItem.id)))).scalar() or 0
        items_to_generate = target_item_count - current_items_count

        if items_to_generate > 0:
            print(f"Generating {items_to_generate} realistic work items across teams...")
            now = datetime.now(timezone.utc)
            statuses = [
                WorkItemStatus.OPEN.value,
                WorkItemStatus.IN_PROGRESS.value,
                WorkItemStatus.AWAITING_APPROVAL.value,
                WorkItemStatus.RESOLVED.value,
                WorkItemStatus.CLOSED.value,
            ]
            status_weights = [0.35, 0.25, 0.15, 0.15, 0.10]

            team_user_map = {
                "team-payments-01": ["user-lead-payments", "user-member-payments"],
                "team-compliance-02": ["user-lead-compliance", "user-member-compliance"],
                "team-infra-03": ["user-lead-infra", "user-member-infra"],
            }

            for i in range(items_to_generate):
                team_id = random.choice(list(TEAMS_DATA))[ "id" ]
                template = random.choice(ITEM_TEMPLATES[team_id])
                item_seq = 1000 + i
                title = template[0].replace("{id}", str(item_seq))
                desc = template[1]
                w_type = template[2].value
                priority = template[3].value
                status_val = random.choices(statuses, weights=status_weights, k=1)[0]

                # Age items backwards to simulate time progression for cursor pagination
                created_at = now - timedelta(days=random.randint(0, 60), hours=random.randint(0, 23), minutes=random.randint(0, 59))
                updated_at = created_at + timedelta(minutes=random.randint(5, 120))

                # Assignee determination
                assignee_id = None
                if status_val in (WorkItemStatus.IN_PROGRESS.value, WorkItemStatus.AWAITING_APPROVAL.value, WorkItemStatus.RESOLVED.value):
                    assignee_id = random.choice(team_user_map[team_id])
                elif status_val == WorkItemStatus.OPEN.value and random.random() < 0.3:
                    assignee_id = random.choice(team_user_map[team_id])

                creator_id = random.choice(team_user_map[team_id])
                due_date = created_at + timedelta(days=random.randint(1, 14)) if random.random() < 0.7 else None

                item = WorkItem(
                    id=str(uuid.uuid4()),
                    title=title,
                    description=desc,
                    type=w_type,
                    priority=priority,
                    status=status_val,
                    team_id=team_id,
                    assignee_id=assignee_id,
                    created_by_id=creator_id,
                    due_date=due_date,
                    version=random.randint(1, 4),
                    created_at=created_at,
                    updated_at=updated_at,
                )
                session.add(item)

                # Add initial activity log
                act = ActivityEvent(
                    id=str(uuid.uuid4()),
                    work_item_id=item.id,
                    user_id=creator_id,
                    event_type=ActivityEventType.CREATED.value,
                    new_value=f"Item initialized as '{status_val}'",
                    created_at=created_at,
                )
                session.add(act)

                # Batch flush every 250 items to keep memory optimal
                if (i + 1) % 250 == 0:
                    await session.flush()
                    print(f"  ...seeded {i + 1}/{items_to_generate} work items")

        await session.commit()
        print(f"Database seed complete! Successfully populated teams, demo users, and {target_item_count} work items.")


if __name__ == "__main__":
    asyncio.run(seed_database())
