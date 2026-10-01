import React, { useState, useEffect } from "react";
import { api, GlobalCompany, GlobalCompanyCreatePayload } from "../services/api";
import { Building2, X, Check, AlertCircle } from "lucide-react";
import { cleanPhoneInput, format10DigitPhone } from "../utils/phoneHelper";

interface EditCompanyModalProps {
  company: GlobalCompany | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (updatedCompany: GlobalCompany, pendingApproval?: boolean) => void;
  currentUser?: any;
}

export const EditCompanyModal: React.FC<EditCompanyModalProps> = ({
  company,
  isOpen,
  onClose,
  onSaved,
  currentUser,
}) => {
  const [formData, setFormData] = useState<Partial<GlobalCompanyCreatePayload>>({});
  const [statusVal, setStatusVal] = useState("ACTIVE");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (company) {
      setFormData({
        legal_name: company.legal_name || "",
        industry: company.industry || "",
        company_type: company.company_type || "Private Limited",
        cin: company.cin || "",
        registration_number: company.registration_number || "",
        gst_number: company.gst_number || "",
        address: company.address || "",
        city: company.city || "",
        postal_code: company.postal_code || "",
        state: company.state || "",
        country: company.country || "India",
        website: company.website || "",
        email: company.email || "",
        phone: company.phone || "",
      });
      setStatusVal(company.status || "ACTIVE");
      setFormError(null);
    }
  }, [company]);

  if (!isOpen || !company) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.legal_name || !formData.legal_name.trim()) {
      setFormError("Company Legal Name is required.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const payload: Partial<GlobalCompanyCreatePayload> & { status?: string } = {
        ...formData,
        legal_name: formData.legal_name.trim(),
        phone: formData.phone ? formData.phone.replace(/\D/g, "") : undefined,
        status: statusVal,
      };

      const isDataEntry = currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY";
      if (isDataEntry) {
        await api.submitGlobalEdit({
          entity_type: "COMPANY",
          entity_id: company.id,
          changes_json: payload,
        });
        onSaved(company, true);
      } else {
        const res = await api.updateGlobalCompany(company.id, payload);
        onSaved(res, false);
      }
      onClose();
    } catch (err: any) {
      setFormError(err.message || "Failed to update company record.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{
          width: "100%",
          maxWidth: "700px",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          padding: 0,
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "18px 24px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--bg-surface)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                backgroundColor: "var(--primary-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--primary)",
              }}
            >
              <Building2 style={{ width: "20px", height: "20px" }} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Edit Enterprise Profile
              </h3>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Update global registry details for{" "}
                <span style={{ color: "var(--primary)", fontWeight: 600 }}>{company.legal_name}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            style={{
              background: "transparent",
              border: "none",
              color: "var(--text-muted)",
              cursor: "pointer",
              padding: "4px",
              display: "flex",
              alignItems: "center",
            }}
          >
            <X style={{ width: "20px", height: "20px" }} />
          </button>
        </div>

        {/* Body Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
          <div
            style={{
              padding: "20px 24px",
              overflowY: "auto",
              flex: 1,
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {formError && (
              <div
                style={{
                  padding: "10px 14px",
                  borderRadius: "8px",
                  backgroundColor: "var(--rose-light)",
                  border: "1px solid var(--rose-border)",
                  color: "var(--rose-dark)",
                  fontSize: "0.8125rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <AlertCircle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
                <span>{formError}</span>
              </div>
            )}

            {/* Row 1: Company Name & Type */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Legal Company Name <span style={{ color: "var(--danger-color)" }}>*</span>
                </label>
                <input
                  type="text"
                  value={formData.legal_name || ""}
                  onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
                  placeholder="e.g. Acme Innovations Pvt Ltd"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-name"
                  required
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Company Type
                </label>
                <select
                  value={formData.company_type || "Private Limited"}
                  onChange={(e) => setFormData({ ...formData, company_type: e.target.value })}
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-type"
                >
                  <option value="Private Limited">Private Limited</option>
                  <option value="Public Limited">Public Limited</option>
                  <option value="LLP">LLP</option>
                  <option value="Partnership">Partnership</option>
                  <option value="Sole Proprietorship">Sole Proprietorship</option>
                  <option value="Government Entity">Government Entity</option>
                  <option value="Non-Profit">Non-Profit / Section 8</option>
                  <option value="Other">Other</option>
                </select>
              </div>
            </div>

            {/* Row 2: Industry & Status */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Industry Sector
                </label>
                <input
                  type="text"
                  value={formData.industry || ""}
                  onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                  placeholder="e.g. Information Technology, Healthcare"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-industry"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Status
                </label>
                <select
                  value={statusVal}
                  onChange={(e) => setStatusVal(e.target.value)}
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-status"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                </select>
              </div>
            </div>

            {/* Row 3: CIN, Registration Number & GST */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  CIN
                </label>
                <input
                  type="text"
                  value={formData.cin || ""}
                  onChange={(e) => setFormData({ ...formData, cin: e.target.value.toUpperCase() })}
                  placeholder="e.g. U72200MH2020PTC123456"
                  className="input-text"
                  style={{ width: "100%", fontFamily: "monospace", fontSize: "0.75rem" }}
                  id="edit-company-cin"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Registration Number
                </label>
                <input
                  type="text"
                  value={formData.registration_number || ""}
                  onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
                  placeholder="e.g. REG-987654"
                  className="input-text"
                  style={{ width: "100%", fontFamily: "monospace", fontSize: "0.75rem" }}
                  id="edit-company-reg"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  GST Number
                </label>
                <input
                  type="text"
                  value={formData.gst_number || ""}
                  onChange={(e) => setFormData({ ...formData, gst_number: e.target.value.toUpperCase() })}
                  placeholder="e.g. 27AAAAA0000A1Z5"
                  className="input-text"
                  style={{ width: "100%", fontFamily: "monospace", fontSize: "0.75rem" }}
                  id="edit-company-gst"
                />
              </div>
            </div>

            {/* Row 4: Address */}
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                Address
              </label>
              <input
                type="text"
                value={formData.address || ""}
                onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                placeholder="Street / Office Suite / Building Name"
                className="input-text"
                style={{ width: "100%" }}
                id="edit-company-address"
              />
            </div>

            {/* Row 5: City, Pincode, State */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  City
                </label>
                <input
                  type="text"
                  value={formData.city || ""}
                  onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                  placeholder="e.g. Mumbai, Bengaluru"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-city"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Pincode
                </label>
                <input
                  type="text"
                  value={formData.postal_code || ""}
                  onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                  placeholder="e.g. 400001"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-postal"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  State
                </label>
                <input
                  type="text"
                  value={formData.state || ""}
                  onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                  placeholder="e.g. Maharashtra, Karnataka"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-state"
                />
              </div>
            </div>

            {/* Row 6: Website, Contact Email, Phone */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Website
                </label>
                <input
                  type="url"
                  value={formData.website || ""}
                  onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                  placeholder="https://example.com"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-website"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Corporate Email
                </label>
                <input
                  type="email"
                  value={formData.email || ""}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  placeholder="info@example.com"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-email"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Official Phone
                </label>
                <input
                  type="tel"
                  maxLength={10}
                  value={formData.phone || ""}
                  onChange={(e) => setFormData({ ...formData, phone: cleanPhoneInput(e.target.value) })}
                  placeholder="e.g. 9876543210 (10 digits)"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-company-phone"
                />
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "flex-end",
              gap: "12px",
              backgroundColor: "var(--bg-surface-subtle)",
            }}
          >
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              disabled={saving}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-primary"
              disabled={saving}
              id="save-company-btn"
            >
              <Check style={{ width: "16px", height: "16px" }} />
              {saving ? "Saving..." : ((currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY") ? "Submit for Approval" : "Update Enterprise")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
