import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { LayoutTemplate, Plus, Mail, MessageCircle, Phone, FileText, X } from "lucide-react";

export const TemplatesView: React.FC = () => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  const [showNewModal, setShowNewModal] = useState(false);
  const [formData, setFormData] = useState({
    name: "",
    medium: "EMAIL",
    subject: "",
    body_template: "Hello {{ lead.contact_name }},\n\nWe would like to..."
  });
  
  useEffect(() => {
    loadTemplates();
  }, []);
  
  const loadTemplates = async () => {
    setLoading(true);
    try {
      const data = await api.getTemplates();
      setTemplates(data || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      await api.createTemplate(formData);
      setShowNewModal(false);
      setFormData({
        name: "",
        medium: "EMAIL",
        subject: "",
        body_template: "Hello {{ lead.contact_name }},\n\nWe would like to..."
      });
      loadTemplates();
    } catch (e: any) {
      alert("Error creating template. Check Jinja syntax.");
    }
  };

  const getMediumIcon = (medium: string) => {
    if (medium === "EMAIL") return <Mail style={{ width: 14, height: 14 }} />;
    if (medium === "WHATSAPP") return <MessageCircle style={{ width: 14, height: 14 }} />;
    if (medium === "SMS") return <Phone style={{ width: 14, height: 14 }} />;
    return <FileText style={{ width: 14, height: 14 }} />;
  };

  return (
    <div style={{ padding: "32px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
            <LayoutTemplate style={{ color: "var(--primary)" }} />
            Communication Templates
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "4px" }}>
            Manage Jinja-powered templates for Email, SMS, and WhatsApp across the organization.
          </p>
        </div>
        <button onClick={() => setShowNewModal(true)} className="btn-primary" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <Plus style={{ width: 16, height: 16 }} />
          New Template
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: "16px" }}>
        {loading ? (
          <p>Loading templates...</p>
        ) : templates.length === 0 ? (
          <div className="card" style={{ padding: "32px", textAlign: "center", color: "var(--text-muted)", gridColumn: "1 / -1" }}>
            No templates configured. Create one to get started.
          </div>
        ) : (
          templates.map((t) => (
            <div key={t.id} className="card" style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "12px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span className="badge badge-medium" style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                  {getMediumIcon(t.medium)} {t.medium}
                </span>
              </div>
              <h3 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)" }}>{t.name}</h3>
              {t.subject && (
                <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                  Subject: {t.subject}
                </p>
              )}
              <div style={{
                background: "var(--bg-surface-subtle)",
                padding: "12px",
                borderRadius: "8px",
                fontSize: "0.75rem",
                fontFamily: "monospace",
                color: "var(--text-secondary)",
                whiteSpace: "pre-wrap",
                flex: 1
              }}>
                {t.body_template}
              </div>
            </div>
          ))
        )}
      </div>

      {showNewModal && (
        <div className="modal-overlay">
          <div className="modal-dialog" style={{ maxWidth: "540px", width: "100%", padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "14px", borderBottom: "1px solid var(--border-subtle)" }}>
              <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
                <LayoutTemplate style={{ width: "20px", height: "20px", color: "var(--primary)" }} />
                Create New Template
              </h3>
              <button onClick={() => setShowNewModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}>
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>
            
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>Template Name</label>
              <input 
                type="text" 
                className="input-text" 
                value={formData.name}
                onChange={e => setFormData({...formData, name: e.target.value})}
                placeholder="e.g., Initial Outreach - B2B"
              />
            </div>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>Medium</label>
              <select 
                className="select-dropdown" 
                value={formData.medium}
                onChange={e => setFormData({...formData, medium: e.target.value})}
              >
                <option value="EMAIL">Email</option>
                <option value="WHATSAPP">WhatsApp</option>
                <option value="SMS">SMS</option>
              </select>
            </div>

            {formData.medium === "EMAIL" && (
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>Subject</label>
                <input 
                  type="text" 
                  className="input-text" 
                  value={formData.subject}
                  onChange={e => setFormData({...formData, subject: e.target.value})}
                  placeholder="Subject line with {{ variables }}"
                />
              </div>
            )}

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>Body Template (Jinja2 Syntax)</label>
              <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginBottom: "8px" }}>
                Variables available: <code>{"{{ lead.contact_name }}"}</code>, <code>{"{{ lead.company_name }}"}</code>, <code>{"{{ lead.title }}"}</code>
              </p>
              <textarea 
                className="textarea-field" 
                rows={8}
                value={formData.body_template}
                onChange={e => setFormData({...formData, body_template: e.target.value})}
              />
            </div>

            <div style={{ paddingTop: "14px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "6px" }}>
              <button type="button" onClick={() => setShowNewModal(false)} className="btn-secondary">Cancel</button>
              <button onClick={handleCreate} className="btn-primary">Save Template</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
