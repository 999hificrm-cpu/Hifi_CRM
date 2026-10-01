import React, { useState, useEffect } from "react";
import { api, GlobalPerson, AssociatedCompany } from "../services/api";
import { UserCheck, X, Check, AlertCircle, Plus, Trash2 } from "lucide-react";
import { cleanPhoneInput, format10DigitPhone } from "../utils/phoneHelper";

interface EditPersonModalProps {
  person: any | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved: (updatedPerson: any, pendingApproval?: boolean) => void;
  currentUser?: any;
}

export const EditPersonModal: React.FC<EditPersonModalProps> = ({
  person,
  isOpen,
  onClose,
  onSaved,
  currentUser,
}) => {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [designation, setDesignation] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [seniority, setSeniority] = useState("C-Level");
  const [department, setDepartment] = useState("Executive");
  const [industry, setIndustry] = useState("");
  const [linkedinUrl, setLinkedinUrl] = useState("");
  const [city, setCity] = useState("");
  const [stateVal, setStateVal] = useState("");
  const [country, setCountry] = useState("India");
  const [estimatedValue, setEstimatedValue] = useState<number | string>(0);
  const [statusVal, setStatusVal] = useState("ACTIVE");
  const [notes, setNotes] = useState("");
  const [associatedCompanies, setAssociatedCompanies] = useState<AssociatedCompany[]>([]);

  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    if (person) {
      setFullName(person.full_name || "");
      setEmail(person.email || "");
      setPhone(format10DigitPhone(person.phone) || "");
      setDesignation(person.designation || "");
      setCompanyName(person.company_name || "");
      setSeniority(person.seniority || "C-Level");
      setDepartment(person.department || "Executive");
      setIndustry(person.industry || "");
      setLinkedinUrl(person.linkedin_url || "");
      setCity(person.city || "");
      setStateVal(person.state || "");
      setCountry(person.country || "India");
      setEstimatedValue(person.estimated_value || 0);
      setStatusVal(person.status || "ACTIVE");
      setNotes(person.notes || "");

      if (person.associated_companies && Array.isArray(person.associated_companies)) {
        setAssociatedCompanies(
          person.associated_companies.map((ac: any) => ({
            company_name: ac.company_name || "",
            designation: ac.designation || "",
          }))
        );
      } else {
        setAssociatedCompanies([]);
      }
      setFormError(null);
    }
  }, [person]);

  if (!isOpen || !person) return null;

  const handleAddAssociatedCompany = () => {
    setAssociatedCompanies([...associatedCompanies, { company_name: "", designation: "" }]);
  };

  const handleRemoveAssociatedCompany = (index: number) => {
    setAssociatedCompanies(associatedCompanies.filter((_, i) => i !== index));
  };

  const handleUpdateAssociatedCompany = (index: number, field: keyof AssociatedCompany, val: string) => {
    const updated = [...associatedCompanies];
    updated[index] = { ...updated[index], [field]: val };
    setAssociatedCompanies(updated);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim()) {
      setFormError("Full Name is required.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      const cleanAssoc = associatedCompanies
        .filter((ac) => ac.company_name.trim())
        .map((ac) => ({
          company_name: ac.company_name.trim(),
          designation: ac.designation?.trim() || "",
        }));

      const payload: Partial<GlobalPerson> = {
        full_name: fullName.trim(),
        email: email.trim() || undefined,
        phone: phone ? phone.replace(/\D/g, "") : undefined,
        designation: designation.trim() || undefined,
        company_name: companyName.trim() || undefined,
        seniority: seniority || undefined,
        department: department || undefined,
        industry: industry.trim() || undefined,
        linkedin_url: linkedinUrl.trim() || undefined,
        city: city.trim() || undefined,
        state: stateVal.trim() || undefined,
        country: country.trim() || "India",
        estimated_value: Number(estimatedValue) || 0,
        status: statusVal,
        notes: notes.trim() || undefined,
        associated_companies: cleanAssoc,
      };

      const isDataEntry = currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY";
      if (isDataEntry) {
        await api.submitGlobalEdit({
          entity_type: "PERSON",
          entity_id: person.id,
          changes_json: payload,
        });
        onSaved(person, true);
      } else {
        const res = await api.updateGlobalPerson(person.id, payload);
        onSaved(res, false);
      }
      onClose();
    } catch (err: any) {
      setFormError(err.message || "Failed to update person lead.");
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
          maxWidth: "750px",
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
                backgroundColor: "var(--emerald-light)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--emerald)",
              }}
            >
              <UserCheck style={{ width: "20px", height: "20px" }} />
            </div>
            <div>
              <h3 style={{ margin: 0, fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Edit Decision Maker Profile
              </h3>
              <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Update executive intelligence for{" "}
                <span style={{ color: "var(--emerald)", fontWeight: 600 }}>{person.full_name}</span>
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

        {/* Form Body */}
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

            {/* Row 1: Full Name, Status */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Executive Full Name <span style={{ color: "var(--danger-color)" }}>*</span>
                </label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  placeholder="e.g. Vikram Singhania"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-name"
                  required
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
                  id="edit-person-status"
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                </select>
              </div>
            </div>

            {/* Row 2: Designation & Company Name */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Primary Designation / Title
                </label>
                <input
                  type="text"
                  value={designation}
                  onChange={(e) => setDesignation(e.target.value)}
                  placeholder="e.g. Managing Director / Chief Technology Officer"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-designation"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Primary Associated Company
                </label>
                <input
                  type="text"
                  value={companyName}
                  onChange={(e) => setCompanyName(e.target.value)}
                  placeholder="e.g. Apex Engineering Solutions"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-company"
                />
              </div>
            </div>

            {/* Row 3: Seniority, Department, Industry */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Seniority Level
                </label>
                <select
                  value={seniority}
                  onChange={(e) => setSeniority(e.target.value)}
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-seniority"
                >
                  <option value="C-Level">C-Level (CEO, CTO, MD)</option>
                  <option value="VP">VP / Vice President</option>
                  <option value="Director">Director</option>
                  <option value="Manager">Manager</option>
                  <option value="Lead">Lead / Supervisor</option>
                  <option value="Individual Contributor">Individual Contributor</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Department
                </label>
                <select
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-department"
                >
                  <option value="Executive">Executive / Management</option>
                  <option value="Sales">Sales & Revenue</option>
                  <option value="Engineering">Engineering / Tech</option>
                  <option value="Operations">Operations</option>
                  <option value="Marketing">Marketing</option>
                  <option value="Finance">Finance & Legal</option>
                  <option value="HR">Human Resources</option>
                  <option value="Product">Product</option>
                  <option value="Other">Other</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Industry
                </label>
                <input
                  type="text"
                  value={industry}
                  onChange={(e) => setIndustry(e.target.value)}
                  placeholder="e.g. Industrial Automation"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-industry"
                />
              </div>
            </div>

            {/* Row 4: Email & Phone */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Direct Work Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="e.g. v.singhania@apex-eng.com"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-email"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Direct Phone Number
                </label>
                <input
                  type="tel"
                  maxLength={10}
                  value={phone}
                  onChange={(e) => setPhone(cleanPhoneInput(e.target.value))}
                  placeholder="e.g. 9820055667 (10 digits)"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-phone"
                />
              </div>
            </div>

            {/* Row 5: City, State, Country */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  City
                </label>
                <input
                  type="text"
                  value={city}
                  onChange={(e) => setCity(e.target.value)}
                  placeholder="e.g. Pune"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-city"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  State
                </label>
                <input
                  type="text"
                  value={stateVal}
                  onChange={(e) => setStateVal(e.target.value)}
                  placeholder="e.g. Maharashtra"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-state"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Country
                </label>
                <input
                  type="text"
                  value={country}
                  onChange={(e) => setCountry(e.target.value)}
                  placeholder="e.g. India"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-country"
                />
              </div>
            </div>

            {/* Row 6: LinkedIn URL & Estimated Value */}
            <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "12px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  LinkedIn Profile URL
                </label>
                <input
                  type="url"
                  value={linkedinUrl}
                  onChange={(e) => setLinkedinUrl(e.target.value)}
                  placeholder="https://linkedin.com/in/username"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-linkedin"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Est. Deal Value (₹)
                </label>
                <input
                  type="number"
                  value={estimatedValue}
                  onChange={(e) => setEstimatedValue(e.target.value)}
                  placeholder="0"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="edit-person-value"
                />
              </div>
            </div>

            {/* Row 7: Associated Companies Section */}
            <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "14px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <label style={{ fontSize: "0.8rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  Additional Associated Companies
                </label>
                <button
                  type="button"
                  onClick={handleAddAssociatedCompany}
                  className="btn-secondary"
                  style={{ padding: "4px 10px", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "4px" }}
                >
                  <Plus style={{ width: "14px", height: "14px" }} /> Add Associated Company
                </button>
              </div>

              {associatedCompanies.length === 0 ? (
                <div style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic", padding: "6px 0" }}>
                  No extra company associations. Primary company is specified above.
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {associatedCompanies.map((ac, idx) => (
                    <div
                      key={idx}
                      style={{
                        display: "grid",
                        gridTemplateColumns: "1fr 1fr auto",
                        gap: "8px",
                        alignItems: "center",
                      }}
                    >
                      <input
                        type="text"
                        value={ac.company_name}
                        onChange={(e) => handleUpdateAssociatedCompany(idx, "company_name", e.target.value)}
                        placeholder="Company Name"
                        className="input-text"
                        style={{ fontSize: "0.8rem", padding: "6px 10px" }}
                      />
                      <input
                        type="text"
                        value={ac.designation || ""}
                        onChange={(e) => handleUpdateAssociatedCompany(idx, "designation", e.target.value)}
                        placeholder="Role / Designation in this Company"
                        className="input-text"
                        style={{ fontSize: "0.8rem", padding: "6px 10px" }}
                      />
                      <button
                        type="button"
                        onClick={() => handleRemoveAssociatedCompany(idx)}
                        style={{
                          background: "transparent",
                          border: "none",
                          color: "var(--rose)",
                          cursor: "pointer",
                          padding: "6px",
                          display: "flex",
                          alignItems: "center",
                          borderRadius: "6px",
                        }}
                        title="Remove"
                      >
                        <Trash2 style={{ width: "16px", height: "16px" }} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Row 8: Notes */}
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                Internal Intelligence Notes
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Background notes, key decision dynamics, communication preferences..."
                className="input-text"
                style={{ width: "100%", minHeight: "60px", resize: "vertical" }}
                id="edit-person-notes"
              />
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
              id="save-person-btn"
            >
              <Check style={{ width: "16px", height: "16px" }} />
              {saving ? "Saving..." : ((currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY") ? "Submit for Approval" : "Update Profile")}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
