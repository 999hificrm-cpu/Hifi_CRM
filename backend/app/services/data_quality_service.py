import logging
from sqlalchemy.orm import Session
from app.models.lead import Lead
from app.models.contact import Contact
from app.models.company import Company
from app.models.data_quality import DataQualityJob, DataQualityIssue
from app.models.base import generate_uuid
import re

logger = logging.getLogger(__name__)

def is_valid_email(email: str) -> bool:
    if not email:
        return False
    return re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", email) is not None

def is_valid_phone(phone: str) -> bool:
    if not phone:
        return False
    digits = re.sub(r"\D", "", phone)
    return len(digits) >= 10

def scan_organization_data_quality(db: Session, organization_id: str):
    logger.info(f"Scanning data quality for org {organization_id}")
    job = DataQualityJob(id=generate_uuid(), organization_id=organization_id, status="RUNNING")
    db.add(job)
    db.commit()
    
    issues_created = 0

    # Scan Leads for missing emails and phones
    leads = db.query(Lead).filter(Lead.organization_id == organization_id, Lead.status != "ARCHIVED").all()
    for lead in leads:
        if lead.contact_email and not is_valid_email(lead.contact_email):
            issue = DataQualityIssue(
                organization_id=organization_id, job_id=job.id, entity_type="LEAD", entity_id=lead.id,
                issue_type="INVALID_EMAIL", severity="WARNING", details_json={"invalid_value": lead.contact_email}
            )
            db.add(issue)
            issues_created += 1

        if lead.contact_phone and not is_valid_phone(lead.contact_phone):
            issue = DataQualityIssue(
                organization_id=organization_id, job_id=job.id, entity_type="LEAD", entity_id=lead.id,
                issue_type="INVALID_PHONE", severity="WARNING", details_json={"invalid_value": lead.contact_phone}
            )
            db.add(issue)
            issues_created += 1
            
        if not lead.contact_email and not lead.contact_phone:
             issue = DataQualityIssue(
                organization_id=organization_id, job_id=job.id, entity_type="LEAD", entity_id=lead.id,
                issue_type="MISSING_CONTACT_INFO", severity="CRITICAL", details_json={"message": "Lead has no email or phone"}
            )
             db.add(issue)
             issues_created += 1

    job.issues_found = issues_created
    job.status = "COMPLETED"
    db.commit()
    logger.info(f"Data quality scan completed for org {organization_id}. Found {issues_created} issues.")
    return issues_created
