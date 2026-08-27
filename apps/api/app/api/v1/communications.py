from urllib.parse import quote

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.authz.deps import require_permission
from app.authz.permissions import TICKETS_INTERNAL_COMMENT, TICKETS_READ, TICKETS_UPDATE
from app.db.session import get_db
from app.models.workspace import WorkspaceMembership
from app.repositories.rbac_repo import RbacRepository
from app.schemas.communication import (
    AttachmentResponse,
    ConversationCreateRequest,
    ConversationResponse,
    InboundMessageCreateRequest,
    InternalNoteCreateRequest,
    InternalNoteResponse,
    MessageCreateRequest,
    MessageResponse,
)
from app.services.communication_service import CommunicationService, MAX_ATTACHMENT_BYTES

router = APIRouter(
    prefix="/workspaces/{workspace_id}/tickets/{ticket_id}", tags=["communications"]
)


@router.post("/conversations", response_model=ConversationResponse, status_code=201)
def create_conversation(
    workspace_id: str,
    ticket_id: str,
    payload: ConversationCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> ConversationResponse:
    item = CommunicationService(db).create_conversation(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        actor_user_id=membership.user_id,
        channel=payload.channel,
        subject=payload.subject,
        external_thread_ref=payload.external_thread_ref,
    )
    return ConversationResponse.model_validate(item)


@router.get("/conversations", response_model=list[ConversationResponse])
def list_conversations(
    workspace_id: str,
    ticket_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> list[ConversationResponse]:
    items = CommunicationService(db).list_conversations(
        workspace_id=workspace_id, ticket_id=ticket_id
    )
    return [ConversationResponse.model_validate(item) for item in items]


@router.post(
    "/conversations/{conversation_id}/messages", response_model=MessageResponse, status_code=201
)
def create_outbound_message(
    workspace_id: str,
    ticket_id: str,
    conversation_id: str,
    payload: MessageCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    item = CommunicationService(db).create_outbound_message(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        actor_user_id=membership.user_id,
        body=payload.body,
    )
    return MessageResponse.model_validate(item)


@router.post(
    "/conversations/{conversation_id}/messages/inbound",
    response_model=MessageResponse,
    status_code=201,
)
def record_inbound_message(
    workspace_id: str,
    ticket_id: str,
    conversation_id: str,
    payload: InboundMessageCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> MessageResponse:
    item = CommunicationService(db).create_inbound_message(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        actor_user_id=membership.user_id,
        body=payload.body,
        external_message_ref=payload.external_message_ref,
    )
    return MessageResponse.model_validate(item)


@router.get(
    "/conversations/{conversation_id}/messages", response_model=list[MessageResponse]
)
def list_messages(
    workspace_id: str,
    ticket_id: str,
    conversation_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> list[MessageResponse]:
    items = CommunicationService(db).list_messages(
        workspace_id=workspace_id, ticket_id=ticket_id, conversation_id=conversation_id
    )
    return [MessageResponse.model_validate(item) for item in items]


@router.post("/internal-notes", response_model=InternalNoteResponse, status_code=201)
def create_internal_note(
    workspace_id: str,
    ticket_id: str,
    payload: InternalNoteCreateRequest,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_INTERNAL_COMMENT)),
    db: Session = Depends(get_db),
) -> InternalNoteResponse:
    item = CommunicationService(db).create_note(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        actor_user_id=membership.user_id,
        body=payload.body,
    )
    return InternalNoteResponse.model_validate(item)


@router.get("/internal-notes", response_model=list[InternalNoteResponse])
def list_internal_notes(
    workspace_id: str,
    ticket_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_INTERNAL_COMMENT)),
    db: Session = Depends(get_db),
) -> list[InternalNoteResponse]:
    items = CommunicationService(db).list_notes(workspace_id=workspace_id, ticket_id=ticket_id)
    return [InternalNoteResponse.model_validate(item) for item in items]


async def _bounded_upload(file: UploadFile) -> bytes:
    # Read one byte beyond the limit so an oversized body is rejected,
    # rather than silently truncated and accepted.
    return await file.read(MAX_ATTACHMENT_BYTES + 1)


@router.post(
    "/conversations/{conversation_id}/messages/{message_id}/attachments",
    response_model=AttachmentResponse,
    status_code=201,
)
async def attach_to_message(
    workspace_id: str,
    ticket_id: str,
    conversation_id: str,
    message_id: str,
    file: UploadFile = File(...),
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_UPDATE)),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    content = await _bounded_upload(file)
    item = CommunicationService(db).attach_to_message(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        conversation_id=conversation_id,
        message_id=message_id,
        actor_user_id=membership.user_id,
        filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return AttachmentResponse.model_validate(item)


@router.post(
    "/internal-notes/{note_id}/attachments", response_model=AttachmentResponse, status_code=201
)
async def attach_to_internal_note(
    workspace_id: str,
    ticket_id: str,
    note_id: str,
    file: UploadFile = File(...),
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_INTERNAL_COMMENT)),
    db: Session = Depends(get_db),
) -> AttachmentResponse:
    content = await _bounded_upload(file)
    item = CommunicationService(db).attach_to_note(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        note_id=note_id,
        actor_user_id=membership.user_id,
        filename=file.filename or "attachment",
        content_type=file.content_type or "application/octet-stream",
        content=content,
    )
    return AttachmentResponse.model_validate(item)


@router.get("/attachments/{attachment_id}")
def download_attachment(
    workspace_id: str,
    ticket_id: str,
    attachment_id: str,
    membership: WorkspaceMembership = Depends(require_permission(TICKETS_READ)),
    db: Session = Depends(get_db),
) -> Response:
    permissions = RbacRepository(db).permission_codes_for_role(membership.role_id)
    item = CommunicationService(db).get_attachment_for_ticket(
        workspace_id=workspace_id,
        ticket_id=ticket_id,
        attachment_id=attachment_id,
        allow_internal=TICKETS_INTERNAL_COMMENT in permissions,
    )
    return Response(
        content=item.content,
        media_type=item.content_type,
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(item.filename)}"},
    )
