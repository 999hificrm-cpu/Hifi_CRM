import pytest
import io
from fastapi.testclient import TestClient
from app.main import app
from app.models.user import User
from app.models.global_registry import GlobalCompany
from app.models.global_people import GlobalPerson
from app.schemas.global_registry import GlobalCompanyUpdate
from app.schemas.global_people import GlobalPersonUpdate
from app.services.global_service import update_global_company
from app.services.global_people_service import update_global_person
from app.core.security import get_password_hash, create_access_token


def test_data_entry_user_login(client, db_session):
    # Ensure data entry user exists in test db session
    email = "dataentry_test@jarvis.local"
    user = db_session.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            full_name="Test Data Operator",
            platform_role="DATA_ENTRY",
            password_hash=get_password_hash("DataEntry@2026"),
            status="ACTIVE"
        )
        db_session.add(user)
        db_session.commit()

    assert user.is_data_entry is True
    assert user.is_super_admin is False

    res = client.post("/api/v1/auth/login", json={"email": email, "password": "DataEntry@2026"})
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["platform_role"] == "DATA_ENTRY"
    assert data["user"]["is_data_entry"] is True


def test_edit_global_company_service(db_session):
    gc = GlobalCompany(
        registry_id="U99999MH2026PTC111111",
        legal_name="Initial Tech Corp Ltd",
        industry="Technology",
        city="Pune"
    )
    db_session.add(gc)
    db_session.commit()

    update_payload = GlobalCompanyUpdate(
        legal_name="Updated Quantum Tech Corp Ltd",
        city="Mumbai",
        phone="+91 98765 00000",
        industry="Artificial Intelligence"
    )
    updated = update_global_company(db=db_session, company_id=gc.id, data=update_payload)
    assert updated.legal_name == "Updated Quantum Tech Corp Ltd"
    assert updated.city == "Mumbai"
    assert updated.phone == "+91 98765 00000"
    assert updated.industry == "Artificial Intelligence"


def test_edit_global_person_service(db_session):
    gp = GlobalPerson(
        full_name="Kavita Deshmukh",
        designation="Engineering Lead",
        company_name="Apex Global",
        email="kavita@apex.com",
        seniority="Lead",
        department="Engineering"
    )
    db_session.add(gp)
    db_session.commit()

    update_payload = GlobalPersonUpdate(
        full_name="Kavita Deshmukh-Patil",
        designation="VP of Artificial Intelligence",
        seniority="VP",
        estimated_value=850000.0,
        city="Bengaluru"
    )
    updated = update_global_person(db=db_session, person_id=gp.id, data=update_payload)
    assert updated.full_name == "Kavita Deshmukh-Patil"
    assert updated.designation == "VP of Artificial Intelligence"
    assert updated.seniority == "VP"
    assert updated.estimated_value == 850000.0
    assert updated.city == "Bengaluru"


def test_strict_tabular_file_rejection(client, db_session, tenant_a_fixture):
    token = tenant_a_fixture["admin_token"]

    # 1. Reject Markdown file (.md)
    md_content = b"# This is markdown notes\n| Name | Company |\n| John | Acme |"
    res_md = client.post(
        "/api/v1/imports/upload",
        files={"file": ("leads.md", io.BytesIO(md_content), "text/markdown")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_md.status_code == 400
    assert "Invalid file format" in res_md.json()["detail"]

    # 2. Reject PDF file (.pdf)
    pdf_content = b"%PDF-1.4 dummy binary content"
    res_pdf = client.post(
        "/api/v1/imports/upload",
        files={"file": ("contract.pdf", io.BytesIO(pdf_content), "application/pdf")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_pdf.status_code == 400
    assert "Invalid file format" in res_pdf.json()["detail"]

    # 3. Accept valid CSV tabular file
    csv_content = b"Full Name,Company,Email,Phone\nRajesh Sharma,Solar Systems,rajesh@solar.in,+919811122233\n"
    res_csv = client.post(
        "/api/v1/imports/upload",
        files={"file": ("leads.csv", io.BytesIO(csv_content), "text/csv")},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res_csv.status_code == 200
    assert res_csv.json()["total_rows_estimate"] == 1
