import re
with open('tests/test_final_hardening.py', 'r') as f:
    code = f.read()

# Fix Admin
code = code.replace(
    '''    # Create Org Admin
    admin = User(
        email="admin_hardening@example.com",
        password_hash=get_password_hash("password"),
        full_name="Hardening Admin",
        tenant_role="ORG_ADMIN",
        organization_id=tenant_id,
        status="ACTIVE"
    )
    db.add(admin)''',
    '''    # Create or Get Org Admin
    admin = db.query(User).filter(User.email == "admin_hardening@example.com").first()
    if not admin:
        admin = User(
            email="admin_hardening@example.com",
            password_hash=get_password_hash("password"),
            full_name="Hardening Admin",
            tenant_role="ORG_ADMIN",
            organization_id=tenant_id,
            status="ACTIVE"
        )
        db.add(admin)'''
)

# Fix Callers
code = code.replace(
    '''    # Create 4 Telecallers
    callers = []
    for i in ["A", "B", "C", "D"]:
        caller = User(
            email=f"caller_{i}@example.com",
            password_hash=get_password_hash("password"),
            full_name=f"Caller {i}",
            tenant_role="TELECALLER",
            organization_id=tenant_id,
            status="ACTIVE"
        )
        db.add(caller)
        callers.append(caller)''',
    '''    # Create 4 Telecallers
    callers = []
    for i in ["A", "B", "C", "D"]:
        caller_email = f"caller_{i}@example.com"
        caller = db.query(User).filter(User.email == caller_email).first()
        if not caller:
            caller = User(
                email=caller_email,
                password_hash=get_password_hash("password"),
                full_name=f"Caller {i}",
                tenant_role="TELECALLER",
                organization_id=tenant_id,
                status="ACTIVE"
            )
            db.add(caller)
        callers.append(caller)'''
)

with open('tests/test_final_hardening.py', 'w') as f:
    f.write(code)
print('Fixed test users')
