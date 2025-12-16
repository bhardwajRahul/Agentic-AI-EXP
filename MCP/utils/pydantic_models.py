"""Pydantic models for Gmail API tools"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, validator


class SendEmailRequest(BaseModel):
    """Send email request"""

    recipient_id: EmailStr = Field(
        ..., description="Recipient email", pattern=r"[^@]+@[^@]+\.[^@]+"
    )
    subject: str = Field(..., min_length=1, description="Email subject")
    message: str = Field(..., min_length=1, description="Email body")


class SendEmailResponse(BaseModel):
    """Send email response"""

    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class EmailAddress(BaseModel):
    """Email address with validation"""

    email: EmailStr


class EmailResponse(BaseModel):
    """Email response"""

    success: bool
    error: Optional[str] = None


class UnreadEmailsRequest(BaseModel):
    """Get unread emails request"""

    date: int = Field(10, ge=1, le=365, description="Days to look back")
    max_results: int = Field(20, ge=1, le=500, description="Max results")


class EmailMetadata(BaseModel):
    """Email metadata structure"""

    id: str
    thread_id: str
    snippet: str
    labels: List[str]
    size: int
    internal_date: Optional[str]
    subject: str
    from_: str = Field(..., alias="from")
    date: str
    to: str

    class Config:
        populate_by_name = True


class UnreadEmailsResponse(BaseModel):
    """Unread emails response"""

    count: int
    emails: List[EmailMetadata]


class LabelRequest(BaseModel):
    """Create/rename label request"""

    name: str = Field(..., min_length=1, max_length=225, description="Label name")

    @validator("name")
    def validate_label_name(cls, v):
        if "/" in v and v.count("/") > 5:
            raise ValueError("Label name cannot have more than 5 levels")
        return v


class LabelResponse(BaseModel):
    """Label operation response"""

    success: bool
    label_id: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


class LabelInfo(BaseModel):
    """Label information"""

    id: str
    name: str
    type: str


class ListLabelsResponse(BaseModel):
    """List labels response"""

    count: int
    labels: List[LabelInfo]
    error: Optional[str] = None


class ApplyLabelRequest(BaseModel):
    """Apply/remove label request"""

    email_id: str = Field(..., description="Message ID")
    label_id: str = Field(..., description="Label ID")


class DraftRequest(BaseModel):
    """Create draft request"""

    recipient_id: EmailStr
    subject: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)


class DraftInfo(BaseModel):
    """Draft information"""

    id: str
    subject: str
    to: str


class ListDraftsResponse(BaseModel):
    """List drafts response"""

    count: int
    drafts: List[DraftInfo]
    error: Optional[str] = None


class BatchArchiveRequest(BaseModel):
    """Batch archive request"""

    query: str = Field(..., description="Gmail search query")
    max_emails: int = Field(100, ge=1, le=500, description="Max emails to archive")


class BatchArchiveResponse(BaseModel):
    """Batch archive response"""

    success: bool
    archived_count: int = 0
    total_found: int = 0
    message: Optional[str] = None
    error: Optional[str] = None


class StandardResponse(BaseModel):
    """Standard success/error response"""

    success: bool
    error: Optional[str] = None


class EmailIdRequest(BaseModel):
    """Email ID request for single email operations"""

    email_id: str = Field(..., min_length=1, description="Gmail message ID")


class ReadEmailResponse(BaseModel):
    """Read email response"""

    content: str
    subject: str
    from_: str = Field(..., alias="from")
    to: str
    date: str
    error: Optional[str] = None

    class Config:
        populate_by_name = True


class DraftResponse(BaseModel):
    """Draft creation response"""

    success: bool
    draft_id: Optional[str] = None
    error: Optional[str] = None


class FilterInfo(
    BaseModel
):  # they are not directly used but use in other filers classes
    """Filter information structure"""

    id: str
    criteria: dict
    action: dict


class ListFiltersResponse(BaseModel):
    """List filters response"""

    count: int
    filters: List[FilterInfo]
    error: Optional[str] = None


class FilterIdRequest(BaseModel):
    """Filter ID request"""

    filter_id: str = Field(..., min_length=1, description="Filter ID")


class SearchEmailsRequest(BaseModel):
    """Search emails request"""

    query: str = Field(..., min_length=1, description="Gmail search query")
    max_results: Optional[int] = Field(None, ge=1, le=500, description="Max results")


class SearchEmailsResponse(BaseModel):
    """Search emails response"""

    count: int
    emails: List[dict]
    error: Optional[str] = None


class FolderRequest(BaseModel):
    """Create folder request"""

    name: str = Field(..., min_length=1, max_length=225, description="Folder name")


class FolderResponse(BaseModel):
    """Folder operation response"""

    success: bool
    folder_id: Optional[str] = None
    name: Optional[str] = None
    error: Optional[str] = None


class MoveToFolderRequest(BaseModel):
    """Move email to folder request"""

    email_id: str = Field(..., min_length=1, description="Gmail message ID")
    folder_id: str = Field(..., min_length=1, description="Folder/Label ID")


class FolderInfo(BaseModel):
    """Folder information"""

    id: str
    name: str


class ListFoldersResponse(BaseModel):
    """List folders response"""

    count: int
    folders: List[FolderInfo]
    error: Optional[str] = None


class RenameLabelRequest(BaseModel):
    """Rename label request"""

    label_id: str = Field(..., min_length=1, description="Label ID to rename")
    new_name: str = Field(
        ..., min_length=1, max_length=225, description="New label name"
    )

    @validator("new_name")
    def validate_label_name(cls, v):
        if "/" in v and v.count("/") > 5:
            raise ValueError("Label name cannot have more than 5 levels")
        return v


class ListArchivedRequest(BaseModel):
    """List archived emails request"""

    max_results: int = Field(100, ge=1, le=500, description="Max results")


class SearchByLabelRequest(BaseModel):
    """Search by label request"""

    label_id: str = Field(..., min_length=1, description="Label ID to search")


class SearchByLabelResponse(BaseModel):
    """Search by label response"""

    count: int
    messages: List[dict]
    error: Optional[str] = None


# ============================Google Chat Models=========================


class ListSpacesRequest(BaseModel):
    """List Google Chat spaces request"""

    page_size: int = Field(100, ge=1, le=1000, description="Max number of spaces")
    space_type: str = Field(
        "all",
        description="Type of spaces: 'all', 'room', or 'dm'",
        pattern="^(all|room|dm)$",
    )


class SpaceInfo(BaseModel):
    """Google Chat space information"""

    name: str
    display_name: str
    space_type: str


class ListSpacesResponse(BaseModel):
    """List spaces response"""

    count: int
    spaces: List[SpaceInfo]
    space_type_filter: str
    error: Optional[str] = None


class GetMessagesRequest(BaseModel):
    """Get messages from a space request"""

    space_id: str = Field(..., min_length=1, description="Space ID (spaces/...)")
    page_size: int = Field(50, ge=1, le=1000, description="Max number of messages")
    order_by: str = Field(
        "createTime desc",
        description="Sort order for messages",
        pattern="^createTime (asc|desc)$",
    )


class MessageInfo(BaseModel):
    """Google Chat message information"""

    name: str
    sender: str
    create_time: str
    text: str


class GetMessagesResponse(BaseModel):
    """Get messages response"""

    count: int
    space_name: str
    space_id: str
    messages: List[MessageInfo]
    error: Optional[str] = None


class SendMessageRequest(BaseModel):
    """Send message to a space request"""

    space_id: str = Field(..., min_length=1, description="Space ID (spaces/...)")
    message_text: str = Field(
        ..., min_length=1, max_length=4096, description="Message text content"
    )
    thread_key: Optional[str] = Field(
        None, description="Optional thread key for replies"
    )


class SendMessageResponse(BaseModel):
    """Send message response"""

    success: bool
    message_id: Optional[str] = None
    space_id: Optional[str] = None
    thread_id: Optional[str] = None
    error: Optional[str] = None


class SearchMessagesRequest(BaseModel):
    """Search messages request"""

    query: str = Field(..., min_length=1, description="Search query text")
    space_id: Optional[str] = Field(
        None, description="Optional space ID to limit search"
    )
    page_size: int = Field(25, ge=1, le=100, description="Max results per space")


class SearchMessageInfo(BaseModel):
    """Search result message information"""

    sender: str
    create_time: str
    text: str
    space_name: str


class SearchMessagesResponse(BaseModel):
    """Search messages response"""

    count: int
    query: str
    context: str
    messages: List[SearchMessageInfo]
    error: Optional[str] = None


# Google Calendar Models


class CalendarInfo(BaseModel):
    """Calendar information"""

    id: str
    summary: str
    description: Optional[str] = None
    timeZone: str
    accessRole: str
    primary: bool = False


class ListCalendarsResponse(BaseModel):
    """List calendars response"""

    status: str
    count: int
    calendars: List[CalendarInfo]
    error: Optional[str] = None


class ReminderItem(BaseModel):
    """Calendar reminder item"""

    method: str = Field(..., pattern="^(popup|email)$", description="Reminder method")
    minutes: int = Field(..., ge=0, le=40320, description="Minutes before event")


class GetEventsRequest(BaseModel):
    """Get events request"""

    calendar_id: str = Field("primary", min_length=1, description="Calendar ID")
    event_id: Optional[str] = Field(None, description="Specific event ID")
    time_min: Optional[str] = Field(None, description="Start time (RFC3339)")
    time_max: Optional[str] = Field(None, description="End time (RFC3339)")
    max_results: int = Field(25, ge=1, le=2500, description="Max number of events")
    query: Optional[str] = Field(None, description="Search query")
    detailed: bool = Field(False, description="Return detailed information")
    include_attachments: bool = Field(False, description="Include attachment info")


class GetEventsResponse(BaseModel):
    """Get events response"""

    status: str
    message: str
    event_id: Optional[str] = None
    error: Optional[str] = None


class CreateEventRequest(BaseModel):
    """Create event request"""

    summary: str = Field(..., min_length=1, max_length=1024, description="Event title")
    start_time: str = Field(..., min_length=1, description="Start time in IST")
    end_time: str = Field(..., min_length=1, description="End time in IST")
    calendar_id: str = Field("primary", min_length=1, description="Calendar ID")
    description: Optional[str] = Field(
        None, max_length=8192, description="Event description"
    )
    location: Optional[str] = Field(None, max_length=1024, description="Event location")
    attendees: Optional[List[str]] = Field(None, description="Attendee emails")
    attachments: Optional[List[str]] = Field(None, description="Drive file URLs/IDs")
    add_google_meet: bool = Field(False, description="Add Google Meet link")
    reminders: Optional[List[ReminderItem]] = Field(
        None, max_items=5, description="Custom reminders"
    )
    use_default_reminders: bool = Field(True, description="Use default reminders")
    transparency: Optional[str] = Field(
        None, pattern="^(opaque|transparent)$", description="Busy/free status"
    )

    @validator("attendees")
    def validate_attendees(cls, v):
        if v and len(v) > 200:
            raise ValueError("Maximum 200 attendees allowed")
        return v


class CreateEventResponse(BaseModel):
    """Create event response"""

    status: str
    message: str
    error: Optional[str] = None


class ModifyEventRequest(BaseModel):
    """Modify event request"""

    event_id: str = Field(..., min_length=1, description="Event ID to modify")
    calendar_id: str = Field("primary", min_length=1, description="Calendar ID")
    summary: Optional[str] = Field(None, max_length=1024, description="New event title")
    start_time: Optional[str] = Field(None, description="New start time in IST")
    end_time: Optional[str] = Field(None, description="New end time in IST")
    description: Optional[str] = Field(
        None, max_length=8192, description="New description"
    )
    location: Optional[str] = Field(None, max_length=1024, description="New location")
    attendees: Optional[List[str]] = Field(None, description="New attendee emails")
    add_google_meet: Optional[bool] = Field(None, description="Add/remove Google Meet")
    reminders: Optional[List[ReminderItem]] = Field(
        None, max_items=5, description="New reminders"
    )
    use_default_reminders: Optional[bool] = Field(
        None, description="Use default reminders"
    )
    transparency: Optional[str] = Field(
        None, pattern="^(opaque|transparent)$", description="Busy/free status"
    )

    @validator("attendees")
    def validate_attendees(cls, v):
        if v and len(v) > 200:
            raise ValueError("Maximum 200 attendees allowed")
        return v


class ModifyEventResponse(BaseModel):
    """Modify event response"""

    status: str
    message: str
    event_id: str
    error: Optional[str] = None


class DeleteEventRequest(BaseModel):
    """Delete event request"""

    event_id: str = Field(..., min_length=1, description="Event ID to delete")
    calendar_id: str = Field("primary", min_length=1, description="Calendar ID")


class DeleteEventResponse(BaseModel):
    """Delete event response"""

    status: str
    message: str
    event_id: str
    error: Optional[str] = None
