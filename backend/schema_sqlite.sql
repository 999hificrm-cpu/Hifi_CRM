-- ==========================================================================
-- JARVIS CRM — Exact SQLite Database Schema (Analyzed from jarvis_crm.db)
-- Total Tables: 26
-- Generated for instant database initialization from scratch
-- ==========================================================================

PRAGMA foreign_keys = ON;

-- Table: activities
CREATE TABLE activities (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36), 
	company_id VARCHAR(36), 
	contact_id VARCHAR(36), 
	user_id VARCHAR(36) NOT NULL, 
	activity_type VARCHAR(50) NOT NULL, 
	subject VARCHAR(255), 
	description TEXT, 
	direction VARCHAR(20), 
	status VARCHAR(50) NOT NULL, 
	duration_seconds INTEGER, 
	metadata_json JSON NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table: ai_insights
CREATE TABLE ai_insights (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	insight_type VARCHAR(100) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	content TEXT NOT NULL, 
	score NUMERIC(5, 2), 
	confidence NUMERIC(5, 2), 
	metadata_json JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	expires_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

-- Table: ai_runs
CREATE TABLE ai_runs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	run_type VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(50), 
	entity_id VARCHAR(36), 
	model VARCHAR(100) NOT NULL, 
	input_data JSON NOT NULL, 
	output_data JSON NOT NULL, 
	tokens_used INTEGER, 
	latency_ms INTEGER, 
	status VARCHAR(30) NOT NULL, 
	error_message TEXT, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
);

-- Table: audit_logs
CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36), 
	user_id VARCHAR(36), 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(100) NOT NULL, 
	entity_id VARCHAR(36), 
	old_values JSON, 
	new_values JSON, 
	ip_address VARCHAR(50), 
	user_agent VARCHAR(500), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
);

-- Table: companies
CREATE TABLE companies (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	source_global_company_id VARCHAR(36), 
	name VARCHAR(255) NOT NULL, 
	legal_name VARCHAR(255), 
	domain VARCHAR(255), 
	cin VARCHAR(64), 
	gstin VARCHAR(64), 
	industry VARCHAR(150), 
	company_size VARCHAR(50), 
	phone VARCHAR(50), 
	email VARCHAR(255), 
	website VARCHAR(500), 
	address TEXT, 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	postal_code VARCHAR(20), 
	status VARCHAR(30) NOT NULL, 
	created_by VARCHAR(36), 
	custom_fields JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

-- Table: contacts
CREATE TABLE contacts (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	company_id VARCHAR(36), 
	source_global_contact_id VARCHAR(36), 
	first_name VARCHAR(100), 
	last_name VARCHAR(100), 
	full_name VARCHAR(255) NOT NULL, 
	designation VARCHAR(150), 
	department VARCHAR(100), 
	email VARCHAR(255), 
	phone VARCHAR(50), 
	alternate_phone VARCHAR(50), 
	linkedin_url VARCHAR(500), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_by VARCHAR(36), 
	custom_fields JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

-- Table: global_companies
CREATE TABLE global_companies (
	id VARCHAR(36) NOT NULL, 
	registry_country VARCHAR(10) NOT NULL, 
	registry_type VARCHAR(30) NOT NULL, 
	registry_id VARCHAR(64) NOT NULL, 
	legal_name VARCHAR(255) NOT NULL, 
	display_name VARCHAR(255), 
	company_type VARCHAR(50), 
	industry VARCHAR(150), 
	website VARCHAR(500), 
	email VARCHAR(255), 
	phone VARCHAR(50), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	postal_code VARCHAR(20), 
	status VARCHAR(30) NOT NULL, 
	first_seen_at DATETIME NOT NULL, 
	last_updated_at DATETIME NOT NULL, 
	metadata_json JSON NOT NULL, address VARCHAR(500), cin VARCHAR(500), registration_number VARCHAR(500), gst_number VARCHAR(500), pull_status VARCHAR(30) DEFAULT 'AVAILABLE', pulled_by_org_id VARCHAR(36), pulled_by_org_name VARCHAR(255), pulled_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table: global_company_contact_map
CREATE TABLE global_company_contact_map (
	id VARCHAR(36) NOT NULL, 
	company_id VARCHAR(36) NOT NULL, 
	contact_id VARCHAR(36) NOT NULL, 
	designation VARCHAR(150), 
	appointment_date DATE, 
	status VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES global_companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(contact_id) REFERENCES global_contacts (id) ON DELETE CASCADE
);

-- Table: global_contacts
CREATE TABLE global_contacts (
	id VARCHAR(36) NOT NULL, 
	registry_country VARCHAR(10) NOT NULL, 
	registry_type VARCHAR(30) NOT NULL, 
	registry_id VARCHAR(64), 
	full_name VARCHAR(255) NOT NULL, 
	designation VARCHAR(150), 
	email VARCHAR(255), 
	phone VARCHAR(50), 
	linkedin_url VARCHAR(500), 
	city VARCHAR(100), 
	status VARCHAR(30) NOT NULL, 
	first_seen_at DATETIME NOT NULL, 
	last_updated_at DATETIME NOT NULL, 
	metadata_json JSON NOT NULL, 
	PRIMARY KEY (id)
);

-- Table: global_data_pull_logs
CREATE TABLE global_data_pull_logs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	pulled_by VARCHAR(36) NOT NULL, 
	global_company_id VARCHAR(36), 
	global_contact_id VARCHAR(36), 
	resulting_company_id VARCHAR(36), 
	resulting_contact_id VARCHAR(36), 
	resulting_lead_id VARCHAR(36), 
	snapshot_json JSON NOT NULL, 
	pulled_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(pulled_by) REFERENCES users (id), 
	FOREIGN KEY(global_company_id) REFERENCES global_companies (id), 
	FOREIGN KEY(global_contact_id) REFERENCES global_contacts (id), 
	FOREIGN KEY(resulting_company_id) REFERENCES companies (id), 
	FOREIGN KEY(resulting_contact_id) REFERENCES contacts (id), 
	FOREIGN KEY(resulting_lead_id) REFERENCES leads (id)
);

-- Table: global_people
CREATE TABLE global_people (
	id VARCHAR(36) NOT NULL, 
	full_name VARCHAR(255) NOT NULL, 
	email VARCHAR(255), 
	phone VARCHAR(50), 
	designation VARCHAR(150), 
	company_name VARCHAR(255), 
	industry VARCHAR(150), 
	seniority VARCHAR(50), 
	department VARCHAR(100), 
	linkedin_url VARCHAR(500), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	estimated_value FLOAT NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	source VARCHAR(50) NOT NULL, 
	notes TEXT, 
	metadata_json JSON NOT NULL, 
	first_seen_at DATETIME NOT NULL, 
	last_updated_at DATETIME NOT NULL, associated_companies JSON DEFAULT '[]', pull_status VARCHAR(30) DEFAULT 'AVAILABLE', pulled_by_org_id VARCHAR(36), pulled_by_org_name VARCHAR(255), pulled_at DATETIME, 
	PRIMARY KEY (id)
);

-- Table: import_jobs
CREATE TABLE import_jobs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36), 
	uploaded_by VARCHAR(36) NOT NULL, 
	job_type VARCHAR(50) NOT NULL, 
	file_name VARCHAR(255) NOT NULL, 
	file_type VARCHAR(20) NOT NULL, 
	file_path VARCHAR(500), 
	total_rows INTEGER NOT NULL, 
	processed_rows INTEGER NOT NULL, 
	successful_rows INTEGER NOT NULL, 
	duplicate_rows INTEGER NOT NULL, 
	error_rows INTEGER NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	column_mapping JSON NOT NULL, 
	target_stage_id VARCHAR(36), 
	target_owner_id VARCHAR(36), 
	error_summary JSON NOT NULL, 
	started_at DATETIME, 
	completed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploaded_by) REFERENCES users (id), 
	FOREIGN KEY(target_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(target_owner_id) REFERENCES users (id)
);

-- Table: import_row_errors
CREATE TABLE import_row_errors (
	id VARCHAR(36) NOT NULL, 
	job_id VARCHAR(36) NOT NULL, 
	row_number INTEGER NOT NULL, 
	raw_data JSON NOT NULL, 
	error_code VARCHAR(100) NOT NULL, 
	error_message VARCHAR(500), 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_id) REFERENCES import_jobs (id) ON DELETE CASCADE
);

-- Table: lead_assignments
CREATE TABLE lead_assignments (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	assigned_by VARCHAR(36), 
	is_primary BOOLEAN NOT NULL, 
	assigned_at DATETIME NOT NULL, 
	unassigned_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
);

-- Table: lead_stage_history
CREATE TABLE lead_stage_history (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	from_stage_id VARCHAR(36), 
	to_stage_id VARCHAR(36) NOT NULL, 
	changed_by VARCHAR(36), 
	reason TEXT, 
	duration_seconds INTEGER, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(from_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(to_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(changed_by) REFERENCES users (id)
);

-- Table: leads
CREATE TABLE leads (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	company_id VARCHAR(36), 
	contact_id VARCHAR(36), 
	pipeline_stage_id VARCHAR(36) NOT NULL, 
	owner_id VARCHAR(36), 
	title VARCHAR(255) NOT NULL, 
	company_name VARCHAR(255), 
	contact_name VARCHAR(255), 
	contact_email VARCHAR(255), 
	contact_phone VARCHAR(50), 
	source VARCHAR(50) NOT NULL, 
	source_global_company_id VARCHAR(36), 
	source_global_contact_id VARCHAR(36), 
	status VARCHAR(30) NOT NULL, 
	priority VARCHAR(30) NOT NULL, 
	score INTEGER NOT NULL, 
	value NUMERIC(15, 2), 
	currency VARCHAR(10) NOT NULL, 
	description TEXT, 
	notes TEXT, 
	tags JSON NOT NULL, 
	created_by VARCHAR(36), 
	closed_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(pipeline_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

-- Table: masking_exceptions
CREATE TABLE masking_exceptions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	field VARCHAR(50) NOT NULL, 
	granted_by VARCHAR(36) NOT NULL, 
	granted_at DATETIME NOT NULL, 
	expires_at DATETIME NOT NULL, 
	reason TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(granted_by) REFERENCES users (id)
);

-- Table: masking_policies
CREATE TABLE masking_policies (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	tenant_role VARCHAR(50) NOT NULL, 
	field VARCHAR(50) NOT NULL, 
	is_masked BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

-- Table: organizations
CREATE TABLE organizations (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	timezone VARCHAR(100) NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	settings JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

-- Table: pipeline_stages
CREATE TABLE pipeline_stages (
	id VARCHAR(36) NOT NULL, 
	pipeline_id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	order_index INTEGER NOT NULL, 
	color VARCHAR(20), 
	win_probability NUMERIC(5, 2), 
	is_won BOOLEAN NOT NULL, 
	is_lost BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pipeline_id) REFERENCES pipelines (id) ON DELETE CASCADE
);

-- Table: pipelines
CREATE TABLE pipelines (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	description TEXT, 
	is_default BOOLEAN NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

-- Table: plans
CREATE TABLE plans (
	id VARCHAR(36) NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	seat_limit INTEGER NOT NULL, 
	monthly_pull_quota INTEGER NOT NULL, 
	price_amount NUMERIC(12, 2), 
	price_currency VARCHAR(10) NOT NULL, 
	feature_flags JSON NOT NULL, 
	is_active BOOLEAN NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
);

-- Table: radar_events
CREATE TABLE radar_events (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	actor_user_id VARCHAR(36) NOT NULL, 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	ip_address VARCHAR(50), 
	user_agent VARCHAR(500), 
	metadata_json JSON NOT NULL, 
	occurred_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE CASCADE
);

-- Table: subscriptions
CREATE TABLE subscriptions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	plan_id VARCHAR(36) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	seats_purchased INTEGER NOT NULL, 
	pull_quota_monthly INTEGER NOT NULL, 
	pull_quota_used INTEGER NOT NULL, 
	current_period_start DATE, 
	current_period_end DATE, 
	billing_provider VARCHAR(50) NOT NULL, 
	billing_reference VARCHAR(255), 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES plans (id)
);

-- Table: tasks
CREATE TABLE tasks (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36), 
	company_id VARCHAR(36), 
	contact_id VARCHAR(36), 
	task_type VARCHAR(50) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	description TEXT, 
	priority VARCHAR(30) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	due_at DATETIME, 
	completed_at DATETIME, 
	assigned_to VARCHAR(36), 
	created_by VARCHAR(36), 
	reschedule_count INTEGER NOT NULL, 
	reschedule_history JSON NOT NULL, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(assigned_to) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
);

-- Table: users
CREATE TABLE users (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36), 
	platform_role VARCHAR(30), 
	tenant_role VARCHAR(30), 
	full_name VARCHAR(255) NOT NULL, 
	email VARCHAR(255) NOT NULL, 
	phone VARCHAR(50), 
	password_hash VARCHAR(255) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	permission_overrides JSON NOT NULL, 
	last_login_at DATETIME, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
);

-- ==========================================================================
-- Indexes
-- ==========================================================================

-- Index: ix_activities_activity_type on activities
CREATE INDEX ix_activities_activity_type ON activities (activity_type);

-- Index: ix_activities_lead_id on activities
CREATE INDEX ix_activities_lead_id ON activities (lead_id);

-- Index: ix_activities_occurred_at on activities
CREATE INDEX ix_activities_occurred_at ON activities (occurred_at);

-- Index: ix_activities_organization_id on activities
CREATE INDEX ix_activities_organization_id ON activities (organization_id);

-- Index: ix_activities_user_id on activities
CREATE INDEX ix_activities_user_id ON activities (user_id);

-- Index: ix_ai_insights_entity_id on ai_insights
CREATE INDEX ix_ai_insights_entity_id ON ai_insights (entity_id);

-- Index: ix_ai_insights_organization_id on ai_insights
CREATE INDEX ix_ai_insights_organization_id ON ai_insights (organization_id);

-- Index: ix_ai_runs_organization_id on ai_runs
CREATE INDEX ix_ai_runs_organization_id ON ai_runs (organization_id);

-- Index: ix_ai_runs_run_type on ai_runs
CREATE INDEX ix_ai_runs_run_type ON ai_runs (run_type);

-- Index: ix_audit_logs_action on audit_logs
CREATE INDEX ix_audit_logs_action ON audit_logs (action);

-- Index: ix_audit_logs_created_at on audit_logs
CREATE INDEX ix_audit_logs_created_at ON audit_logs (created_at);

-- Index: ix_audit_logs_entity_id on audit_logs
CREATE INDEX ix_audit_logs_entity_id ON audit_logs (entity_id);

-- Index: ix_audit_logs_entity_type on audit_logs
CREATE INDEX ix_audit_logs_entity_type ON audit_logs (entity_type);

-- Index: ix_audit_logs_organization_id on audit_logs
CREATE INDEX ix_audit_logs_organization_id ON audit_logs (organization_id);

-- Index: ix_audit_logs_user_id on audit_logs
CREATE INDEX ix_audit_logs_user_id ON audit_logs (user_id);

-- Index: ix_companies_cin on companies
CREATE INDEX ix_companies_cin ON companies (cin);

-- Index: ix_companies_city on companies
CREATE INDEX ix_companies_city ON companies (city);

-- Index: ix_companies_domain on companies
CREATE INDEX ix_companies_domain ON companies (domain);

-- Index: ix_companies_industry on companies
CREATE INDEX ix_companies_industry ON companies (industry);

-- Index: ix_companies_name on companies
CREATE INDEX ix_companies_name ON companies (name);

-- Index: ix_companies_organization_id on companies
CREATE INDEX ix_companies_organization_id ON companies (organization_id);

-- Index: ix_companies_source_global_company_id on companies
CREATE INDEX ix_companies_source_global_company_id ON companies (source_global_company_id);

-- Index: ix_contacts_company_id on contacts
CREATE INDEX ix_contacts_company_id ON contacts (company_id);

-- Index: ix_contacts_email on contacts
CREATE INDEX ix_contacts_email ON contacts (email);

-- Index: ix_contacts_full_name on contacts
CREATE INDEX ix_contacts_full_name ON contacts (full_name);

-- Index: ix_contacts_organization_id on contacts
CREATE INDEX ix_contacts_organization_id ON contacts (organization_id);

-- Index: ix_contacts_phone on contacts
CREATE INDEX ix_contacts_phone ON contacts (phone);

-- Index: ix_contacts_source_global_contact_id on contacts
CREATE INDEX ix_contacts_source_global_contact_id ON contacts (source_global_contact_id);

-- Index: ix_global_companies_city on global_companies
CREATE INDEX ix_global_companies_city ON global_companies (city);

-- Index: ix_global_companies_email on global_companies
CREATE INDEX ix_global_companies_email ON global_companies (email);

-- Index: ix_global_companies_industry on global_companies
CREATE INDEX ix_global_companies_industry ON global_companies (industry);

-- Index: ix_global_companies_legal_name on global_companies
CREATE INDEX ix_global_companies_legal_name ON global_companies (legal_name);

-- Index: ix_global_companies_phone on global_companies
CREATE INDEX ix_global_companies_phone ON global_companies (phone);

-- Index: ix_global_companies_registry_id on global_companies
CREATE UNIQUE INDEX ix_global_companies_registry_id ON global_companies (registry_id);

-- Index: ix_global_company_contact_map_company_id on global_company_contact_map
CREATE INDEX ix_global_company_contact_map_company_id ON global_company_contact_map (company_id);

-- Index: ix_global_company_contact_map_contact_id on global_company_contact_map
CREATE INDEX ix_global_company_contact_map_contact_id ON global_company_contact_map (contact_id);

-- Index: ix_global_contacts_email on global_contacts
CREATE INDEX ix_global_contacts_email ON global_contacts (email);

-- Index: ix_global_contacts_full_name on global_contacts
CREATE INDEX ix_global_contacts_full_name ON global_contacts (full_name);

-- Index: ix_global_contacts_phone on global_contacts
CREATE INDEX ix_global_contacts_phone ON global_contacts (phone);

-- Index: ix_global_contacts_registry_id on global_contacts
CREATE INDEX ix_global_contacts_registry_id ON global_contacts (registry_id);

-- Index: ix_global_data_pull_logs_organization_id on global_data_pull_logs
CREATE INDEX ix_global_data_pull_logs_organization_id ON global_data_pull_logs (organization_id);

-- Index: ix_global_data_pull_logs_pulled_at on global_data_pull_logs
CREATE INDEX ix_global_data_pull_logs_pulled_at ON global_data_pull_logs (pulled_at);

-- Index: ix_global_people_city on global_people
CREATE INDEX ix_global_people_city ON global_people (city);

-- Index: ix_global_people_company_name on global_people
CREATE INDEX ix_global_people_company_name ON global_people (company_name);

-- Index: ix_global_people_department on global_people
CREATE INDEX ix_global_people_department ON global_people (department);

-- Index: ix_global_people_designation on global_people
CREATE INDEX ix_global_people_designation ON global_people (designation);

-- Index: ix_global_people_email on global_people
CREATE INDEX ix_global_people_email ON global_people (email);

-- Index: ix_global_people_full_name on global_people
CREATE INDEX ix_global_people_full_name ON global_people (full_name);

-- Index: ix_global_people_industry on global_people
CREATE INDEX ix_global_people_industry ON global_people (industry);

-- Index: ix_global_people_phone on global_people
CREATE INDEX ix_global_people_phone ON global_people (phone);

-- Index: ix_global_people_seniority on global_people
CREATE INDEX ix_global_people_seniority ON global_people (seniority);

-- Index: ix_import_jobs_organization_id on import_jobs
CREATE INDEX ix_import_jobs_organization_id ON import_jobs (organization_id);

-- Index: ix_import_jobs_status on import_jobs
CREATE INDEX ix_import_jobs_status ON import_jobs (status);

-- Index: ix_import_row_errors_job_id on import_row_errors
CREATE INDEX ix_import_row_errors_job_id ON import_row_errors (job_id);

-- Index: ix_lead_assignments_lead_id on lead_assignments
CREATE INDEX ix_lead_assignments_lead_id ON lead_assignments (lead_id);

-- Index: ix_lead_assignments_organization_id on lead_assignments
CREATE INDEX ix_lead_assignments_organization_id ON lead_assignments (organization_id);

-- Index: ix_lead_assignments_user_id on lead_assignments
CREATE INDEX ix_lead_assignments_user_id ON lead_assignments (user_id);

-- Index: ix_lead_stage_history_created_at on lead_stage_history
CREATE INDEX ix_lead_stage_history_created_at ON lead_stage_history (created_at);

-- Index: ix_lead_stage_history_lead_id on lead_stage_history
CREATE INDEX ix_lead_stage_history_lead_id ON lead_stage_history (lead_id);

-- Index: ix_lead_stage_history_organization_id on lead_stage_history
CREATE INDEX ix_lead_stage_history_organization_id ON lead_stage_history (organization_id);

-- Index: ix_leads_company_id on leads
CREATE INDEX ix_leads_company_id ON leads (company_id);

-- Index: ix_leads_company_name on leads
CREATE INDEX ix_leads_company_name ON leads (company_name);

-- Index: ix_leads_contact_email on leads
CREATE INDEX ix_leads_contact_email ON leads (contact_email);

-- Index: ix_leads_contact_id on leads
CREATE INDEX ix_leads_contact_id ON leads (contact_id);

-- Index: ix_leads_contact_name on leads
CREATE INDEX ix_leads_contact_name ON leads (contact_name);

-- Index: ix_leads_contact_phone on leads
CREATE INDEX ix_leads_contact_phone ON leads (contact_phone);

-- Index: ix_leads_organization_id on leads
CREATE INDEX ix_leads_organization_id ON leads (organization_id);

-- Index: ix_leads_owner_id on leads
CREATE INDEX ix_leads_owner_id ON leads (owner_id);

-- Index: ix_leads_pipeline_stage_id on leads
CREATE INDEX ix_leads_pipeline_stage_id ON leads (pipeline_stage_id);

-- Index: ix_leads_status on leads
CREATE INDEX ix_leads_status ON leads (status);

-- Index: ix_leads_title on leads
CREATE INDEX ix_leads_title ON leads (title);

-- Index: ix_masking_exceptions_lead_id on masking_exceptions
CREATE INDEX ix_masking_exceptions_lead_id ON masking_exceptions (lead_id);

-- Index: ix_masking_exceptions_organization_id on masking_exceptions
CREATE INDEX ix_masking_exceptions_organization_id ON masking_exceptions (organization_id);

-- Index: ix_masking_exceptions_user_id on masking_exceptions
CREATE INDEX ix_masking_exceptions_user_id ON masking_exceptions (user_id);

-- Index: ix_masking_policies_organization_id on masking_policies
CREATE INDEX ix_masking_policies_organization_id ON masking_policies (organization_id);

-- Index: ix_organizations_slug on organizations
CREATE UNIQUE INDEX ix_organizations_slug ON organizations (slug);

-- Index: ix_pipeline_stages_pipeline_id on pipeline_stages
CREATE INDEX ix_pipeline_stages_pipeline_id ON pipeline_stages (pipeline_id);

-- Index: ix_pipelines_organization_id on pipelines
CREATE INDEX ix_pipelines_organization_id ON pipelines (organization_id);

-- Index: ix_plans_code on plans
CREATE UNIQUE INDEX ix_plans_code ON plans (code);

-- Index: ix_radar_events_action on radar_events
CREATE INDEX ix_radar_events_action ON radar_events (action);

-- Index: ix_radar_events_actor_user_id on radar_events
CREATE INDEX ix_radar_events_actor_user_id ON radar_events (actor_user_id);

-- Index: ix_radar_events_occurred_at on radar_events
CREATE INDEX ix_radar_events_occurred_at ON radar_events (occurred_at);

-- Index: ix_radar_events_organization_id on radar_events
CREATE INDEX ix_radar_events_organization_id ON radar_events (organization_id);

-- Index: ix_subscriptions_organization_id on subscriptions
CREATE INDEX ix_subscriptions_organization_id ON subscriptions (organization_id);

-- Index: ix_tasks_assigned_to on tasks
CREATE INDEX ix_tasks_assigned_to ON tasks (assigned_to);

-- Index: ix_tasks_due_at on tasks
CREATE INDEX ix_tasks_due_at ON tasks (due_at);

-- Index: ix_tasks_lead_id on tasks
CREATE INDEX ix_tasks_lead_id ON tasks (lead_id);

-- Index: ix_tasks_organization_id on tasks
CREATE INDEX ix_tasks_organization_id ON tasks (organization_id);

-- Index: ix_users_email on users
CREATE INDEX ix_users_email ON users (email);

-- Index: ix_users_organization_id on users
CREATE INDEX ix_users_organization_id ON users (organization_id);

