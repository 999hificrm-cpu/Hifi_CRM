from typing import List, Optional, Dict, Any, Set
from sqlalchemy.orm import Session
import re

from app.models.global_registry import GlobalCompany
from app.models.global_people import GlobalPerson
from app.schemas.global_registry import (
    LinkedPersonOut,
    CompanyWithPeopleOut,
    GlobalIntelligenceResponse
)
from app.models.company import Company
from app.models.contact import Contact

def _normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    # Strip legal suffixes like Pvt Ltd, Private Limited, Ltd, Limited, Inc, LLP
    s = name.lower().strip()
    s = re.sub(r"\b(pvt|private|ltd|limited|llp|inc|corp|corporation)\b", "", s)
    s = re.sub(r"[^\w\s]", "", s)
    return " ".join(s.split())


def get_global_intelligence(
    db: Session,
    search: Optional[str] = None,
    filter_type: Optional[str] = "ALL",  # ALL, WITH_PEOPLE, WITHOUT_PEOPLE
    city: Optional[str] = None,
    industry: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: Optional[Any] = None
) -> GlobalIntelligenceResponse:
    # 1. Fetch active companies and active people (filter out PULLED for non-superadmins/non-data-entry)
    is_sa = bool(current_user and (getattr(current_user, "is_super_admin", False) or getattr(current_user, "is_data_entry", False)))
    if is_sa:
        all_companies = db.query(GlobalCompany).filter(GlobalCompany.status == "ACTIVE").all()
        all_people = db.query(GlobalPerson).filter(GlobalPerson.status == "ACTIVE").all()
    else:
        all_companies = db.query(GlobalCompany).filter(GlobalCompany.status == "ACTIVE").all()
        all_people = db.query(GlobalPerson).filter(GlobalPerson.status == "ACTIVE").all()

    total_companies = len(all_companies)
    total_people = len(all_people)
    
    tenant_id = getattr(current_user, "organization_id", None)
    pulled_company_ids = set()
    pulled_contact_ids = set()
    
    if tenant_id:
        pulled_comps = db.query(Company.source_global_company_id).filter(
            Company.organization_id == tenant_id,
            Company.source_global_company_id.isnot(None)
        ).all()
        pulled_company_ids = {c[0] for c in pulled_comps}
        
        pulled_conts = db.query(Contact.source_global_contact_id).filter(
            Contact.organization_id == tenant_id,
            Contact.source_global_contact_id.isnot(None)
        ).all()
        pulled_contact_ids = {c[0] for c in pulled_conts}

    # 2. Store list of LinkedPersonOut per company_id
    linked_people_by_comp: Dict[str, List[LinkedPersonOut]] = {c.id: [] for c in all_companies}
    linked_people_ids: Set[str] = set()

    # Pre-compute match keys for each company
    # Maps key -> set of company IDs
    key_to_comp_ids: Dict[str, Set[str]] = {}

    for c in all_companies:
        keys = set()
        if c.legal_name:
            keys.add(c.legal_name.lower().strip())
            norm = _normalize_name(c.legal_name)
            if norm:
                keys.add(norm)
        if c.display_name:
            keys.add(c.display_name.lower().strip())
            norm_disp = _normalize_name(c.display_name)
            if norm_disp:
                keys.add(norm_disp)
        if c.cin:
            keys.add(c.cin.lower().strip())
        if c.registry_id:
            keys.add(c.registry_id.lower().strip())

        for k in keys:
            if k not in key_to_comp_ids:
                key_to_comp_ids[k] = set()
            key_to_comp_ids[k].add(c.id)

    # Helper function to find matching company IDs for a given company name query
    def find_matching_company_ids(c_name: Optional[str]) -> Set[str]:
        if not c_name or not c_name.strip():
            return set()
        raw = c_name.lower().strip()
        norm = _normalize_name(c_name)
        matched_ids = set()
        if raw in key_to_comp_ids:
            matched_ids.update(key_to_comp_ids[raw])
        if norm and norm in key_to_comp_ids:
            matched_ids.update(key_to_comp_ids[norm])
        if not matched_ids and norm and len(norm) >= 4:
            # Fuzzy match if norm length >= 4
            for k, cids in key_to_comp_ids.items():
                if len(k) >= 4 and (norm in k or k in norm):
                    matched_ids.update(cids)
        return matched_ids

    # 3. Associate people to companies dynamically
    for person in all_people:
        person_linked = False

        # Match primary company
        primary_comp_ids = find_matching_company_ids(person.company_name)
        for cid in primary_comp_ids:
            if not any(
                lp.id == person.id or 
                (lp.full_name.strip().lower() == person.full_name.strip().lower() and (not lp.email or not person.email or lp.email.strip().lower() == person.email.strip().lower()))
                for lp in linked_people_by_comp[cid]
            ):
                linked_people_by_comp[cid].append(LinkedPersonOut(
                    id=person.id,
                    full_name=person.full_name,
                    email=person.email,
                    phone=person.phone,
                    designation=person.designation,
                    company_name=person.company_name,
                    seniority=person.seniority,
                    department=person.department,
                    city=person.city,
                    state=person.state,
                    linkedin_url=person.linkedin_url,
                    status="PULLED" if person.id in pulled_contact_ids else person.status,
                    is_primary=True,
                    estimated_value=float(person.estimated_value or 0.0)
                ))
                person_linked = True

        # Match associated companies list
        if person.associated_companies and isinstance(person.associated_companies, list):
            for ac in person.associated_companies:
                if not isinstance(ac, dict):
                    continue
                ac_name = ac.get("company_name", "")
                ac_desig = ac.get("designation") or person.designation
                matched_ac_ids = find_matching_company_ids(ac_name)
                for cid in matched_ac_ids:
                    if not any(
                        lp.id == person.id or 
                        (lp.full_name.strip().lower() == person.full_name.strip().lower() and (not lp.email or not person.email or lp.email.strip().lower() == person.email.strip().lower()))
                        for lp in linked_people_by_comp[cid]
                    ):
                        linked_people_by_comp[cid].append(LinkedPersonOut(
                            id=person.id,
                            full_name=person.full_name,
                            email=person.email,
                            phone=person.phone,
                            designation=ac_desig,
                            company_name=ac_name or person.company_name,
                            seniority=person.seniority,
                            department=person.department,
                            city=person.city,
                            state=person.state,
                            linkedin_url=person.linkedin_url,
                            status="PULLED" if person.id in pulled_contact_ids else person.status,
                            is_primary=False,
                            estimated_value=float(person.estimated_value or 0.0)
                        ))
                        person_linked = True

        if person_linked:
            linked_people_ids.add(person.id)

    # 4. Construct enriched company list
    enriched_companies: List[CompanyWithPeopleOut] = []
    companies_with_people_count = 0
    total_market_turnover = 0.0

    for c in all_companies:
        is_public = (c.company_type or "").lower().find("public") != -1
        base_val = 50000000.0 if is_public else (15000000.0 if c.cin else 8000000.0)
        c_people = linked_people_by_comp.get(c.id, [])
        p_count = len(c_people)
        if p_count > 0:
            companies_with_people_count += 1
        turnover = base_val + (p_count * 2500000.0)
        total_market_turnover += turnover

        enriched_companies.append(CompanyWithPeopleOut(
            id=c.id,
            registry_id=c.registry_id,
            legal_name=c.legal_name,
            display_name=c.display_name,
            company_type=c.company_type,
            industry=c.industry,
            cin=c.cin,
            registration_number=c.registration_number,
            gst_number=c.gst_number,
            address=c.address,
            city=c.city,
            state=c.state,
            country=c.country or "India",
            postal_code=c.postal_code,
            website=c.website,
            email=c.email,
            phone=c.phone,
            status="PULLED" if c.id in pulled_company_ids else c.status,
            contacts_count=len(c.contacts) if hasattr(c, "contacts") and c.contacts else 0,
            associated_people=c_people,
            people_count=p_count
        ))

    # 5. Filtering and Searching
    filtered = enriched_companies

    # Search filter across company fields OR any associated person's name/designation/email/phone
    if search and search.strip():
        s = search.strip().lower()
        def matches_search(comp: CompanyWithPeopleOut) -> bool:
            if s in comp.legal_name.lower(): return True
            if comp.display_name and s in comp.display_name.lower(): return True
            if comp.cin and s in comp.cin.lower(): return True
            if comp.gst_number and s in comp.gst_number.lower(): return True
            if comp.registration_number and s in comp.registration_number.lower(): return True
            if comp.city and s in comp.city.lower(): return True
            if comp.industry and s in comp.industry.lower(): return True
            for p in comp.associated_people:
                if s in p.full_name.lower(): return True
                if p.designation and s in p.designation.lower(): return True
                if p.email and s in p.email.lower(): return True
                if p.phone and s in p.phone.lower(): return True
            return False

        filtered = [c for c in filtered if matches_search(c)]

    if filter_type == "WITH_PEOPLE":
        filtered = [c for c in filtered if c.people_count > 0]
    elif filter_type == "WITHOUT_PEOPLE":
        filtered = [c for c in filtered if c.people_count == 0]

    if city and city.strip():
        c_lower = city.strip().lower()
        filtered = [c for c in filtered if c.city and c_lower in c.city.lower()]

    if industry and industry.strip():
        ind_lower = industry.strip().lower()
        filtered = [c for c in filtered if c.industry and ind_lower in c.industry.lower()]

    # Sort: Companies with people first, then sorted by people_count desc, then legal_name asc
    filtered.sort(key=lambda c: (c.people_count > 0, c.people_count, c.legal_name), reverse=True)

    paged_companies = filtered[skip : skip + limit]

    # 6. Extract Independent / Unassociated People Leads
    unlinked_people_list: List[LinkedPersonOut] = []
    seen_unlinked_ids = set()
    for person in all_people:
        if person.id not in linked_people_ids and person.id not in seen_unlinked_ids:
            seen_unlinked_ids.add(person.id)
            cname = person.company_name
            if not cname and person.associated_companies and isinstance(person.associated_companies, list) and len(person.associated_companies) > 0:
                cname = person.associated_companies[0].get("company_name", "")

            unlinked_people_list.append(LinkedPersonOut(
                id=person.id,
                full_name=person.full_name,
                email=person.email,
                phone=person.phone,
                designation=person.designation,
                company_name=cname or "Independent / Unspecified Account",
                seniority=person.seniority,
                department=person.department,
                city=person.city,
                state=person.state,
                linkedin_url=person.linkedin_url,
                status="PULLED" if person.id in pulled_contact_ids else person.status,
                is_primary=True,
                estimated_value=float(person.estimated_value or 0.0)
            ))

    filtered_unlinked = unlinked_people_list
    if search and search.strip():
        s = search.strip().lower()
        filtered_unlinked = [
            p for p in filtered_unlinked
            if (s in p.full_name.lower() or
                (p.designation and s in p.designation.lower()) or
                (p.company_name and s in p.company_name.lower()) or
                (p.email and s in p.email.lower()) or
                (p.phone and s in p.phone.lower()) or
                (p.city and s in p.city.lower()) or
                (p.department and s in p.department.lower()))
        ]

    if city and city.strip():
        c_lower = city.strip().lower()
        filtered_unlinked = [p for p in filtered_unlinked if p.city and c_lower in p.city.lower()]

    filtered_unlinked.sort(key=lambda p: p.full_name.lower())

    # 7. Compute Direct Reach Percentage (Phone / Email coverage across people)
    contacts_with_reach = sum(1 for p in all_people if (p.phone and p.phone.strip()) or (p.email and p.email.strip()))
    direct_reach_percentage = round((contacts_with_reach / max(1, total_people)) * 100.0, 1) if total_people > 0 else 0.0

    return GlobalIntelligenceResponse(
        total_companies=total_companies,
        total_people=total_people,
        linked_people_count=len(linked_people_ids),
        unlinked_people_count=len(unlinked_people_list),
        companies_with_people_count=companies_with_people_count,
        direct_reach_percentage=direct_reach_percentage,
        total_market_turnover=total_market_turnover,
        companies=paged_companies,
        unlinked_people=filtered_unlinked
    )
