# **📖 CTMS CLI: Managing API Clients, Roles, and Permissions**

The **CTMS CLI** provides a command-line interface for managing API clients, roles, and permissions
within the system. It allows administrators to control access by defining **permissions**, assigning
**permissions** to **roles**, and granting **roles to API clients**.

This document outlines how to use the CTMS CLI to manage these entities.

## Confirmation Prompts for Destructive Actions

To prevent accidental data loss, all destructive operations (delete, revoke, disable, rotate-secret)
will prompt for confirmation before proceeding. You can bypass these prompts by using the `--yes` or `-y` 
flag when running these commands, which is especially useful for scripting or automation.

Example:
```sh
# With confirmation prompt:
ctms-cli clients delete id_client123

# Bypass confirmation prompt:
ctms-cli clients delete --yes id_client123
```

## Permissions

### Listing All Permissions
To see all available permissions:
```sh
ctms-cli permissions list
```

### Adding a New Permission
Permissions control what actions a **role** is allowed to perform. To create a new permission, use:

```sh
ctms-cli permissions create <permission_name> "<description>"
```

### Deleting a Permission
Delete the permission from the database. If the permission is assigned to a **role**, the permission
will need to be revoked from the **role** first. The CLI will output the commands needed to be
performed. 
```sh
ctms-cli permissions delete <permission_name>
```

A confirmation prompt will appear before deletion.

## Roles

### Listing All Permissions
To see all available roles:
```sh
ctms-cli roles list
```

### Showing Role Details
To view a role’s permissions and assigned API clients:
```sh
ctms-cli roles show <role_name>
```

### Adding a New Role
Roles define **groups of permissions** that can be assigned to **API clients**.

To create a new role, use:
```sh
ctms-cli roles create <role_name> "<description>"
```

### Granting Permissions to a Role
Assign a permission to a role:
```sh
ctms-cli roles grant <role_name> <permission_name>
```

### Revoking a Permission from a Role
If you need to remove a permission from a role:
```sh
ctms-cli roles revoke <role_name> <permission_name>
```

A confirmation prompt will appear before the permission is revoked.

### Deleting a Role
Delete the role from the database. If the role is assigned to an **API client**, the role will need
to be revoked from the **API client** first. The CLI will output the commands needed to be performed.
```sh
ctms-cli roles delete <role_name>
```

A confirmation prompt will appear before deletion.

## API Clients

### Listing All API Clients
To see all available API clients:
```sh
ctms-cli clients list
```

### Showing API Client Details
To check an API client’s assigned roles and status:
```sh
ctms-cli clients show <client_id>
```

### Adding a New API Client
API clients are entities that authenticate and are **assigned roles**.

To create a new API client:
```sh
ctms-cli clients create <client_id> <email>
```

The `client_id` must start with `"id_"` and only use alphanumeric characters plus `"-"`, `"_"`, or
`"."`.

This command will output the generated **client ID** and **client secret** that is used to get an
oAuth token needed to access the CTMS API. The credentials and instructions will be printed out to
the console. Be sure to save the credentials in a secure location.

### Rotate the API Client Secret
When needed, the API client secret can be rotated:
```sh
ctms-cli clients rotate-secret <client_id>
```

A confirmation prompt will appear before rotating the secret.

The command will print out the new API client credentials to the console.

### Granting a Role to an API Client
To assign a role to an API client:
```sh
ctms-cli clients grant <client_id> <role_name>
```

### Revoking a Role from an API Client
To remove a role from an API client:
```sh
ctms-cli clients revoke <client_id> <role_name>
```

A confirmation prompt will appear before the role is revoked.

### Enabling / Disabling an API Client
Enable or disable an API client:
```sh
ctms-cli clients enable <client_id>
ctms-cli clients disable <client_id>
```

When disabling a client, a confirmation prompt will appear.

### Deleting an API Client
To delete an API client from the database:
```sh
ctms-cli clients delete <client_id>
```

A confirmation prompt will appear before deletion.
