"""Canonical permission codes and the system roles that bundle them.

Backend authorization is always performed against these codes, never
against a role name. Roles are a convenience for assigning bundles of
permissions to a membership.
"""

# --- Permission codes (section E of the project charter) ---
CLIENTS_READ = "clients.read"
CLIENTS_WRITE = "clients.write"
TICKETS_READ = "tickets.read"
TICKETS_CREATE = "tickets.create"
TICKETS_ASSIGN = "tickets.assign"
TICKETS_UPDATE = "tickets.update"
TICKETS_CLOSE = "tickets.close"
TICKETS_INTERNAL_COMMENT = "tickets.internal_comment"
USERS_MANAGE = "users.manage"
ROLES_MANAGE = "roles.manage"
SETTINGS_MANAGE = "settings.manage"
AUDIT_READ = "audit.read"
REPORTS_READ = "reports.read"

ALL_PERMISSIONS: tuple[str, ...] = (
    CLIENTS_READ,
    CLIENTS_WRITE,
    TICKETS_READ,
    TICKETS_CREATE,
    TICKETS_ASSIGN,
    TICKETS_UPDATE,
    TICKETS_CLOSE,
    TICKETS_INTERNAL_COMMENT,
    USERS_MANAGE,
    ROLES_MANAGE,
    SETTINGS_MANAGE,
    AUDIT_READ,
    REPORTS_READ,
)

# --- System roles (section E: Client, Operator, Supervisor, Administrator) ---
ROLE_CLIENT = "client"
ROLE_OPERATOR = "operator"
ROLE_SUPERVISOR = "supervisor"
ROLE_ADMINISTRATOR = "administrator"

SYSTEM_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    # Clients only ever act through the client-portal endpoints (Phase 7+),
    # which are not covered by this generic permission set — a client's
    # membership intentionally carries no internal-service permissions.
    ROLE_CLIENT: (),
    ROLE_OPERATOR: (
        CLIENTS_READ,
        TICKETS_READ,
        TICKETS_CREATE,
        TICKETS_ASSIGN,
        TICKETS_UPDATE,
        TICKETS_INTERNAL_COMMENT,
    ),
    ROLE_SUPERVISOR: (
        CLIENTS_READ,
        CLIENTS_WRITE,
        TICKETS_READ,
        TICKETS_CREATE,
        TICKETS_ASSIGN,
        TICKETS_UPDATE,
        TICKETS_CLOSE,
        TICKETS_INTERNAL_COMMENT,
        REPORTS_READ,
    ),
    ROLE_ADMINISTRATOR: ALL_PERMISSIONS,
}
