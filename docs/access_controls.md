# CTMS Access Control Overview

CTMS uses **Role-Based Access Control (RBAC)** to manage access to resources. The system consists of:
- **Permissions**: Define specific actions that can be performed.
- **Roles**: Group permissions together for easier management.
- **API Clients**: The oAuth clients that authenticate and receive roles.

See the [CTMS CLI](./cli.md) documentation on how to manage API clients, roles, and permissions.

---

## Permissions

**Permissions** define **what actions can be performed** within the system. They are the
**lowest level of access control** and must be assigned to **roles**.

### Key Characteristics
- Permissions are not assigned directly to API clients.
- Roles are the only way permissions are granted to clients.
- A single permission can be used in multiple roles.

### Example Permissions
| Permission Name | Description |
|----------------|-------------|
| `manage_contacts` | Grants the ability to create, edit, and delete contacts |
| `view_updates` | Allows access to updated contacts |

---

## Roles

**Roles** are collections of **permissions**. Assigning a role to an API client grants them all the
permissions within that role.

### Key Characteristics
- Roles group multiple permissions together.
- API clients receive roles, not individual permissions.
- A single API client can have multiple roles.

### Example Roles
| Role Name | Assigned Permissions |
|-----------|----------------------|
| `admin` | `manage_contacts`, `view_updates` |
| `viewer` | `view_updates` |

---

## API Clients

**API Clients** represent oAuth clients that authenticate and receive **roles**.

### Key Characteristics
- Authenticate using oAuth2 client credentials.
- Receive access via assigned roles.
- Can be enabled or disabled as needed.
- Secrets can be rotated for security.

---

## Authentication: Obtaining an OAuth Token

API clients authenticate using the **OAuth2 Client Credentials Flow**.

After **creating a client**, use the following `curl` request to obtain an access token:

```sh
curl --user <client_id>:<client_secret> -F grant_type=client_credentials <server_prefix>/token
```

The JSON response will have an access token, such as:

```json
{
    "access_token": "<token>",
    "token_type": "bearer",
    "expires_in": <time_in_seconds>
}
```

This can be used to access the API, such as:

```sh
curl --oauth2-bearer <token> <server_prefix>/ctms?primary_email=<email>
```

## Protecting Endpoints in FastAPI

To protect an API endpoint and **require a specific permission**, use the **`with_permission`**
helper from `ctms.permissions`.

### Usage

Using `"delete_contact"` as the example **permission**.

1. Import `with_permission` in your FastAPI app:
   ```python
   from ctms.permissions import with_permission
   from fastapi import Depends, APIRouter
   from typing import Annotated
   ```

2. Protect an API route by requiring a permission (made up example):
   ```python
   router = APIRouter()

   @router.delete("/contacts/{contact_id}")
   def delete_contact(
       contact_id: int,
       db: Annotated[Session, Depends(get_db)],
       _: Annotated[bool, Depends(with_permission("delete_contact"))],
   ):
       return {"message": f"Contact {contact_id} deleted"}
   ```

- The `with_permission("delete_contact")` ensures that the client making the request has the `delete_contact` permission.
- If the client does not have the required permission, FastAPI returns a 403 Forbidden response.
