
CREATE TABLE global_companies (
	id VARCHAR(36) NOT NULL, 
	registry_country VARCHAR(10) NOT NULL, 
	registry_type VARCHAR(30) NOT NULL, 
	registry_id VARCHAR(64) NOT NULL, 
	legal_name VARCHAR(255) NOT NULL, 
	display_name VARCHAR(255), 
	company_type VARCHAR(50), 
	industry VARCHAR(150), 
	cin VARCHAR(64), 
	registration_number VARCHAR(64), 
	gst_number VARCHAR(64), 
	address VARCHAR(500), 
	city VARCHAR(100), 
	state VARCHAR(100), 
	country VARCHAR(100) NOT NULL, 
	postal_code VARCHAR(20), 
	website VARCHAR(500), 
	email VARCHAR(255), 
	phone VARCHAR(50), 
	status VARCHAR(30) NOT NULL, 
	first_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	metadata_json JSON NOT NULL, 
	PRIMARY KEY (id)
)

;

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
	first_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	metadata_json JSON NOT NULL, 
	PRIMARY KEY (id)
)

;

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
	associated_companies JSON NOT NULL, 
	metadata_json JSON NOT NULL, 
	first_seen_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	last_updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE idempotency_records (
	id VARCHAR(36) NOT NULL, 
	key VARCHAR(128) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	action VARCHAR(100) NOT NULL, 
	request_hash VARCHAR(64) NOT NULL, 
	response_status INTEGER NOT NULL, 
	response_body JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE job_runs (
	id VARCHAR(36) NOT NULL, 
	job_id VARCHAR(100) NOT NULL, 
	job_type VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	attempt INTEGER NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	duration_seconds INTEGER, 
	error_message TEXT, 
	error_traceback TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE organizations (
	id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	slug VARCHAR(100) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	timezone VARCHAR(100) NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	schema_name VARCHAR(100), 
	settings JSON NOT NULL, 
	feature_overrides JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	deleted_at TIMESTAMP WITHOUT TIME ZONE, 
	deleted_by VARCHAR(36), 
	deletion_reason VARCHAR(500), 
	PRIMARY KEY (id)
)

;

CREATE TABLE permissions (
	id VARCHAR(36) NOT NULL, 
	code VARCHAR(100) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	category VARCHAR(50) NOT NULL, 
	description VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE platform_roles (
	id VARCHAR(36) NOT NULL, 
	code VARCHAR(50) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	description VARCHAR(255), 
	is_system BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE TABLE admin_action_items (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	item_type VARCHAR(50) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	action_url VARCHAR(500), 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE api_rate_limits (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	daily_request_limit INTEGER NOT NULL, 
	requests_today INTEGER NOT NULL, 
	last_reset_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (organization_id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE billing_events (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36), 
	provider VARCHAR(50) NOT NULL, 
	event_type VARCHAR(100) NOT NULL, 
	payload JSON NOT NULL, 
	processed_status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE data_quality_jobs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	issues_found INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE followup_policies (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	name VARCHAR(100) NOT NULL, 
	trigger_outcome VARCHAR(50) NOT NULL, 
	max_attempts INTEGER, 
	interval_minutes INTEGER, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE global_company_contact_map (
	id VARCHAR(36) NOT NULL, 
	company_id VARCHAR(36) NOT NULL, 
	contact_id VARCHAR(36) NOT NULL, 
	designation VARCHAR(150), 
	appointment_date DATE, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(company_id) REFERENCES global_companies (id) ON DELETE CASCADE, 
	FOREIGN KEY(contact_id) REFERENCES global_contacts (id) ON DELETE CASCADE
)

;

CREATE TABLE integrations (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(50) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	config JSON NOT NULL, 
	last_synced_at TIMESTAMP WITHOUT TIME ZONE, 
	last_error VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE masking_policies (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	tenant_role VARCHAR(50) NOT NULL, 
	field VARCHAR(50) NOT NULL, 
	is_masked BOOLEAN NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE notification_rules (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(50) NOT NULL, 
	channels JSON NOT NULL, 
	is_active BOOLEAN, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE pipelines (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	description VARCHAR(500), 
	is_default BOOLEAN NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	segment VARCHAR(10), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE role_permissions (
	id VARCHAR(36) NOT NULL, 
	role_id VARCHAR(36) NOT NULL, 
	permission_id VARCHAR(36) NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_role_permission UNIQUE (role_id, permission_id), 
	FOREIGN KEY(role_id) REFERENCES platform_roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(permission_id) REFERENCES permissions (id) ON DELETE CASCADE
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES plans (id)
)

;

CREATE TABLE templates (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	medium VARCHAR(50) NOT NULL, 
	subject VARCHAR(255), 
	body_template TEXT NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

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
	token_version INTEGER NOT NULL, 
	permission_overrides JSON NOT NULL, 
	last_login_at TIMESTAMP WITHOUT TIME ZONE, 
	gmail_tokens JSON, 
	telecaller_targets JSON, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	deleted_at TIMESTAMP WITHOUT TIME ZONE, 
	deleted_by VARCHAR(36), 
	deletion_reason VARCHAR(500), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE absence_delegations (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	absent_user_id VARCHAR(36) NOT NULL, 
	cover_user_id VARCHAR(36) NOT NULL, 
	start_date DATE NOT NULL, 
	end_date DATE NOT NULL, 
	reason TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(absent_user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(cover_user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE admin_alerts (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	alert_type VARCHAR(50) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	title VARCHAR(200) NOT NULL, 
	message VARCHAR(1000), 
	status VARCHAR(30) NOT NULL, 
	resolved_at TIMESTAMP WITHOUT TIME ZONE, 
	resolved_by VARCHAR(36), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(resolved_by) REFERENCES users (id) ON DELETE SET NULL
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE api_keys (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36), 
	name VARCHAR(100) NOT NULL, 
	key_prefix VARCHAR(10) NOT NULL, 
	key_hash VARCHAR(128) NOT NULL, 
	scopes JSON NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	last_used_at TIMESTAMP WITHOUT TIME ZONE, 
	status VARCHAR(30) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE attendance_sessions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	login_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	logout_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE availability_status (
	user_id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE break_sessions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	started_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ended_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	deleted_at TIMESTAMP WITHOUT TIME ZONE, 
	deleted_by VARCHAR(36), 
	deletion_reason VARCHAR(500), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(created_by) REFERENCES users (id)
)

;

CREATE TABLE daily_call_plans (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	date TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	generated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE data_quality_issues (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	job_id VARCHAR(36), 
	entity_type VARCHAR(50) NOT NULL, 
	entity_id VARCHAR(36) NOT NULL, 
	issue_type VARCHAR(50) NOT NULL, 
	severity VARCHAR(20) NOT NULL, 
	details_json JSON NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	resolved_by VARCHAR(36), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(job_id) REFERENCES data_quality_jobs (id) ON DELETE CASCADE, 
	FOREIGN KEY(resolved_by) REFERENCES users (id)
)

;

CREATE TABLE eod_reports (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	report_date DATE NOT NULL, 
	metrics_snapshot JSON NOT NULL, 
	ai_summary TEXT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE global_data_change_requests (
	id VARCHAR(36) NOT NULL, 
	global_entity_type VARCHAR(50) NOT NULL, 
	global_entity_id VARCHAR(36) NOT NULL, 
	requested_by VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36), 
	proposed_changes JSON NOT NULL, 
	reason VARCHAR(500), 
	status VARCHAR(30) NOT NULL, 
	reviewed_by VARCHAR(36), 
	reviewed_at TIMESTAMP WITHOUT TIME ZONE, 
	review_notes VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requested_by) REFERENCES users (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(reviewed_by) REFERENCES users (id)
)

;

CREATE TABLE integration_credentials (
	id VARCHAR(36) NOT NULL, 
	integration_id VARCHAR(36) NOT NULL, 
	encrypted_payload VARCHAR(2000) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (integration_id), 
	FOREIGN KEY(integration_id) REFERENCES integrations (id) ON DELETE CASCADE
)

;

CREATE TABLE integration_events (
	id VARCHAR(36) NOT NULL, 
	integration_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(50) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	payload JSON, 
	error_message VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(integration_id) REFERENCES integrations (id) ON DELETE CASCADE
)

;

CREATE TABLE leave_requests (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	reason VARCHAR(255), 
	approved_by VARCHAR(36), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(approved_by) REFERENCES users (id) ON DELETE SET NULL
)

;

CREATE TABLE notifications (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	recipient_id VARCHAR(36) NOT NULL, 
	event_type VARCHAR(50) NOT NULL, 
	event_key VARCHAR(100), 
	title VARCHAR(200) NOT NULL, 
	body VARCHAR(1000), 
	action_url VARCHAR(500), 
	is_read BOOLEAN, 
	read_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(recipient_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE payment_transactions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	subscription_id VARCHAR(36) NOT NULL, 
	amount NUMERIC(12, 2) NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	provider_reference VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(subscription_id) REFERENCES subscriptions (id) ON DELETE CASCADE
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(pipeline_id) REFERENCES pipelines (id) ON DELETE CASCADE
)

;

CREATE TABLE platform_user_roles (
	id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	role_id VARCHAR(36) NOT NULL, 
	assigned_by VARCHAR(36), 
	assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_platform_role UNIQUE (user_id, role_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(role_id) REFERENCES platform_roles (id) ON DELETE CASCADE, 
	FOREIGN KEY(assigned_by) REFERENCES users (id) ON DELETE SET NULL
)

;

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
	occurred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE revoked_tokens (
	id VARCHAR(36) NOT NULL, 
	token_hash VARCHAR(64) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	reason VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE support_sessions (
	id VARCHAR(36) NOT NULL, 
	created_by VARCHAR(36) NOT NULL, 
	target_user_id VARCHAR(36), 
	organization_id VARCHAR(36) NOT NULL, 
	reason VARCHAR(500) NOT NULL, 
	started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	revoked_at TIMESTAMP WITHOUT TIME ZONE, 
	ip_address VARCHAR(50), 
	user_agent VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(created_by) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(target_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE
)

;

CREATE TABLE telecaller_sessions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	start_time TIMESTAMP WITH TIME ZONE NOT NULL, 
	end_time TIMESTAMP WITH TIME ZONE, 
	calls_made INTEGER, 
	total_talk_time_seconds INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE telecaller_targets (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	target_date DATE NOT NULL, 
	target_calls INTEGER, 
	target_connects INTEGER, 
	target_talk_time_minutes INTEGER, 
	target_qualified_leads INTEGER, 
	target_conversions INTEGER, 
	target_revenue FLOAT, 
	achieved_calls INTEGER, 
	achieved_connects INTEGER, 
	achieved_talk_time_minutes INTEGER, 
	achieved_qualified_leads INTEGER, 
	achieved_conversions INTEGER, 
	achieved_revenue FLOAT, 
	created_at TIMESTAMP WITH TIME ZONE, 
	updated_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)

;

CREATE TABLE api_usage_events (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	api_key_id VARCHAR(36), 
	user_id VARCHAR(36), 
	endpoint VARCHAR(200) NOT NULL, 
	method VARCHAR(10) NOT NULL, 
	status_code INTEGER NOT NULL, 
	response_time_ms INTEGER, 
	ip_address VARCHAR(50), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(api_key_id) REFERENCES api_keys (id) ON DELETE SET NULL, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL
)

;

CREATE TABLE audit_logs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36), 
	user_id VARCHAR(36), 
	actor_user_id VARCHAR(36), 
	target_user_id VARCHAR(36), 
	support_session_id VARCHAR(36), 
	context_type VARCHAR(30) NOT NULL, 
	reason VARCHAR(500), 
	action VARCHAR(100) NOT NULL, 
	entity_type VARCHAR(100) NOT NULL, 
	entity_id VARCHAR(36), 
	old_values JSON, 
	new_values JSON, 
	ip_address VARCHAR(50), 
	user_agent VARCHAR(500), 
	sequence_number INTEGER, 
	event_hash VARCHAR(64), 
	previous_event_hash VARCHAR(64), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(actor_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(target_user_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(support_session_id) REFERENCES support_sessions (id) ON DELETE SET NULL
)

;

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
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	deleted_at TIMESTAMP WITHOUT TIME ZONE, 
	deleted_by VARCHAR(36), 
	deletion_reason VARCHAR(500), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id)
)

;

CREATE TABLE data_quality_resolutions (
	id VARCHAR(36) NOT NULL, 
	issue_id VARCHAR(36) NOT NULL, 
	applied_by VARCHAR(36) NOT NULL, 
	action_taken VARCHAR(50) NOT NULL, 
	previous_data JSON NOT NULL, 
	new_data JSON NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(issue_id) REFERENCES data_quality_issues (id) ON DELETE CASCADE, 
	FOREIGN KEY(applied_by) REFERENCES users (id)
)

;

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
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(uploaded_by) REFERENCES users (id), 
	FOREIGN KEY(target_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(target_owner_id) REFERENCES users (id)
)

;

CREATE TABLE notification_deliveries (
	id VARCHAR(36) NOT NULL, 
	notification_id VARCHAR(36) NOT NULL, 
	channel VARCHAR(20) NOT NULL, 
	status VARCHAR(20) NOT NULL, 
	external_id VARCHAR(100), 
	error_message VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(notification_id) REFERENCES notifications (id) ON DELETE CASCADE
)

;

CREATE TABLE contact_phones (
	id VARCHAR(36) NOT NULL, 
	contact_id VARCHAR(36) NOT NULL, 
	phone_number VARCHAR(50) NOT NULL, 
	phone_type VARCHAR(20) NOT NULL, 
	label VARCHAR(50), 
	is_primary BOOLEAN NOT NULL, 
	is_whatsapp BOOLEAN NOT NULL, 
	is_sms_capable BOOLEAN NOT NULL, 
	is_callable BOOLEAN NOT NULL, 
	is_verified BOOLEAN NOT NULL, 
	country_code VARCHAR(5), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE CASCADE
)

;

CREATE TABLE import_row_errors (
	id VARCHAR(36) NOT NULL, 
	job_id VARCHAR(36) NOT NULL, 
	row_number INTEGER NOT NULL, 
	raw_data JSON NOT NULL, 
	error_code VARCHAR(100) NOT NULL, 
	error_message VARCHAR(500), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(job_id) REFERENCES import_jobs (id) ON DELETE CASCADE
)

;

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
	lead_type VARCHAR(50), 
	segment VARCHAR(10), 
	status VARCHAR(30) NOT NULL, 
	priority VARCHAR(30) NOT NULL, 
	score INTEGER NOT NULL, 
	value NUMERIC(15, 2), 
	currency VARCHAR(10) NOT NULL, 
	description TEXT, 
	notes TEXT, 
	tags JSON NOT NULL, 
	created_by VARCHAR(36), 
	closed_at TIMESTAMP WITHOUT TIME ZONE, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	deleted_at TIMESTAMP WITHOUT TIME ZONE, 
	deleted_by VARCHAR(36), 
	deletion_reason VARCHAR(500), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(pipeline_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(owner_id) REFERENCES users (id) ON DELETE SET NULL, 
	FOREIGN KEY(created_by) REFERENCES users (id)
)

;

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
	occurred_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE call_records (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36), 
	contact_id VARCHAR(36), 
	user_id VARCHAR(36) NOT NULL, 
	provider VARCHAR(30), 
	provider_call_id VARCHAR(100), 
	direction VARCHAR(10), 
	started_at TIMESTAMP WITHOUT TIME ZONE, 
	answered_at TIMESTAMP WITHOUT TIME ZONE, 
	ended_at TIMESTAMP WITHOUT TIME ZONE, 
	duration_seconds INTEGER, 
	disposition VARCHAR(50), 
	recording_url TEXT, 
	transcript TEXT, 
	ai_summary TEXT, 
	sentiment VARCHAR(20), 
	ai_score NUMERIC(5, 2), 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(user_id) REFERENCES users (id)
)

;

CREATE TABLE communication_logs (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36), 
	channel VARCHAR(20) NOT NULL, 
	direction VARCHAR(10) NOT NULL, 
	message_id VARCHAR(100), 
	body TEXT, 
	status VARCHAR(20) NOT NULL, 
	sent_at TIMESTAMP WITH TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
)

;

CREATE TABLE daily_tasks (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	plan_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	sequence INTEGER NOT NULL, 
	source VARCHAR(20) NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(plan_id) REFERENCES daily_call_plans (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
)

;

CREATE TABLE dedupe_candidates (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id_a VARCHAR(36) NOT NULL, 
	lead_id_b VARCHAR(36) NOT NULL, 
	match_confidence NUMERIC, 
	match_basis VARCHAR(100), 
	status VARCHAR(20) NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id_a) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id_b) REFERENCES leads (id) ON DELETE CASCADE
)

;

CREATE TABLE lead_assignments (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	assigned_by VARCHAR(36), 
	is_primary BOOLEAN NOT NULL, 
	assigned_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	unassigned_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id), 
	FOREIGN KEY(assigned_by) REFERENCES users (id)
)

;

CREATE TABLE lead_stage_history (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	from_stage_id VARCHAR(36), 
	to_stage_id VARCHAR(36) NOT NULL, 
	changed_by VARCHAR(36), 
	reason TEXT, 
	duration_seconds INTEGER, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(from_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(to_stage_id) REFERENCES pipeline_stages (id), 
	FOREIGN KEY(changed_by) REFERENCES users (id)
)

;

CREATE TABLE masking_exceptions (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	user_id VARCHAR(36) NOT NULL, 
	field VARCHAR(50) NOT NULL, 
	granted_by VARCHAR(36) NOT NULL, 
	granted_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	reason TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, 
	FOREIGN KEY(granted_by) REFERENCES users (id)
)

;

CREATE TABLE payments (
	id VARCHAR(36) NOT NULL, 
	organization_id VARCHAR(36) NOT NULL, 
	lead_id VARCHAR(36) NOT NULL, 
	amount NUMERIC(15, 2) NOT NULL, 
	currency VARCHAR(10) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	payment_link VARCHAR(500), 
	reference_id VARCHAR(255), 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE
)

;

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
	due_at TIMESTAMP WITHOUT TIME ZONE, 
	completed_at TIMESTAMP WITHOUT TIME ZONE, 
	assigned_to VARCHAR(36), 
	created_by VARCHAR(36), 
	reschedule_count INTEGER NOT NULL, 
	reschedule_history JSON NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organizations (id) ON DELETE CASCADE, 
	FOREIGN KEY(lead_id) REFERENCES leads (id) ON DELETE CASCADE, 
	FOREIGN KEY(company_id) REFERENCES companies (id) ON DELETE SET NULL, 
	FOREIGN KEY(contact_id) REFERENCES contacts (id) ON DELETE SET NULL, 
	FOREIGN KEY(assigned_to) REFERENCES users (id), 
	FOREIGN KEY(created_by) REFERENCES users (id)
)

;
