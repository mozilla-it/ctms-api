from .addons import AddOnsInSchema, AddOnsSchema, AddOnsTableSchema
from .api_client import ApiClientSchema
from .contact import (
    ContactInSchema,
    ContactPatchSchema,
    ContactPutSchema,
    ContactSchema,
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
)
from .fxa import (
    FirefoxAccountsInSchema,
    FirefoxAccountsSchema,
    FirefoxAccountsTableSchema,
)
from .mofo import MozillaFoundationInSchema, MozillaFoundationSchema
from .newsletter import NewsletterInSchema, NewsletterSchema, NewsletterTableSchema
from .vpn import VpnWaitlistInSchema, VpnWaitlistSchema, VpnWaitlistTableSchema
from .web import (
    BadRequestResponse,
    NotFoundResponse,
    TokenResponse,
    UnauthorizedResponse,
)
