from .addons import (
    AddOnsInSchema,
    AddOnsSchema,
    AddOnsTableSchema,
    UpdatedAddOnsInSchema,
)
from .api_client import ApiClientSchema
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
    EmailTableSchema,
    UpdatedEmailPutSchema,
)
from .fxa import (
    FirefoxAccountsInSchema,
    FirefoxAccountsSchema,
    FirefoxAccountsTableSchema,
    UpdatedFirefoxAccountsInSchema,
)
from .mofo import MozillaFoundationInSchema, MozillaFoundationSchema
from .newsletter import (
    NewsletterInSchema,
    NewsletterSchema,
    NewsletterTableSchema,
    UpdatedNewsletterInSchema,
)
from .vpn import (
    UpdatedVpnWaitlistInSchema,
    VpnWaitlistInSchema,
    VpnWaitlistSchema,
    VpnWaitlistTableSchema,
)
from .web import (
    BadRequestResponse,
    NotFoundResponse,
    TokenResponse,
    UnauthorizedResponse,
)
