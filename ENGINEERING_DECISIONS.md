# Engineering Decisions & Architecture Trade-offs

**Project:** Operations Under Pressure  
**Candidate Roll Number:** `23131010924`  
**Repository:** `newtonite-ops-23131010924`  

---

## Executive Summary
This document explains the rationale, alternative options evaluated, concrete architectural choices, and technical trade-offs made during the implementation of the "Operations Under Pressure" platform. The platform is designed to guarantee consistency under race conditions, enforce server-side resource-level authorization, and handle operational scale reliably.

---

## 1. Concurrency Control: Atomic Conditional Updates & Optimistic Versioning

### Context
In high-stress operational environments, multiple operators frequently view and attempt to act on the same unassigned or volatile incident simultaneously. Without strict concurrency safeguards, two operators can double-claim an item, or an operator with stale screen data can overwrite updates made seconds earlier by a colleague.

### Options Considered
1. **Pessimistic Row Locking (`SELECT FOR UPDATE`)**: Lock the database row as soon as a user opens the item drawer.
   - *Problem:* Holding locks across human thinking/reading time exhausts connection pools and causes widespread database timeouts under load.
2. **First-Write-Wins with Optimistic Locking (Chosen for Edits)**: Compare-and-swap on an integer `version` vector (`WHERE id = :id AND version = :client_version`).
3. **Atomic Conditional Update (Chosen for Claims)**: Execute atomic conditional SQL:
   ```sql
   UPDATE work_items 
   SET assignee_id = :user_id, status = 'In Progress', version = version + 1, updated_at = NOW() 
   WHERE id = :item_id AND assignee_id IS NULL;
   ```

### Technical Choice
- **Atomic Claiming:** We use atomic conditional updates for claiming. If two operators click "Claim" at the exact same millisecond, the database's internal row lock serializes the execution. Exactly one query matches `assignee_id IS NULL` and updates 1 row (`200 OK`); the colliding query updates 0 rows and immediately returns a `409 Conflict`.
- **Optimistic Locking:** For general modifications (title, priority, description), each record maintains an incrementing integer `version`. If the client submits an update with a mismatched version, the server rejects it with `409 Conflict` and returns the freshest state.

### Trade-offs
- *Trade-off:* The client must handle `409 Conflict` responses explicitly by rolling back optimistic UI states and displaying a conflict resolution banner. This adds minor frontend complexity but eliminates data loss and double-assignment with zero database locking overhead.

---

## 2. History & Audit Integrity: Transaction-Bound Append-Only Events

### Context
Operational compliance demands that no work item ever changes status, priority, or ownership without a corresponding immutable audit trail. A common anti-pattern is updating the entity and then firing an asynchronous event to record history; if the server crashes or network breaks between those two operations, state drifts from history.

### Options Considered
1. **Dual Writes via Messaging (Item Update + Kafka/RabbitMQ Event)**:
   - *Problem:* Vulnerable to distributed partial failure. If the database commit succeeds but message publishing fails, history is lost.
2. **Database Change Data Capture (CDC) via Debezium/WAL**:
   - *Problem:* Overkill for a single-service vertical slice; adds significant infrastructure operational burden.
3. **Transactional Event Append in Primary DB Transaction (Chosen)**:
   - Perform the entity update and insert the audit event into `activity_events` within the **exact same database transaction**.

### Technical Choice
All mutations (creation, assignment, status transition, priority shifts, and comments) are executed within a single SQLAlchemy `AsyncSession` transaction. If the item update fails, the audit record is rolled back; if the audit insert fails, the item update is rolled back.

### Trade-offs
- *Trade-off:* Increases the disk write volume per mutation on the primary PostgreSQL cluster. At 10x scale, the `activity_events` table would require declarative time-range partitioning (e.g., monthly partitions) to keep indexes compact.

---

## 3. Real Server-Side Authorization: Team-Scoped Role-Based Access Control (RBAC)

### Context
Internal operations tools frequently fall into the trap of "cosmetic security"—hiding buttons in the UI while leaving API endpoints unguarded. Furthermore, users often belong to multiple functional teams with different responsibilities (e.g. Lead in Payments, but merely Member in Core Infrastructure).

### Options Considered
1. **Global User Roles (e.g., user is globally an 'Admin' or 'User')**:
   - *Problem:* Unrealistic for cross-functional operations. A Payments Lead should not be authorized to approve regulatory filings in Compliance without explicit membership.
2. **Team-Scoped Roles with Server Dependency Injection (Chosen)**:
   - A `memberships` table maps `(user_id, team_id, role)` where `role ∈ {Viewer, Member, Lead, Admin}`.
   - FastAPI dependencies inspect the target item's `team_id` and enforce:
     - `Viewer`: Read-only. Blocked with `403 Forbidden` on creation, claims, or edits.
     - `Member`: Can create, claim, edit, and advance items to `Awaiting Approval`.
     - `Lead`: Can approve items from `Awaiting Approval` to `Resolved` and close items.
     - `Admin`: Full oversight within assigned teams.

### Technical Choice
Permissions are validated at the service layer inside `verify_team_access` and `validate_transition`. Non-members receive `403 Forbidden` (or `404 Not Found` to prevent entity enumeration), and illegal state transitions (such as a Member attempting to approve an item) are strictly rejected.

### Trade-offs
- *Trade-off:* Requires joining or caching the user's team memberships on protected requests. We mitigated this by returning the user's role mapping directly within the verified JWT session context while validating live permissions against the database.

---

## 4. Asynchronous Side-Effects: Transactional Outbox Pattern

### Context
When operational work items undergo state transitions (e.g. an incident is claimed or marked urgent), side-effects such as sending notifications, dispatching webhooks, or alerting on-call engineers must take place reliably without blocking the HTTP request/response loop.

### Options Considered
1. **Synchronous In-Request Dispatch**:
   - *Problem:* High HTTP latency; if external notification gateways are slow or fail, the entire user operation times out or fails.
2. **In-Memory Background Tasks (`asyncio.create_task` / FastAPI `BackgroundTasks`)**:
   - *Problem:* Volatile. If the container restarts or crashes mid-flight, pending jobs are permanently lost without retry records.
3. **Transactional Outbox Table with Polling Worker (Chosen)**:
   - Enqueue jobs into an `outbox_jobs` table inside the item mutation transaction.
   - An independent worker polls pending jobs using `SELECT ... FOR UPDATE SKIP LOCKED`.

### Technical Choice
- Jobs are written with initial status `pending`.
- The worker executes jobs with:
  - Exponential backoff: `scheduled_at = NOW() + 2^attempts seconds`.
  - Max retry cap (default: 5 attempts).
  - Dead-letter state: jobs exceeding max attempts are marked `failed` with captured error tracebacks in `last_error`.
  - Idempotent handlers: ensures at-least-once processing does not create duplicate side-effects.

### Trade-offs
- *Trade-off:* Short delay (polling interval of 2 seconds) between mutation and background dispatch compared to push-based pub/sub. In extreme-scale scenarios, PostgreSQL `LISTEN/NOTIFY` can be combined with the outbox table to achieve instant wake-up.

---

## 5. Scalability & Pagination: Indexed Keyset / Cursor Pagination

### Context
Operational tables grow rapidly to tens of thousands of work items. Traditional `OFFSET / LIMIT` pagination suffers from severe performance degradation ($O(N)$ scanning on large offsets) and the "sliding window" anomaly (items shifting pages when new records are inserted during browsing).

### Options Considered
1. **Offset-Based Pagination (`OFFSET 10000 LIMIT 25`)**:
   - *Problem:* Scans and discards 10,000 index entries for every page. Database queries become slower as operators navigate deeper into logs.
2. **Client-Side Filtering**:
   - *Problem:* Loading all items into the browser and filtering client-side causes unacceptable memory bloat and network transfer waste.
3. **Indexed Keyset / Cursor Pagination (Chosen)**:
   - Base64-encoded cursor storing `(created_at, id)`.
   - SQL query:
     ```sql
     WHERE (created_at < :cursor_time) 
        OR (created_at = :cursor_time AND id < :cursor_id)
     ORDER BY created_at DESC, id DESC 
     LIMIT 26;
     ```

### Technical Choice
We implemented keyset pagination backed by composite index `(team_id, created_at, id)` and filter indexes on `(team_id, status)` and `(team_id, priority)`. This guarantees $O(\log N)$ point lookups regardless of whether the table contains 1,000 items or 10,000,000 items.

### Trade-offs
- *Trade-off:* Does not support jumping directly to an arbitrary page number (e.g. "Jump to Page 42"). However, for operational work item streams, forward streaming ("Load More") and faceted filtering are the natural interaction paradigms.

---

## 6. What Was Deliberately Not Built & Known Limitations

Per the project brief's explicit instruction to build a **tight vertical slice** and avoid stretching scope:
1. **No External SMTP/SES Delivery**: Notifications are routed to a verified outbox audit sink rather than third-party email APIs to ensure local offline evaluability.
2. **No WebSockets**: Live synchronicity relies on TanStack Query automatic focus/interval refetching and explicit user reload buttons. This eliminates connection heartbeat overhead.
3. **No File Attachments**: Kept work item schemas focused strictly on metadata, state transitions, and audit trails.
4. **No Public Sign-Up Flow**: Production enterprise internal ops tools do not allow public user registration; authentication relies on pre-seeded corporate personas with predefined team memberships.
