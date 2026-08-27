from enum import StrEnum


class TicketStatus(StrEnum):
    """Fixed, system-wide lifecycle states (section H of the project
    charter). Not workspace-customizable — every workspace shares the
    same state machine so SLA logic (Phase 6) can rely on it.
    """

    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_INTERNAL = "waiting_internal"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


# Allowed status transitions, enforced server-side (section H: "Clients
# cannot arbitrarily set status or protected fields" — more generally,
# no caller can skip the state machine). Reopening from RESOLVED or
# CLOSED back to OPEN is allowed; CLOSED is otherwise terminal except
# for that explicit reopen path.
ALLOWED_TRANSITIONS: dict[TicketStatus, tuple[TicketStatus, ...]] = {
    TicketStatus.NEW: (
        TicketStatus.OPEN,
        TicketStatus.IN_PROGRESS,
        TicketStatus.CLOSED,
    ),
    TicketStatus.OPEN: (
        TicketStatus.IN_PROGRESS,
        TicketStatus.WAITING_CUSTOMER,
        TicketStatus.WAITING_INTERNAL,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ),
    TicketStatus.IN_PROGRESS: (
        TicketStatus.OPEN,
        TicketStatus.WAITING_CUSTOMER,
        TicketStatus.WAITING_INTERNAL,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ),
    TicketStatus.WAITING_CUSTOMER: (
        TicketStatus.IN_PROGRESS,
        TicketStatus.OPEN,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ),
    TicketStatus.WAITING_INTERNAL: (
        TicketStatus.IN_PROGRESS,
        TicketStatus.OPEN,
        TicketStatus.RESOLVED,
        TicketStatus.CLOSED,
    ),
    TicketStatus.RESOLVED: (
        TicketStatus.OPEN,  # reopen
        TicketStatus.CLOSED,
    ),
    TicketStatus.CLOSED: (
        TicketStatus.OPEN,  # reopen
    ),
}


def is_transition_allowed(current: TicketStatus, target: TicketStatus) -> bool:
    if current == target:
        return False
    return target in ALLOWED_TRANSITIONS.get(current, ())
