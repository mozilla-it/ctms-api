from .addons import AddOnsInSchema, AddOnsSchema, UpdatedAddOnsInSchema
from .api_client import ApiClientSchema
from .bulk import BulkRequestSchema
from .contact import (
    ContactInSchema,
    ContactPatchSchema,
    ContactPutSchema,
    ContactSchema,
    CTMSBulkResponse,
    CTMSResponse,
    CTMSSingleResponse,
    IdentityResponse,
)
from .email import (
    EmailInSchema,
    EmailPatchSchema,
    EmailPutSchema,
    EmailSchema,
    UpdatedEmailPutSchema,
)
from .fxa import (
    FirefoxAccountsInSchema,
    FirefoxAccountsSchema,
    UpdatedFirefoxAccountsInSchema,
)
from .mofo import MozillaFoundationInSchema, MozillaFoundationSchema
from .newsletter import NewsletterInSchema, NewsletterSchema, NewsletterTableSchema
from .waitlist import (
    RelayWaitlistInSchema,
    VpnWaitlistInSchema,
    WaitlistInSchema,
    WaitlistSchema,
    WaitlistTableSchema,
)
from .web import (
    BadRequestResponse,
    NotFoundResponse,
    TokenResponse,
    UnauthorizedResponse,
)
