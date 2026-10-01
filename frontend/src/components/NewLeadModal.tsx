import React, { useEffect, useState } from "react";
import { api, PipelineStage, ProductService } from "../services/api";
import { X, UserPlus, AlertCircle } from "lucide-react";
import { cleanPhoneInput } from "../utils/phoneHelper";

interface NewLeadModalProps {
  stages: PipelineStage[];
  onClose: () => void;
  onSuccess: () => void;
}

export const NewLeadModal: React.FC<NewLeadModalProps> = ({ stages, onClose, onSuccess }) => {
  const [title, setTitle] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [value, setValue] = useState("100000");
  const [stageId, setStageId] = useState(stages[0]?.id || "");
  const [priority, setPriority] = useState("MEDIUM");
  const [notes, setNotes] = useState("");
  const [purpose, setPurpose] = useState("");
  const [productServiceId, setProductServiceId] = useState("");
  const [productServices, setProductServices] = useState<ProductService[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.getProductServices(true)
      .then(setProductServices)
      .catch(() => setProductServices([]));
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title) return;
    setLoading(true);
    setError(null);
    try {
      await api.createLead({
        title,
        company_name: companyName || null,
        contact_name: contactName || null,
        contact_phone: contactPhone ? contactPhone.replace(/\D/g, "") : null,
        contact_email: contactEmail || null,
        value: Number(value),
        pipeline_stage_id: stageId || null,
        priority,
        notes: notes || null,
        product_service_id: productServiceId || null,
        purpose: purpose || null,
      });
      onSuccess();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create lead");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "540px", padding: "24px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "14px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "18px" }}>
          <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
            <UserPlus style={{ width: "20px", height: "20px", color: "var(--primary)" }} />
            Create New CRM Lead
          </h3>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}>
            <X style={{ width: "20px", height: "20px" }} />
          </button>
        </div>

        {error && (
          <div style={{
            marginBottom: "14px",
            padding: "10px 14px",
            borderRadius: "8px",
            background: "var(--rose-light)",
            border: "1px solid var(--rose-border)",
            color: "var(--rose-dark)",
            fontSize: "0.8125rem",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <AlertCircle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
              Opportunity Title *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Enterprise Expansion - Apex Tech"
              className="input-text"
              required
            />
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Company / Account
              </label>
              <input
                type="text"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                placeholder="e.g. Apex Tech Ltd"
                className="input-text"
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Contact Person Name
              </label>
              <input
                type="text"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
                placeholder="e.g. Rahul Mehta"
                className="input-text"
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Phone Number (10 Digits)
              </label>
              <input
                type="tel"
                maxLength={10}
                value={contactPhone}
                onChange={(e) => setContactPhone(cleanPhoneInput(e.target.value))}
                placeholder="e.g. 9876543210"
                className="input-text"
              />
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Email Address
              </label>
              <input
                type="email"
                value={contactEmail}
                onChange={(e) => setContactEmail(e.target.value)}
                placeholder="rahul@apextech.com"
                className="input-text"
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Pipeline Stage
              </label>
              <select
                value={stageId}
                onChange={(e) => setStageId(e.target.value)}
                className="select-dropdown"
              >
                {stages.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Priority
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
                className="select-dropdown"
              >
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="URGENT">Urgent</option>
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Estimated Value (₹)
              </label>
              <input
                type="number"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                className="input-text"
                style={{ fontFamily: "monospace" }}
              />
            </div>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Product / Service
              </label>
              <select value={productServiceId} onChange={(e) => setProductServiceId(e.target.value)} className="select-dropdown">
                <option value="">Not selected</option>
                {productServices.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                Purpose
              </label>
              <input
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                placeholder="e.g. Interested in our data science course"
                className="input-text"
              />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
              Notes
            </label>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              placeholder="Initial lead context, product interest, source..."
              rows={2}
              className="textarea-field"
            />
          </div>

          <div style={{ paddingTop: "14px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
            <button type="button" onClick={onClose} className="btn-secondary">
              Cancel
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Creating..." : "Save Lead to Pipeline"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
