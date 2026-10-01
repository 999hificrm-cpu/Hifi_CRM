# JARVIS CRM — Database Bible

## 1. Domain Hierarchy
```
organizations
  ├── users (organization_id != NULL, tenant_role)
  ├── companies (tenant accounts)
  ├── contacts (tenant people, linked to company)
  ├── pipelines
  │     └── pipeline_stages
  ├── leads (opportunity linking contact + company + stage + owner)
  │     ├── lead_stage_history
  │     └── lead_assignments
  ├── activities (calls, whatsapp, emails, notes)
  ├── tasks (follow-ups and reminders)
  ├── masking_policies & masking_exceptions
  └── import_jobs & import_row_errors
```

## 2. Rejection of Previous Anti-Patterns
- Eliminated `crm_people` in favor of standard `contacts`.
- Eliminated circular `lead_contacts` table; `leads` has direct foreign keys to `contact_id` and `company_id`.
- Eliminated pipeline mutation during imports.
