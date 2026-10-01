# JARVIS CRM — Product Bible (Source of Truth)

## 1. What Jarvis CRM Is
JARVIS CRM is a **multi-tenant Lead Intelligence Radar and Controlled Outbound Sales Platform**. It integrates a platform-wide Global Business Intelligence registry with an isolated tenant-level CRM, hardened against data theft through field-level masking and audit logging.

## 2. What Jarvis CRM Is NOT
- It is NOT a generic, unconstrained contact book where telecallers can export customer lists to Excel.
- It is NOT a microservices maze or college prototype.
- It does NOT duplicate entities (no `crm_people`, no duplicate registries).

## 3. Product Principles
1. **Global Data ≠ Customer Data ≠ CRM Activity Data**:
   - Platform admins curate the Global Intelligence Registry.
   - Customers pull licensed snapshots into their private CRM workspace.
2. **Contact Protection by Design**:
   - Telecallers execute calls, WhatsApp, and emails through platform triggers without raw phone numbers or emails being exposed in the DOM or API payloads.
3. **Pipeline Immutability**:
   - Pipelines belong to the organization. Ingesting 1,000 or 100,000 leads creates lead records and appends stage history; it NEVER modifies or duplicates pipeline configuration.
4. **Autonomous Opportunity Radar**:
   - Instead of a static table, Jarvis highlights high-probability deals, stale leads, and overdue follow-ups.
