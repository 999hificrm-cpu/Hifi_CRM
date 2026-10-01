import logging
from app.core.database import SessionLocal, Base, engine
from app.tasks.daily_tasks import dynamic_cleanup_and_deduplication
from app.models.organization import Organization
from app.models.user import User
from app.models.pipeline import Pipeline, PipelineStage
from app.models.lead import Lead
from app.models.dedupe import DedupeCandidate
from app.models.data_quality import DataQualityIssue
from app.models.base import generate_uuid

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_test():
    # Ensure tables are created
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    try:
        # Create a test organization
        org_id = generate_uuid()
        org = Organization(id=org_id, name="Test Org", slug=f"test-{org_id[:8]}", status="ACTIVE", timezone="UTC", currency="USD")
        db.add(org)
        
        # Create a test user
        user_id = generate_uuid()
        user = User(id=user_id, organization_id=org_id, full_name="Test User", email="testuser@example.com", password_hash="hash", status="ACTIVE")
        db.add(user)
        
        # Create pipeline and stage
        pipe_id = generate_uuid()
        pipe = Pipeline(id=pipe_id, organization_id=org_id, name="Test Pipe", is_default=True, status="ACTIVE")
        db.add(pipe)
        
        stage_id = generate_uuid()
        stage = PipelineStage(id=stage_id, pipeline_id=pipe_id, name="New", code="NEW", order_index=1, is_won=False, is_lost=False)
        db.add(stage)
        db.commit()

        # Seed problematic data for Dedupe and Data Quality
        
        # 1. Exact Duplicate Phone Leads
        lead1 = Lead(id=generate_uuid(), organization_id=org_id, pipeline_stage_id=stage_id, title="Lead A", source="TEST", status="OPEN", priority="MEDIUM", score=10, currency="USD", contact_phone="9876543210")
        lead2 = Lead(id=generate_uuid(), organization_id=org_id, pipeline_stage_id=stage_id, title="Lead B", source="TEST", status="OPEN", priority="MEDIUM", score=10, currency="USD", contact_phone="9876543210")
        db.add(lead1)
        db.add(lead2)
        
        # 2. Data Quality Issues (Invalid email, invalid phone)
        lead3 = Lead(id=generate_uuid(), organization_id=org_id, pipeline_stage_id=stage_id, title="Lead C", source="TEST", status="OPEN", priority="MEDIUM", score=10, currency="USD", contact_email="invalid-email-no-domain", contact_phone="123")
        db.add(lead3)
        
        # 3. Data Quality Issue (Missing contact info completely)
        lead4 = Lead(id=generate_uuid(), organization_id=org_id, pipeline_stage_id=stage_id, title="Lead D", source="TEST", status="OPEN", priority="MEDIUM", score=10, currency="USD")
        db.add(lead4)
        
        db.commit()
        
        # Run Celery task function synchronously
        logger.info("Executing dynamic_cleanup_and_deduplication...")
        dynamic_cleanup_and_deduplication()
        
        # Assert results
        dedupe_candidates = db.query(DedupeCandidate).filter(DedupeCandidate.organization_id == org_id).all()
        logger.info(f"Found {len(dedupe_candidates)} dedupe candidates (Expected: 1)")
        for c in dedupe_candidates:
            logger.info(f" - Candidate: Lead A vs Lead B, match_basis: {c.match_basis}")
            
        dq_issues = db.query(DataQualityIssue).filter(DataQualityIssue.organization_id == org_id).all()
        logger.info(f"Found {len(dq_issues)} data quality issues (Expected: 3)")
        for iss in dq_issues:
            logger.info(f" - Issue on Lead {iss.entity_id}: {iss.issue_type}, Severity: {iss.severity}")
            
        assert len(dedupe_candidates) >= 1
        assert len(dq_issues) >= 3
        logger.info("TEST PASSED!")

    except Exception as e:
        logger.error(f"TEST FAILED: {e}")
    finally:
        # Cleanup
        db.execute(Organization.__table__.delete().where(Organization.id == org_id))
        db.commit()
        db.close()

if __name__ == "__main__":
    run_test()
