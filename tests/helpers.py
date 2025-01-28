from ctms import models


def assign_role(db, api_client_id, role_name):
    role = db.query(models.Roles).filter_by(name=role_name).first()
    if not role:
        role = models.Roles(name=role_name)
        db.add(role)
        db.commit()

    api_client_role = models.ApiClientRoles(api_client_id=api_client_id, role_id=role.id)
    db.add(api_client_role)
    db.commit()
