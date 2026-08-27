"""Canonical permission codes and the system roles that bundle them.

Backend authorization is always performed against these codes, never
against a role name. Roles are a convenience for assigning bundles of
permissions to a membership.
"""

CLIENTS_READ = "clients.read"
CLIENTS_WRITE = "clients.write"
TICKETS_READ = "tickets.read"
TICKETS_CREATE = "tickets.create"
TICKETS_ASSIGN = "tickets.assign"
TICKETS_UPDATE = "tickets.update"
TICKETS_CLOSE = "tickets.close"
TICKETS_INTERNAL_COMMENT = "tickets.internal_comment"
TASKS_READ = "tasks.read"
TASKS_WRITE = "tasks.write"
SLA_READ = "sla.read"
SLA_MANAGE = "sla.manage"
NOTIFICATIONS_READ = "notifications.read"
KNOWLEDGE_READ = "knowledge.read"
KNOWLEDGE_WRITE = "knowledge.write"
AI_ASSIST = "ai.assist"
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
    TASKS_READ,
    TASKS_WRITE,
    SLA_READ,
    SLA_MANAGE,
    NOTIFICATIONS_READ,
    KNOWLEDGE_READ,
    KNOWLEDGE_WRITE,
    AI_ASSIST,
    USERS_MANAGE,
    ROLES_MANAGE,
    SETTINGS_MANAGE,
    AUDIT_READ,
    REPORTS_READ,
)

ROLE_CLIENT = "client"
ROLE_OPERATOR = "operator"
ROLE_SUPERVISOR = "supervisor"
ROLE_ADMINISTRATOR = "administrator"

SYSTEM_ROLE_PERMISSIONS: dict[str, tuple[str, ...]] = {
    ROLE_CLIENT: (),
    ROLE_OPERATOR: (
        CLIENTS_READ,
        TICKETS_READ,
        TICKETS_CREATE,
        TICKETS_ASSIGN,
        TICKETS_UPDATE,
        TICKETS_INTERNAL_COMMENT,
        TASKS_READ,
        TASKS_WRITE,
        SLA_READ,
        NOTIFICATIONS_READ,
        KNOWLEDGE_READ,
        AI_ASSIST,
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
        TASKS_READ,
        TASKS_WRITE,
        SLA_READ,
        SLA_MANAGE,
        NOTIFICATIONS_READ,
        KNOWLEDGE_READ,
        KNOWLEDGE_WRITE,
        AI_ASSIST,
        REPORTS_READ,
    ),
    ROLE_ADMINISTRATOR: ALL_PERMISSIONS,
}
