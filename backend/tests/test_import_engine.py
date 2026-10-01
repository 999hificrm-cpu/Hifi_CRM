import os
import pytest
from pathlib import Path
from app.models.pipeline import PipelineStage
from app.models.lead import Lead
from app.models.company import Company
from app.models.contact import Contact
from app.services.import_service import preview_import_file, execute_import_job
from app.models.import_job import ImportJob, ImportRowError


def test_import_engine_pipeline_immutability(db_session, tenant_a_fixture, tmp_path):
    org = tenant_a_fixture["org"]
    admin = tenant_a_fixture["admin_user"]
    test_csv_path = tmp_path / "test_1000_leads.csv"
    header = "Company Name,Contact Person,Email Address,Phone Number,City,Industry,Opportunity Title\n"
    rows = [
        f"Import Company {index},Contact {index},contact{index}@example.com,98765{index:05d},Mumbai,Services,Opportunity {index}\n"
        for index in range(1000)
    ]
    test_csv_path.write_text(header + "".join(rows), encoding="utf-8")

    # Count initial pipeline stages
    initial_stages_count = db_session.query(PipelineStage).join(PipelineStage.pipeline).filter(
        PipelineStage.pipeline.has(organization_id=org.id)
    ).count()
    assert initial_stages_count == 7  # Canonical 7 stages seeded

    # 1. Preview file
    preview = preview_import_file(str(test_csv_path), "CSV")
    assert preview["total_detected_rows"] == 1000
    assert "Company Name" in preview["detected_headers"]
    assert preview["suggested_mappings"]["Company Name"] == "company_name"
    assert preview["suggested_mappings"]["Contact Person"] == "contact_name"

    # 2. Create and execute import job
    mapping = {
        "Company Name": "company_name",
        "Contact Person": "contact_name",
        "Email Address": "contact_email",
        "Phone Number": "contact_phone",
        "City": "city",
        "Industry": "industry",
        "Opportunity Title": "title"
    }

    job = ImportJob(
        organization_id=org.id,
        uploaded_by=admin.id,
        job_type="TENANT_LEADS",
        file_name="test_1000_leads.csv",
        file_type="CSV",
        file_path=str(test_csv_path),
        column_mapping=mapping,
        status="PENDING"
    )
    db_session.add(job)
    db_session.commit()

    job_id = job.id
    # Execute import synchronously for testing
    completed_job = execute_import_job(db_session, job_id)
    assert completed_job.status == "COMPLETED"
    assert completed_job.successful_rows == 1000
    assert completed_job.total_rows == 1000
    assert completed_job.error_rows == 0

    # 3. VERIFY PIPELINE IMMUTABILITY (Crucial requirement from prompt)
    final_stages_count = db_session.query(PipelineStage).join(PipelineStage.pipeline).filter(
        PipelineStage.pipeline.has(organization_id=org.id)
    ).count()
    assert final_stages_count == initial_stages_count  # STRICTLY UNCHANGED: Still 7 stages!

    # 4. Verify leads, companies, and contacts were created
    leads_count = db_session.query(Lead).filter(Lead.organization_id == org.id).count()
    assert leads_count >= 1000

    companies_count = db_session.query(Company).filter(Company.organization_id == org.id).count()
    assert companies_count >= 1000

    contacts_count = db_session.query(Contact).filter(Contact.organization_id == org.id).count()
    assert contacts_count >= 1000
