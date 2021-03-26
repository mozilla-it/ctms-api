from .addons import AddOnsInSchema, AddOnsSchema
from .api_client import ApiClientSchema
from .contact import (
    ContactInSchema,
    ContactPutSchema,
    ContactSchema,
    CTMSResponse,
    CTMSSingleResponse,
    IdentityResponse,
)
from .email import EmailInSchema, EmailPutSchema, EmailSchema
from .fxa import FirefoxAccountsInSchema, FirefoxAccountsSchema
from .newsletter import NewsletterInSchema, NewsletterSchema
from .vpn import VpnWaitlistInSchema, VpnWaitlistSchema
from .web import (
    BadRequestResponse,
    NotFoundResponse,
    TokenResponse,
    UnauthorizedResponse,
)
