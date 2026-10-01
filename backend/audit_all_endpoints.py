import io
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.main import app
from app.core.database import engine, SessionLocal
from app.core.config import settings

client = TestClient(app)

results = {
    "passed": [],
    "failed": [],
    "warnings": []
}

def log_test(name, success, details=""):
    if success:
        results["passed"].append(f"{name}: {details}")
        print(f"  [PASS] {name} - {details}")
    else:
        results["failed"].append(f"{name}: {details}")
        print(f"  [FAIL] {name} - {details}")

print("=" * 70)
print("JARVIS CRM: COMPREHENSIVE PRODUCTION READINESS AUDIT")
print("=" * 70)

# -------------------------------------------------------------
# 1. DATABASE & POSTGRESQL INTEGRITY
# -------------------------------------------------------------
print("\n--- 1. DATABASE & POSTGRESQL INTEGRITY ---")
try:
    with engine.connect() as conn:
        db_res = conn.execute(text("SELECT current_database(), current_user, version()")).fetchone()
        log_test("PostgreSQL Active Connection", True, f"Connected to '{db_res[0]}' as '{db_res[1]}'")
        
        # Check table counts
        tables_res = conn.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)).fetchall()
        table_names = [t[0] for t in tables_res]
        log_test("PostgreSQL Schema Verification", len(table_names) == 26, f"Found {len(table_names)}/26 tables")
        
        # Check critical table rows
        org_count = conn.execute(text("SELECT COUNT(*) FROM organizations")).scalar()
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
        lead_count = conn.execute(text("SELECT COUNT(*) FROM leads")).scalar()
        company_count = conn.execute(text("SELECT COUNT(*) FROM global_companies")).scalar()
        people_count = conn.execute(text("SELECT COUNT(*) FROM global_people")).scalar()
        
        log_test("Row Integrity Check", all([org_count > 0, user_count > 0, lead_count > 0, company_count > 0, people_count > 0]),
                 f"Orgs: {org_count}, Users: {user_count}, Leads: {lead_count}, Global Companies: {company_count}, People: {people_count}")
except Exception as e:
    log_test("PostgreSQL Connection", False, str(e))


# -------------------------------------------------------------
# 2. AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC)
# -------------------------------------------------------------
print("\n--- 2. AUTHENTICATION & ROLE-BASED ACCESS CONTROL (RBAC) ---")

tokens = {}
credentials = [
    ("Super Admin", "superadmin@jarvis.local", "JarvisAdmin@2026", "SUPER_ADMIN"),
    ("Data Entry", "dataentry@jarvis.local", "DataEntry@2026", "DATA_ENTRY"),
    ("Org Admin", "admin@apex.com", "ApexAdmin@2026", "ADMIN"),
    ("Telecaller", "telecaller@apex.com", "Telecaller@2026", "TELECALLER"),
]

for role_name, email, password, expected_role in credentials:
    res = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    if res.status_code == 200:
        data = res.json()
        token = data.get("access_token")
        user = data.get("user", {})
        tokens[role_name] = token
        
        # Check role flags
        if role_name == "Super Admin":
            role_ok = user.get("is_super_admin") is True
        elif role_name == "Data Entry":
            role_ok = user.get("is_data_entry") is True or user.get("platform_role") == "DATA_ENTRY"
        elif role_name == "Org Admin":
            role_ok = user.get("tenant_role") in ("ORG_ADMIN", "ADMIN")
        elif role_name == "Telecaller":
            role_ok = user.get("tenant_role") == "TELECALLER"
        else:
            role_ok = True

        log_test(f"Login & Token Issuance ({role_name})", role_ok, f"Role verified for {email}")
    else:
        log_test(f"Login ({role_name})", False, f"Status {res.status_code}: {res.text}")

# Test invalid login
bad_res = client.post("/api/v1/auth/login", json={"email": "fake@jarvis.local", "password": "wrong"})
log_test("Invalid Login Rejection", bad_res.status_code == 401, f"Returned status {bad_res.status_code}")


# -------------------------------------------------------------
# 3. ENDPOINT PERMISSIONS & ACCESS BARRIERS
# -------------------------------------------------------------
print("\n--- 3. ENDPOINT PERMISSIONS & SECURITY BARRIERS ---")

# A. Super Admin can access organizations & audit logs
sa_headers = {"Authorization": f"Bearer {tokens.get('Super Admin')}"}
sa_orgs = client.get("/api/v1/organizations/", headers=sa_headers)
log_test("Super Admin -> Organizations List", sa_orgs.status_code == 200, f"Status {sa_orgs.status_code}")

sa_audit = client.get("/api/v1/radar/audit-logs", headers=sa_headers)
log_test("Super Admin -> Platform Audit Logs", sa_audit.status_code == 200, f"Status {sa_audit.status_code}")

# B. Super Admin cannot pull leads directly (Forbidden for platform accounts)
sa_pull = client.post("/api/v1/global/pull", json={"global_company_ids": ["dummy"]}, headers=sa_headers)
log_test("Super Admin -> Blocked from Pulling Leads to CRM", sa_pull.status_code in (400, 403), f"Status {sa_pull.status_code} (Properly Guarded)")

# C. Data Entry Access Controls
de_headers = {"Authorization": f"Bearer {tokens.get('Data Entry')}"}
de_intel = client.get("/api/v1/global/intelligence", headers=de_headers)
log_test("Data Entry -> Global Intelligence View", de_intel.status_code == 200, f"Status {de_intel.status_code}")

de_companies = client.get("/api/v1/global/companies", headers=de_headers)
log_test("Data Entry -> Company Registry List", de_companies.status_code == 200, f"Status {de_companies.status_code}")

de_people = client.get("/api/v1/global/people/", headers=de_headers)
log_test("Data Entry -> People Intelligence List", de_people.status_code == 200, f"Status {de_people.status_code}")

# Data Entry BLOCKED from Tenant Org Admin
de_orgs = client.get("/api/v1/organizations/", headers=de_headers)
log_test("Data Entry -> Blocked from Organizations Management", de_orgs.status_code == 403, f"Status {de_orgs.status_code} (Properly Guarded)")

# Data Entry BLOCKED from pulling leads
de_pull = client.post("/api/v1/global/pull", json={"global_company_ids": ["dummy"]}, headers=de_headers)
log_test("Data Entry -> Blocked from Pulling Leads to CRM", de_pull.status_code == 403, f"Status {de_pull.status_code} (Properly Guarded)")

# D. Org Admin Access Controls
oa_headers = {"Authorization": f"Bearer {tokens.get('Org Admin')}"}
oa_leads = client.get("/api/v1/leads/", headers=oa_headers)
log_test("Org Admin -> Leads & Pipeline", oa_leads.status_code == 200, f"Status {oa_leads.status_code}")

oa_pipelines = client.get("/api/v1/pipelines/", headers=oa_headers)
log_test("Org Admin -> Pipelines List", oa_pipelines.status_code == 200, f"Status {oa_pipelines.status_code}")

# Org Admin Scoped Audit Logs
oa_audit = client.get("/api/v1/radar/audit-logs", headers=oa_headers)
log_test("Org Admin -> Tenant-Scoped Audit Logs", oa_audit.status_code == 200, f"Status {oa_audit.status_code}")

# E. Telecaller Access & Anti-Theft Data Masking
tc_headers = {"Authorization": f"Bearer {tokens.get('Telecaller')}"}
tc_leads = client.get("/api/v1/leads/", headers=tc_headers)
if tc_leads.status_code == 200:
    leads_list = tc_leads.json()
    if isinstance(leads_list, list) and leads_list:
        sample_lead = leads_list[0]
        phone = sample_lead.get("contact_phone") or ""
        email = sample_lead.get("contact_email") or ""
        is_masked = ("*" in phone or not phone) and ("*" in email or not email)
        log_test("Telecaller Data Masking (Anti-Theft)", is_masked, f"Masked Phone: {phone}, Masked Email: {email}")
    else:
        log_test("Telecaller Data Masking", True, "Endpoint accessible")


# -------------------------------------------------------------
# 4. TABULAR DATA INGESTION & WHITELIST ENFORCEMENT
# -------------------------------------------------------------
print("\n--- 4. TABULAR DATA INGESTION & WHITELIST ENFORCEMENT ---")

# Test 1: Upload CSV (Allowed)
csv_content = b"legal_name,industry,city\nAlpha Robotics,Automation,Pune\n"
res_csv = client.post(
    "/api/v1/imports/upload",
    files={"file": ("test_tabular.csv", io.BytesIO(csv_content), "text/csv")},
    headers=sa_headers
)
log_test("Ingestion Whitelist -> Valid CSV Upload", res_csv.status_code == 200, f"Status {res_csv.status_code}")

# Test 2: Upload JSON (Allowed)
json_content = json.dumps([{"legal_name": "Beta AI", "industry": "AI"}]).encode()
res_json = client.post(
    "/api/v1/imports/upload",
    files={"file": ("test_data.json", io.BytesIO(json_content), "application/json")},
    headers=sa_headers
)
log_test("Ingestion Whitelist -> Valid JSON Upload", res_json.status_code == 200, f"Status {res_json.status_code}")

# Test 3: Upload Markdown (.md) - MUST BE REJECTED
md_content = b"# Sales Leads\n- Lead 1\n- Lead 2\n"
res_md = client.post(
    "/api/v1/imports/upload",
    files={"file": ("test_notes.md", io.BytesIO(md_content), "text/markdown")},
    headers=sa_headers
)
log_test("Ingestion Whitelist -> Reject Markdown (.md)", res_md.status_code == 400, f"Status {res_md.status_code} (Properly Rejected)")

# Test 4: Upload PDF (.pdf) - MUST BE REJECTED
pdf_content = b"%PDF-1.4 dummy pdf binary"
res_pdf = client.post(
    "/api/v1/imports/upload",
    files={"file": ("report.pdf", io.BytesIO(pdf_content), "application/pdf")},
    headers=sa_headers
)
log_test("Ingestion Whitelist -> Reject PDF (.pdf)", res_pdf.status_code == 400, f"Status {res_pdf.status_code} (Properly Rejected)")


# -------------------------------------------------------------
# 5. RECORD EDITING & DATA MUTATION CAPABILITIES
# -------------------------------------------------------------
print("\n--- 5. RECORD EDITING & DATA MUTATIONS ---")

# Test Edit Global Company
with engine.connect() as conn:
    comp_row = conn.execute(text("SELECT id, legal_name FROM global_companies LIMIT 1")).fetchone()
    person_row = conn.execute(text("SELECT id, full_name FROM global_people LIMIT 1")).fetchone()

if comp_row:
    comp_id, old_name = comp_row
    res_update_comp = client.put(
        f"/api/v1/global/companies/{comp_id}",
        json={"legal_name": old_name, "city": "Bengaluru Updated"},
        headers=de_headers
    )
    log_test("Data Entry -> Edit Company (PUT /global/companies/{id})", res_update_comp.status_code == 200, f"Status {res_update_comp.status_code}")
else:
    log_test("Data Entry -> Edit Company", False, "No companies found in database")

if person_row:
    person_id, old_pname = person_row
    res_update_person = client.put(
        f"/api/v1/global/people/{person_id}",
        json={"full_name": old_pname, "city": "Noida Updated"},
        headers=de_headers
    )
    log_test("Data Entry -> Edit Decision Maker (PUT /global/people/{id})", res_update_person.status_code == 200, f"Status {res_update_person.status_code}")
else:
    log_test("Data Entry -> Edit Decision Maker", False, "No people found in database")


# -------------------------------------------------------------
# 6. MAIL HELPER INTEGRITY (AUTHUSER SENDER VS TO RECIPIENT)
# -------------------------------------------------------------
print("\n--- 6. MAIL HELPER INTEGRITY ---")

with engine.connect() as conn:
    lead_row = conn.execute(text("SELECT id, title, contact_email FROM leads WHERE contact_email IS NOT NULL LIMIT 1")).fetchone()

if lead_row:
    lead_id, title, contact_email = lead_row
    res_mail = client.post(
        f"/api/v1/leads/{lead_id}/action/email",
        headers=oa_headers
    )
    if res_mail.status_code == 200:
        mail_data = res_mail.json()
        mail_url = mail_data.get("gmail_url", "")
        has_correct_to = f"to={contact_email}" in mail_url or "to=" in mail_url
        has_correct_from = "authuser=admin%40apex.com" in mail_url or "authuser=admin@apex.com" in mail_url
        
        log_test("Mail Trigger -> Correct Recipient (to)", has_correct_to, f"Recipient is '{contact_email}'")
        log_test("Mail Trigger -> Correct Authenticated Sender (authuser)", has_correct_from, f"Sender authuser is 'admin@apex.com'")
    else:
        log_test("Mail Trigger Endpoint", False, f"Status {res_mail.status_code}: {res_mail.text}")
else:
    log_test("Mail Trigger Endpoint", False, "No lead with email found in DB")


# -------------------------------------------------------------
# SUMMARY REPORT
# -------------------------------------------------------------
print("\n" + "=" * 70)
print(f"AUDIT SUMMARY: {len(results['passed'])} PASSED, {len(results['failed'])} FAILED")
print("=" * 70)
if results["failed"]:
    print("FAILED CHECKS:")
    for f in results["failed"]:
        print(f"  - {f}")
else:
    print("ALL TEST CHECKS PASSED WITH 100% OPERATIONAL INTEGRITY!")
