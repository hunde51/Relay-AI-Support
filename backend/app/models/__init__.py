# Import order matters — base first, then models with no FK deps,
# then models that reference others. This ensures SQLAlchemy sees all
# tables before relationships are resolved.

from app.models.base import Base, TimestampMixin, make_id, utc_now  # noqa: F401

from app.models.org import (  # noqa: F401
    OrganizationORM,
    UserORM,
    OrganizationSettingsORM,
    NotificationSettingsORM,
    IntegrationORM,
)
from app.models.customer import CustomerORM  # noqa: F401
from app.models.ticket import (  # noqa: F401
    Ticket,
    TicketStatus,
    TicketPriority,
    TicketCategory,
    TicketORM,
    TicketMessageORM,
    TicketEventORM,
    TicketAssignmentORM,
    TagORM,
    TicketTagORM,
)
from app.models.knowledge import (  # noqa: F401
    KnowledgeSourceORM,
    KnowledgeDocumentORM,
    KnowledgeChunkORM,
    KnowledgeIngestionJobORM,
)
from app.models.ai import (  # noqa: F401
    AIRunORM,
    AIStepORM,
    AIToolCallORM,
    AISuggestedActionORM,
    AIResponseORM,
    AIToolDefinitionORM,
)
from app.models.api_key import ApiKeyORM  # noqa: F401
from app.models.audit import AuditLogORM, NotificationORM  # noqa: F401
