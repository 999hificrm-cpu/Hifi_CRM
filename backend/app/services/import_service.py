import os
import re
import csv
import uuid
import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.import_job import ImportJob, ImportRowError
from app.models.lead import Lead
from app.models.lead_history import LeadStageHistory
from app.models.company import Company
from app.models.contact import Contact
from app.models.global_registry import GlobalCompany, GlobalContact, GlobalCompanyContactMap
from app.models.global_people import GlobalPerson
from app.models.pipeline import PipelineStage
from app.models.user import User
from app.services.pipeline_service import get_first_stage, get_stage_by_id
from app.services.company_service import get_or_create_company
from app.services.contact_service import get_or_create_contact
from app.services.lead_qualification_service import classify_segment as classify_lead_segment

ALLOWED_TABULAR_EXTENSIONS = (".csv", ".xls", ".xlsx", ".xlsb", ".xlsm", ".parquet", ".json")

COLUMN_PATTERNS = {
    "id": [r"^id$", r"^uuid$", r"^unique_?id$", r"^identifier$"],
    "contact_phone": [r"company_contact_number", r"contact_?number", r"contactnumber", r"company_phone", r"phone", r"mobile", r"cell", r"contact_?no", r"tel", r"telephone"],
    "contact_email": [r"company_email", r"contact_?email", r"contactemail", r"email_?id", r"emailid", r"^email$", r"mail", r"e-mail"],
    "associated_companies": [r"associated_companies", r"associated_company", r"companies", r"other_companies", r"affiliations"],
    "company_name": [r"company_?name", r"companyname", r"^company$", r"organization", r"^org$", r"business", r"firm", r"account_?name", r"legal_?name"],
    "contact_name": [r"contact_?name", r"contactname", r"contact_?person", r"^contact$", r"^person$", r"^name$", r"director", r"decision_maker", r"client", r"full_?name", r"fullname"],
    "cin": [r"^cin$", r"cin_number", r"corporate_id", r"^company_?id$", r"^companyid$"],
    "registration_number": [r"registration_number", r"registration_no", r"reg_no", r"reg_num", r"registration"],
    "gst_number": [r"gst_number", r"gst_no", r"gstin", r"^gst$"],
    "address": [r"address", r"street", r"office_address", r"location_address"],
    "postal_code": [r"pincode", r"pin_code", r"postal_code", r"postalcode", r"^zip$", r"zipcode", r"postal"],
    "city": [r"^city$", r"location", r"town", r"district"],
    "state": [r"^state$", r"province"],
    "website": [r"website", r"web", r"domain", r"url", r"site"],
    "designation": [r"designation_with_each_company", r"designation", r"job_?title", r"jobtitle", r"role", r"position"],
    "title": [r"title", r"deal", r"opportunity", r"project"],
    "value": [r"value", r"amount", r"budget", r"revenue", r"deal_size"],
    "industry": [r"industry", r"sector", r"category"],
    "seniority": [r"seniority", r"level", r"tier"],
    "department": [r"department", r"dept", r"function", r"division"],
    "linkedin_url": [r"linkedin", r"profile", r"social"],
    "notes": [r"notes", r"bio", r"summary", r"description", r"comments"],
    "product_service": [r"product", r"product_name", r"service", r"service_name", r"offering", r"solution", r"product_service", r"product_or_service"],
    "purpose": [r"purpose", r"call_purpose", r"lead_purpose", r"requirement", r"interest"]
}


def normalize_phone(phone_raw: Any) -> Optional[str]:
    if pd.isna(phone_raw) or not str(phone_raw).strip():
        return None
    val = str(phone_raw).strip()
    # Remove floating point decimals from Excel like 9876543210.0
    if val.endswith(".0"):
        val = val[:-2]
    # Remove spaces, parentheses, hyphens, pluses
    digits = re.sub(r"\D", "", val)
    if not digits:
        return None
    # 12 digits starting with 91 (India country code) -> take last 10 digits
    if len(digits) == 12 and digits.startswith("91"):
        return digits[2:]
    # 11 digits starting with 0 (STD trunk prefix) -> take last 10 digits
    if len(digits) == 11 and digits.startswith("0"):
        return digits[1:]
    # If longer than 10 digits -> take last 10 digits
    if len(digits) > 10:
        return digits[-10:]
    return digits if len(digits) >= 6 else None


def normalize_email(email_raw: Any) -> Optional[str]:
    if pd.isna(email_raw) or not str(email_raw).strip():
        return None
    val = str(email_raw).strip().lower()
    if "@" in val and "." in val:
        return val
    return None


FREE_EMAIL_DOMAINS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "rediffmail.com", "icloud.com", "live.com", "msn.com", "aol.com"
}

def is_free_email_domain(email: Optional[str]) -> bool:
    if not email or "@" not in email:
        return True
    domain = email.split("@")[1].strip().lower()
    return domain in FREE_EMAIL_DOMAINS

def classify_segment(row: dict) -> Tuple[str, float]:
    comp = row.get("company_name") or row.get("company")
    email = row.get("email") or row.get("contact_email")
    segment = classify_lead_segment(comp, email)
    return segment, 0.99 if segment in ("B2B", "B2C") else 0.0


def detect_file_encoding(file_path: str) -> str:
    # Try utf-8, fallback to latin-1
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            f.read(4096)
        return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def load_tabular_dataframe(file_path: str, file_type: str, nrows: Optional[int] = None) -> Tuple[pd.DataFrame, int]:
    ext = os.path.splitext(file_path)[1].lower()
    if ext not in ALLOWED_TABULAR_EXTENSIONS:
        invalid_type = ext.replace(".", "").upper() if ext else file_type
        raise ValueError(
            f"Invalid file format '{invalid_type}'. Data ingestion strictly requires tabular spreadsheet files "
            f"(.CSV, .XLS, .XLSX, .XLSB, .XLSM, .PARQUET, .JSON). Non-tabular formats such as .PDF, .TXT, .MD, .ZIP, .HTML are not supported."
        )

    clean_type = file_type.upper().replace(".", "")
    if clean_type == "CSV" or ext == ".csv":
        encoding = detect_file_encoding(file_path)
        if nrows:
            df = pd.read_csv(file_path, encoding=encoding, nrows=nrows)
            with open(file_path, "r", encoding=encoding, errors="ignore") as f:
                total_rows = max(0, sum(1 for _ in f) - 1)
        else:
            df = pd.read_csv(file_path, encoding=encoding)
            total_rows = len(df)
    elif clean_type in ("XLSX", "XLS", "XLSM") or ext in (".xlsx", ".xls", ".xlsm"):
        df = pd.read_excel(file_path, nrows=nrows)
        total_rows = len(pd.read_excel(file_path)) if nrows else len(df)
    elif clean_type == "XLSB" or ext == ".xlsb":
        df = pd.read_excel(file_path, engine="pyxlsb", nrows=nrows)
        total_rows = len(pd.read_excel(file_path, engine="pyxlsb")) if nrows else len(df)
    elif clean_type == "PARQUET" or ext == ".parquet":
        full_df = pd.read_parquet(file_path)
        total_rows = len(full_df)
        df = full_df.head(nrows) if nrows else full_df
    elif clean_type == "JSON" or ext == ".json":
        raw_data = None
        # 1. Try standard JSON parse
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                raw_data = json.load(f)
        except Exception:
            # 2. Fallback to line-delimited JSON (NDJSON/JSONL)
            try:
                lines = []
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        line_str = line.strip()
                        if line_str and line_str.startswith("{") and line_str.endswith("}"):
                            lines.append(json.loads(line_str))
                if lines:
                    raw_data = lines
            except Exception:
                pass

        if raw_data is None:
            raise ValueError(f"Failed to parse JSON file '{os.path.basename(file_path)}'. Please ensure it contains valid JSON objects.")

        # 3. If raw_data is a dictionary, unwrap list of records if nested
        if isinstance(raw_data, dict):
            found_list = None
            for k in ("data", "records", "leads", "companies", "people", "contacts", "results", "rows", "items", "payload"):
                if k in raw_data and isinstance(raw_data[k], list) and len(raw_data[k]) > 0:
                    found_list = raw_data[k]
                    break
            if found_list is None:
                for k, v in raw_data.items():
                    if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict):
                        found_list = v
                        break
            if found_list is not None:
                raw_data = found_list

        if isinstance(raw_data, list):
            # Flatten nested structures cleanly using json_normalize with underscore separator
            full_df = pd.json_normalize(raw_data, sep="_")
        elif isinstance(raw_data, dict):
            full_df = pd.json_normalize([raw_data], sep="_")
        else:
            raise ValueError("JSON file must contain an array of objects or an object with a data list.")

        total_rows = len(full_df)
        df = full_df.head(nrows) if nrows else full_df
    else:
        raise ValueError(f"Unsupported tabular format: {file_type}")

    return df, total_rows


def preview_import_file(file_path: str, file_type: str) -> Dict[str, Any]:
    df, total_rows = load_tabular_dataframe(file_path, file_type, nrows=50)

    headers = [str(c).strip() for c in df.columns if not str(c).startswith("Unnamed:")]
    if len(headers) == 0:
        raise ValueError("The uploaded spreadsheet does not contain any recognizable column headers.")
    if total_rows <= 0 and len(df) == 0:
        raise ValueError("The uploaded spreadsheet contains no data rows. Please verify your sheet has data below the headers.")

    sample_rows = df.head(5).fillna("").to_dict(orient="records")

    # Smart column mapping suggestion with camelCase to snake_case normalization
    suggested_mapping = {}
    for header in headers:
        header_lower = header.lower().strip()
        snake_case = re.sub(r"(?<!^)(?=[A-Z])", "_", header).lower().strip()
        norm_header = re.sub(r"[\s\-]+", "_", header_lower)
        norm_snake = re.sub(r"[\s\-]+", "_", snake_case)
        matched = False
        for system_field, patterns in COLUMN_PATTERNS.items():
            if any(
                re.search(pat, header_lower) or 
                re.search(pat, norm_header) or 
                re.search(pat, snake_case) or 
                re.search(pat, norm_snake) 
                for pat in patterns
            ):
                if system_field not in suggested_mapping.values():
                    suggested_mapping[header] = system_field
                    matched = True
                    break
        if not matched:
            suggested_mapping[header] = "ignore"

    return {
        "detected_headers": headers,
        "sample_rows": sample_rows,
        "suggested_mappings": suggested_mapping,
        "total_detected_rows": max(0, total_rows)
    }


def execute_import_job(db: Session, job_id: str) -> ImportJob:
    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
    if not job and db.bind and db.bind.dialect.name == "postgresql":
        # Search public schema
        res = db.execute(text("SELECT organization_id FROM public.import_jobs WHERE id = :jid"), {"jid": job_id}).first()
        if res:
            db.execute(text('SET search_path TO public'))
            job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        else:
            schemas = db.execute(text("SELECT schema_name FROM organizations WHERE schema_name IS NOT NULL")).scalars().all()
            for s in schemas:
                res_s = db.execute(text(f'SELECT organization_id FROM "{s}".import_jobs WHERE id = :jid'), {"jid": job_id}).first()
                if res_s:
                    db.execute(text(f'SET search_path TO "{s}", public'))
                    job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
                    break

    if not job:
        raise ValueError(f"Import job {job_id} not found")

    # Read needed job fields into variables before any schema switch or commit
    file_path = job.file_path
    file_name = job.file_name
    file_type = job.file_type.upper()
    mapping = job.column_mapping or {}
    job_org_id = job.organization_id
    target_stage_id = job.target_stage_id
    uploaded_by = job.uploaded_by
    target_owner_id = job.target_owner_id
    default_product_service_id = job.default_product_service_id
    job_type = (job.job_type or "").upper()

    # Update status to PROCESSING and expunge BEFORE switching search_path
    job.status = "PROCESSING"
    job.started_at = datetime.now(timezone.utc)
    db.commit()
    try:
        db.expunge(job)
    except Exception:
        pass

    # Ensure search_path is set to tenant schema for lead/company/contact insertion
    tenant_schema = None
    if job_org_id and db.bind and db.bind.dialect.name == "postgresql":
        from app.models.organization import Organization
        org = db.query(Organization).filter(Organization.id == job_org_id).first()
        if org and org.schema_name:
            tenant_schema = org.schema_name
            db.execute(text(f'SET search_path TO "{tenant_schema}", public'))
            try:
                db.execute(text(f'''
                    INSERT INTO "{tenant_schema}".import_jobs 
                    (id, organization_id, uploaded_by, job_type, file_name, file_type, file_path, column_mapping, target_stage_id, target_owner_id, default_product_service_id, status, total_rows, processed_rows, successful_rows, duplicate_rows, error_rows, created_at, started_at, error_summary)
                    SELECT id, organization_id, uploaded_by, job_type, file_name, file_type, file_path, column_mapping, target_stage_id, target_owner_id, default_product_service_id, status, total_rows, processed_rows, successful_rows, duplicate_rows, error_rows, created_at, started_at, COALESCE(error_summary, '{{}}'::json)
                    FROM public.import_jobs WHERE id = :jid
                    ON CONFLICT (id) DO UPDATE SET status = 'PROCESSING', started_at = EXCLUDED.started_at
                '''), {"jid": job_id})
                db.commit()
            except Exception:
                db.rollback()
    elif db.bind and db.bind.dialect.name == "postgresql":
        db.execute(text('SET search_path TO public'))

    try:
        is_global_companies = job_type in ("GLOBAL_COMPANIES", "GLOBAL_DATABASE")
        is_global_people = job_type == "GLOBAL_PEOPLE"
        is_global = is_global_companies or is_global_people
        stage = None
        organization_id = None

        if not is_global:
            # Resolve Target Pipeline Stage without modifying the pipeline!
            organization_id = job_org_id
            if target_stage_id:
                stage = get_stage_by_id(db, target_stage_id, organization_id)
            else:
                stage = get_first_stage(db, organization_id)

        # Read dataset
        df, total = load_tabular_dataframe(file_path, file_type)

        total = len(df)
        job.total_rows = total
        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(text("UPDATE public.import_jobs SET total_rows = :t WHERE id = :jid"), {"t": total, "jid": job_id})
                if tenant_schema:
                    db.execute(text(f'UPDATE "{tenant_schema}".import_jobs SET total_rows = :t WHERE id = :jid'), {"t": total, "jid": job_id})
                db.commit()
            else:
                db.execute(text("UPDATE import_jobs SET total_rows = :t WHERE id = :jid"), {"t": total, "jid": job_id})
                db.commit()
        except Exception:
            pass

        # Inversion of mapping: system_field -> csv_column
        reverse_map = {v: k for k, v in mapping.items() if v != "ignore"}

        successful = 0
        duplicates = 0
        errors = 0

        for idx, row in df.iterrows():
            row_num = idx + 1
            raw_dict = {str(k): ("" if pd.isna(v) else str(v)) for k, v in row.items()}

            try:
                # Extract fields
                comp_name = str(row[reverse_map["company_name"]]).strip() if "company_name" in reverse_map and not pd.isna(row[reverse_map["company_name"]]) else None
                cont_name = str(row[reverse_map["contact_name"]]).strip() if "contact_name" in reverse_map and not pd.isna(row[reverse_map["contact_name"]]) else None
                raw_email = row[reverse_map["contact_email"]] if "contact_email" in reverse_map else None
                raw_phone = row[reverse_map["contact_phone"]] if "contact_phone" in reverse_map else None
                lead_title = str(row[reverse_map["title"]]).strip() if "title" in reverse_map and not pd.isna(row[reverse_map["title"]]) else None
                city = str(row[reverse_map["city"]]).strip() if "city" in reverse_map and not pd.isna(row[reverse_map["city"]]) else None
                state_name = str(row[reverse_map["state"]]).strip() if "state" in reverse_map and not pd.isna(row[reverse_map["state"]]) else None
                postal_code = str(row[reverse_map["postal_code"]]).strip() if "postal_code" in reverse_map and not pd.isna(row[reverse_map["postal_code"]]) else None
                address = str(row[reverse_map["address"]]).strip() if "address" in reverse_map and not pd.isna(row[reverse_map["address"]]) else None
                website = str(row[reverse_map["website"]]).strip() if "website" in reverse_map and not pd.isna(row[reverse_map["website"]]) else None
                cin = str(row[reverse_map["cin"]]).strip() if "cin" in reverse_map and not pd.isna(row[reverse_map["cin"]]) else None
                reg_num = str(row[reverse_map["registration_number"]]).strip() if "registration_number" in reverse_map and not pd.isna(row[reverse_map["registration_number"]]) else None
                gst_num = str(row[reverse_map["gst_number"]]).strip() if "gst_number" in reverse_map and not pd.isna(row[reverse_map["gst_number"]]) else None
                row_id = str(row[reverse_map["id"]]).strip() if "id" in reverse_map and not pd.isna(row[reverse_map["id"]]) else None
                assoc_raw = str(row[reverse_map["associated_companies"]]).strip() if "associated_companies" in reverse_map and not pd.isna(row[reverse_map["associated_companies"]]) else None
                designation = str(row[reverse_map["designation"]]).strip() if "designation" in reverse_map and not pd.isna(row[reverse_map["designation"]]) else None
                industry = str(row[reverse_map["industry"]]).strip() if "industry" in reverse_map and not pd.isna(row[reverse_map["industry"]]) else None
                seniority = str(row[reverse_map["seniority"]]).strip() if "seniority" in reverse_map and not pd.isna(row[reverse_map["seniority"]]) else None
                department = str(row[reverse_map["department"]]).strip() if "department" in reverse_map and not pd.isna(row[reverse_map["department"]]) else None
                linkedin_url = str(row[reverse_map["linkedin_url"]]).strip() if "linkedin_url" in reverse_map and not pd.isna(row[reverse_map["linkedin_url"]]) else None
                notes = str(row[reverse_map["notes"]]).strip() if "notes" in reverse_map and not pd.isna(row[reverse_map["notes"]]) else None
                raw_product_service = str(row[reverse_map["product_service"]]).strip() if "product_service" in reverse_map and not pd.isna(row[reverse_map["product_service"]]) else None
                purpose = str(row[reverse_map["purpose"]]).strip() if "purpose" in reverse_map and not pd.isna(row[reverse_map["purpose"]]) else None
                raw_val = row[reverse_map["value"]] if "value" in reverse_map and not pd.isna(row[reverse_map["value"]]) else 0.0

                # Normalization
                email = normalize_email(raw_email)
                phone = normalize_phone(raw_phone)

                if is_global_people:
                    person_name = cont_name or lead_title
                    if not person_name:
                        error = ImportRowError(
                            job_id=job_id,
                            row_number=row_num,
                            raw_data=raw_dict,
                            error_code="EMPTY_NAME",
                            error_message="People Intelligence row must have a contact or person name"
                        )
                        db.add(error)
                        errors += 1
                        continue

                    # Deduplication check in global_people
                    dup = None
                    if email:
                        dup = db.query(GlobalPerson).filter(GlobalPerson.email == email).first()
                    if not dup and phone:
                        dup = db.query(GlobalPerson).filter(GlobalPerson.phone == phone).first()
                    if not dup and comp_name:
                        dup = db.query(GlobalPerson).filter(
                            GlobalPerson.full_name.ilike(person_name),
                            GlobalPerson.company_name.ilike(comp_name)
                        ).first()

                    if dup:
                        duplicates += 1
                        continue

                    try:
                        val_num = float(raw_val)
                    except Exception:
                        val_num = 0.0

                    # Parse associated companies
                    assoc_list = []
                    if assoc_raw:
                        parts = re.split(r"[,;|]+", assoc_raw)
                        for part in parts:
                            p = part.strip()
                            if not p:
                                continue
                            m = re.match(r"^([^\(\-]+)(?:[\(\-]([^\)\-]+)\)?)?$", p)
                            if m:
                                c_part = m.group(1).strip()
                                d_part = m.group(2).strip() if m.group(2) else ""
                                if c_part:
                                    assoc_list.append({"company_name": c_part, "designation": d_part})
                            else:
                                assoc_list.append({"company_name": p, "designation": ""})

                    if comp_name:
                        if not any(a["company_name"].lower() == comp_name.lower() for a in assoc_list):
                            assoc_list.insert(0, {"company_name": comp_name, "designation": designation or ""})
                    elif assoc_list:
                        comp_name = assoc_list[0]["company_name"]
                        if not designation and assoc_list[0].get("designation"):
                            designation = assoc_list[0]["designation"]

                    new_person = GlobalPerson(
                        full_name=person_name,
                        email=email,
                        phone=phone,
                        designation=designation,
                        company_name=comp_name,
                        associated_companies=assoc_list,
                        industry=industry,
                        seniority=seniority,
                        department=department,
                        linkedin_url=linkedin_url,
                        city=city,
                        state=state_name,
                        country="India",
                        estimated_value=val_num,
                        status="ACTIVE",
                        source="IMPORT",
                        notes=notes
                    )
                    db.add(new_person)
                    successful += 1

                elif is_global_companies:
                    if not comp_name:
                        error = ImportRowError(
                            job_id=job.id,
                            row_number=row_num,
                            raw_data=raw_dict,
                            error_code="EMPTY_COMPANY",
                            error_message="Company Intelligence row must have a company name"
                        )
                        db.add(error)
                        errors += 1
                        continue

                    # Determine company UUID
                    company_uuid = row_id if (row_id and len(row_id) >= 10) else str(uuid.uuid4())
                    if db.query(GlobalCompany).filter(GlobalCompany.id == company_uuid).first():
                        company_uuid = str(uuid.uuid4())

                    # Upsert Global Company
                    cin_clean = cin.strip().upper() if cin else None
                    reg_clean = reg_num.strip() if reg_num else None
                    gst_clean = gst_num.strip().upper() if gst_num else None

                    g_comp = None
                    if cin_clean:
                        g_comp = db.query(GlobalCompany).filter(GlobalCompany.registry_id == cin_clean).first()
                    if not g_comp and reg_clean:
                        g_comp = db.query(GlobalCompany).filter(GlobalCompany.registration_number == reg_clean).first()
                    if not g_comp and gst_clean:
                        g_comp = db.query(GlobalCompany).filter(GlobalCompany.gst_number == gst_clean).first()
                    if not g_comp:
                        g_comp = db.query(GlobalCompany).filter(GlobalCompany.legal_name.ilike(comp_name)).first()

                    if not g_comp:
                        cin_val = cin_clean or reg_clean or f"REG-{uuid.uuid4().hex[:8].upper()}"
                        if db.query(GlobalCompany).filter(GlobalCompany.registry_id == cin_val).first():
                            cin_val = f"{cin_val}-{uuid.uuid4().hex[:4].upper()}"

                        g_comp = GlobalCompany(
                            id=company_uuid,
                            registry_country="IN",
                            registry_type="CIN" if cin_clean else "OTHER",
                            registry_id=cin_val,
                            legal_name=comp_name,
                            display_name=comp_name,
                            cin=cin_clean,
                            registration_number=reg_clean,
                            gst_number=gst_clean,
                            address=address,
                            postal_code=postal_code,
                            website=website,
                            industry=industry,
                            email=email,
                            phone=phone,
                            city=city,
                            state=state_name,
                            country="India",
                            status="ACTIVE"
                        )
                        db.add(g_comp)
                        db.flush()
                    else:
                        if city and not g_comp.city: g_comp.city = city
                        if state_name and not g_comp.state: g_comp.state = state_name
                        if address and not g_comp.address: g_comp.address = address
                        if postal_code and not g_comp.postal_code: g_comp.postal_code = postal_code
                        if website and not g_comp.website: g_comp.website = website
                        if cin_clean and not g_comp.cin: g_comp.cin = cin_clean
                        if reg_clean and not g_comp.registration_number: g_comp.registration_number = reg_clean
                        if gst_clean and not g_comp.gst_number: g_comp.gst_number = gst_clean
                        if industry and not g_comp.industry: g_comp.industry = industry
                        if phone and not g_comp.phone: g_comp.phone = phone
                        if email and not g_comp.email: g_comp.email = email

                    # Upsert Global Contact
                    if cont_name:
                        g_cont = None
                        if email:
                            g_cont = db.query(GlobalContact).filter(GlobalContact.email == email).first()
                        elif phone:
                            g_cont = db.query(GlobalContact).filter(GlobalContact.phone == phone).first()
                        if not g_cont:
                            g_cont = db.query(GlobalContact).filter(GlobalContact.full_name.ilike(cont_name)).first()

                        if not g_cont:
                            g_cont = GlobalContact(
                                full_name=cont_name,
                                designation=designation or "Director",
                                email=email,
                                phone=phone,
                                city=city,
                                status="ACTIVE"
                            )
                            db.add(g_cont)
                            db.flush()

                        # Link in GlobalCompanyContactMap
                        mapping_entry = db.query(GlobalCompanyContactMap).filter(
                            GlobalCompanyContactMap.company_id == g_comp.id,
                            GlobalCompanyContactMap.contact_id == g_cont.id
                        ).first()
                        if not mapping_entry:
                            mapping_entry = GlobalCompanyContactMap(
                                company_id=g_comp.id,
                                contact_id=g_cont.id,
                                designation=designation or "Director"
                            )
                            db.add(mapping_entry)

                    successful += 1

                else:
                    # Row validation
                    if not comp_name and not cont_name and not lead_title:
                        error = ImportRowError(
                            job_id=job_id,
                            row_number=row_num,
                            raw_data=raw_dict,
                            error_code="EMPTY_IDENTIFIER",
                            error_message="Row has no company name, contact name, or lead title"
                        )
                        db.add(error)
                        errors += 1
                        continue

                    final_title = lead_title or (f"{comp_name} - Opportunity" if comp_name else f"Lead: {cont_name}")

                    # 1. Company Resolution & Deduplication
                    company = None
                    if comp_name:
                        company, _ = get_or_create_company(
                            db=db,
                            organization_id=organization_id,
                            name=comp_name,
                            cin=cin,
                            city=city,
                            user_id=uploaded_by
                        )

                    # 2. Contact Resolution & Deduplication
                    contact = None
                    if cont_name:
                        contact, _ = get_or_create_contact(
                            db=db,
                            organization_id=organization_id,
                            full_name=cont_name,
                            phone=phone,
                            email=email,
                            company_id=company.id if company else None,
                            designation=designation,
                            user_id=uploaded_by
                        )

                    # 3. Duplicate Detection for Lead
                    dup_query = db.query(Lead).filter(Lead.organization_id == organization_id)
                    is_dup = False
                    if phone:
                        if dup_query.filter(Lead.contact_phone == phone).first():
                            is_dup = True
                    elif email:
                        if dup_query.filter(Lead.contact_email == email).first():
                            is_dup = True

                    if is_dup:
                        duplicates += 1
                        continue

                    # 4. Classify Segment & Lead Type (Problem 6 & 20)
                    detected_segment, _ = classify_segment({"company_name": comp_name, "email": email})
                    # Segment describes B2B/B2C/OTHER; imported leads are an
                    # outbound source regardless of their segment.
                    inferred_lead_type = "OUTBOUND"

                    # Ensure ContactPhone record is registered (Problem 4 & 15)
                    if contact and phone:
                        from app.models.contact_phone import ContactPhone
                        from app.services.telephony_service import parse_and_format_phone
                        e164_phone, phone_type, is_sms = parse_and_format_phone(phone)
                        existing_cp = db.query(ContactPhone).filter(
                            ContactPhone.contact_id == contact.id,
                            ContactPhone.phone_number == (e164_phone or phone)
                        ).first()
                        if not existing_cp:
                            cp = ContactPhone(
                                contact_id=contact.id,
                                phone_number=e164_phone or phone,
                                phone_type=phone_type,
                                label="Primary",
                                is_primary=True,
                                is_whatsapp=(phone_type == "MOBILE"),
                                is_sms_capable=is_sms,
                                is_callable=True
                            )
                            db.add(cp)
                            
                    # 5. Product/Service Resolution
                    resolved_product_service_id = default_product_service_id
                    resolved_product_service_name = None
                    if raw_product_service:
                        from app.models.product_service import ProductService
                        ps = db.query(ProductService).filter(
                            ProductService.organization_id == organization_id,
                            ProductService.name.ilike(raw_product_service),
                            ProductService.is_active.is_(True),
                        ).first()
                        if ps:
                            resolved_product_service_id = ps.id
                            resolved_product_service_name = ps.name
                        else:
                            error = ImportRowError(
                                job_id=job_id,
                                row_number=row_num,
                                raw_data=raw_dict,
                                error_code="UNRESOLVABLE_PRODUCT_SERVICE",
                                error_message=f"Product/Service '{raw_product_service}' not found in organization catalog"
                            )
                            db.add(error)
                            errors += 1
                            continue
                    elif default_product_service_id:
                        from app.models.product_service import ProductService
                        ps = db.query(ProductService).filter(
                            ProductService.id == default_product_service_id,
                            ProductService.organization_id == organization_id,
                            ProductService.is_active.is_(True),
                        ).first()
                        if not ps:
                            error = ImportRowError(
                                job_id=job_id,
                                row_number=row_num,
                                raw_data=raw_dict,
                                error_code="UNRESOLVABLE_PRODUCT_SERVICE",
                                error_message="Default Product/Service is not active in organization catalog",
                            )
                            db.add(error)
                            errors += 1
                            continue
                        resolved_product_service_name = ps.name

                    # Create Lead Record referencing target stage
                    new_lead = Lead(
                        organization_id=organization_id,
                        company_id=company.id if company else None,
                        contact_id=contact.id if contact else None,
                        pipeline_stage_id=stage.id,
                        owner_id=target_owner_id,
                        title=final_title,
                        company_name=comp_name or (company.name if company else None),
                        contact_name=cont_name or (contact.full_name if contact else None),
                        contact_email=email,
                        contact_phone=phone,
                        segment=detected_segment,
                        lead_type=inferred_lead_type,
                        product_service_id=resolved_product_service_id,
                        product_service_name=resolved_product_service_name,
                        purpose=purpose,
                        source="IMPORT",
                        status="OPEN",
                        priority="MEDIUM",
                        score=60,
                        created_by=uploaded_by
                    )
                    db.add(new_lead)
                    db.flush()

                    # 5. Append Initial Stage History
                    history = LeadStageHistory(
                        organization_id=organization_id,
                        lead_id=new_lead.id,
                        from_stage_id=None,
                        to_stage_id=stage.id,
                        changed_by=uploaded_by,
                        reason=f"Batch Import: {file_name}",
                        duration_seconds=0
                    )
                    db.add(history)
                    successful += 1

                # Periodic commit every 250 rows for safety & memory control
                if row_num % 250 == 0:
                    db.commit()
                    try:
                        if db.bind and db.bind.dialect.name == "postgresql":
                            db.execute(text("UPDATE public.import_jobs SET processed_rows = :p, successful_rows = :s, duplicate_rows = :d, error_rows = :e WHERE id = :jid"),
                                {"p": row_num, "s": successful, "d": duplicates, "e": errors, "jid": job_id})
                            if tenant_schema:
                                db.execute(text(f'UPDATE "{tenant_schema}".import_jobs SET processed_rows = :p, successful_rows = :s, duplicate_rows = :d, error_rows = :e WHERE id = :jid'),
                                    {"p": row_num, "s": successful, "d": duplicates, "e": errors, "jid": job_id})
                            db.commit()
                    except Exception:
                        db.rollback()

            except Exception as row_exc:
                db.rollback()
                errors += 1
                error = ImportRowError(
                    job_id=job_id,
                    row_number=row_num,
                    raw_data=raw_dict,
                    error_code="ROW_PROCESSING_ERROR",
                    error_message=str(row_exc)[:500]
                )
                db.add(error)
                db.commit()

        completed_time = datetime.now(timezone.utc)
        error_summary_dict = {
            "total_rows": total,
            "successful_rows": successful,
            "duplicate_rows": duplicates,
            "error_rows": errors,
            "completion_rate": f"{(successful / total * 100):.1f}%" if total > 0 else "0%"
        }
        final_status = "COMPLETED" if errors == 0 else "PARTIAL"

        # Update in DB safely via SQL
        if db.bind and db.bind.dialect.name == "postgresql":
            try:
                db.execute(text("""
                    UPDATE public.import_jobs
                    SET status = :status, processed_rows = :processed, successful_rows = :successful,
                        duplicate_rows = :duplicates, error_rows = :errors, completed_at = :completed,
                        error_summary = :summary
                    WHERE id = :jid
                """), {
                    "status": final_status,
                    "processed": total,
                    "successful": successful,
                    "duplicates": duplicates,
                    "errors": errors,
                    "completed": completed_time,
                    "summary": json.dumps(error_summary_dict),
                    "jid": job_id
                })
                db.commit()
            except Exception:
                db.rollback()

            if tenant_schema:
                try:
                    db.execute(text(f"""
                        UPDATE "{tenant_schema}".import_jobs
                        SET status = :status, processed_rows = :processed, successful_rows = :successful,
                            duplicate_rows = :duplicates, error_rows = :errors, completed_at = :completed,
                            error_summary = :summary
                        WHERE id = :jid
                    """), {
                        "status": final_status,
                        "processed": total,
                        "successful": successful,
                        "duplicates": duplicates,
                        "errors": errors,
                        "completed": completed_time,
                        "summary": json.dumps(error_summary_dict),
                        "jid": job_id
                    })
                    db.commit()
                except Exception:
                    db.rollback()
        else:
            try:
                db.execute(text("""
                    UPDATE import_jobs
                    SET status = :status, processed_rows = :processed, successful_rows = :successful,
                        duplicate_rows = :duplicates, error_rows = :errors, completed_at = :completed,
                        error_summary = :summary
                    WHERE id = :jid
                """), {
                    "status": final_status,
                    "processed": total,
                    "successful": successful,
                    "duplicates": duplicates,
                    "errors": errors,
                    "completed": completed_time,
                    "summary": json.dumps(error_summary_dict),
                    "jid": job_id
                })
                db.commit()
            except Exception:
                db.rollback()

        # Reload fresh job from DB
        fresh_job = db.query(ImportJob).filter(ImportJob.id == job_id).first()
        if fresh_job:
            return fresh_job
        return job

    except Exception as exc:
        db.rollback()
        completed_time = datetime.now(timezone.utc)
        error_summary = {"fatal_error": str(exc)}
        try:
            job.status = "FAILED"
            job.completed_at = completed_time
            job.error_summary = error_summary
        except Exception:
            pass

        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(text("UPDATE public.import_jobs SET status = 'FAILED', completed_at = :c, error_summary = :s WHERE id = :jid"),
                    {"c": completed_time, "s": json.dumps(error_summary), "jid": job_id})
                db.commit()
                if tenant_schema:
                    db.execute(text(f'UPDATE "{tenant_schema}".import_jobs SET status = \'FAILED\', completed_at = :c, error_summary = :s WHERE id = :jid'),
                        {"c": completed_time, "s": json.dumps(error_summary), "jid": job_id})
                    db.commit()
            else:
                db.execute(text("UPDATE import_jobs SET status = 'FAILED', completed_at = :c, error_summary = :s WHERE id = :jid"),
                    {"c": completed_time, "s": json.dumps(error_summary), "jid": job_id})
                db.commit()
        except Exception:
            db.rollback()
        return job
