import React, { useState, useEffect } from "react";
import { Lead, PipelineStage, Activity, api } from "../services/api";
import { openGmail, openWhatsApp } from "../utils/mailHelper";
// import { EmailComposeModal } from "./EmailComposeModal";
import { format10DigitPhone, getCallUrl } from "../utils/phoneHelper";
import { 
  X, 
  Phone, 
  MessageCircle, 
  Mail, 
  Sparkles, 
  Clock, 
  CheckCircle, 
  History,
  Shield, 
  Send,
  ActivitySquare,
  Download
} from "lucide-react";

interface LeadDetailModalProps {
  lead: Lead;
  stages: PipelineStage[];
  onClose: () => void;
  onRefresh: () => void;
}

export const LeadDetailModal: React.FC<LeadDetailModalProps> = ({
  lead,
  stages,
  onClose,
  onRefresh,
}) => {
  const [currentLead, setCurrentLead] = useState<Lead>(lead);
  const [timeline, setTimeline] = useState<Activity[]>([]);
  const [stageHistories, setStageHistories] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<"timeline" | "ai" | "history" | "templates" | "payments">("timeline");
  const [copiedEmail, setCopiedEmail] = useState<string | null>(null);
  
  const handleCopyEmail = (email: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmail(email);
    setTimeout(() => setCopiedEmail(null), 2000);
  };
  // Activity log state
  const [activityType, setActivityType] = useState("CALL");
  const [activitySubject, setActivitySubject] = useState("");
  const [activityDesc, setActivityDesc] = useState("");
  const [callStatus, setCallStatus] = useState("CONNECTED");
  const [submittingAct, setSubmittingAct] = useState(false);

  // AI states
  const [aiLoading, setAiLoading] = useState(false);
  const [aiScoreData, setAiScoreData] = useState<any>(null);
  const [aiSummaryData, setAiSummaryData] = useState<any>(null);
  const [aiNextAction, setAiNextAction] = useState<any>(null);

  // Templates and Payments states
  const [templates, setTemplates] = useState<any[]>([]);
  const [payments, setPayments] = useState<any[]>([]);
  const [renderedTemplate, setRenderedTemplate] = useState<{ id: string, text: string } | null>(null);
  const [paymentAmount, setPaymentAmount] = useState<number>(0);

  useEffect(() => {
    loadTimelineAndHistory();
    if (activeTab === "templates") loadTemplates();
    if (activeTab === "payments") loadPayments();
  }, [lead.id, activeTab]);

  const loadTimelineAndHistory = async () => {
    try {
      const [tl, sh] = await Promise.all([
        api.getLeadTimeline(lead.id),
        api.getLeadStageHistory(lead.id),
      ]);
      setTimeline(tl);
      setStageHistories(sh);
    } catch (e) {
      console.error(e);
    }
  };

  const loadTemplates = async () => {
    try {
      const data = await api.getTemplates();
      setTemplates(data || []);
    } catch (e) {
      console.error(e);
    }
  };

  const loadPayments = async () => {
    try {
      const data = await api.getLeadPayments(currentLead.id);
      setPayments(data || []);
    } catch (e) {
      console.error(e);
    }
  };

  const handleRenderTemplate = async (templateId: string) => {
    try {
      const res = await api.renderTemplate(templateId, currentLead.id);
      setRenderedTemplate({ id: templateId, text: res.rendered });
    } catch (e) {
      alert("Failed to render template");
    }
  };

  const handleGeneratePayment = async () => {
    if (!paymentAmount || paymentAmount <= 0) return alert("Enter valid amount");
    try {
      await api.generatePaymentLink({ lead_id: currentLead.id, amount: paymentAmount });
      setPaymentAmount(0);
      loadPayments();
    } catch (e) {
      alert("Failed to generate payment");
    }
  };

  const handleSimulatePayment = async (paymentId: string) => {
    try {
      await api.simulatePayment(paymentId);
      loadPayments();
      
      const wonStage = stages.find(s => s.is_won);
      setCurrentLead(prev => ({ 
        ...prev, 
        status: "WON", 
        pipeline_stage_id: wonStage ? wonStage.id : prev.pipeline_stage_id 
      }));

      // Wait for status to be propagated if possible, or just refresh timeline
      onRefresh();
    } catch (e) {
      alert("Simulation failed");
    }
  };

  const handleStageChange = async (newStageId: string) => {
    try {
      const updated = await api.updateLeadStage(currentLead.id, newStageId, "Manual stage change in 360° modal");
      setCurrentLead(updated);
      await loadTimelineAndHistory();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleLogActivity = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!activitySubject) return;
    setSubmittingAct(true);
    try {
      await api.logActivity({
        lead_id: currentLead.id,
        activity_type: activityType,
        subject: activitySubject,
        description: activityDesc,
        status: callStatus,
      });
      setActivitySubject("");
      setActivityDesc("");
      await loadTimelineAndHistory();
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setSubmittingAct(false);
    }
  };

  const handleRunAiScore = async () => {
    setAiLoading(true);
    try {
      const res = await api.scoreLeadAI(currentLead.id);
      setAiScoreData(res);
      setCurrentLead({ ...currentLead, score: res.score });
      onRefresh();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleRunAiSummary = async () => {
    setAiLoading(true);
    try {
      const res = await api.summarizeLeadAI(currentLead.id);
      setAiSummaryData(res);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setAiLoading(false);
    }
  };

  const handleRunAiAction = async () => {
    setAiLoading(true);
    try {
      const res = await api.recommendNextActionAI(currentLead.id);
      setAiNextAction(res);
    } catch (e: any) {
      alert(e.message);
    } finally {
      setAiLoading(false);
    }
  };

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={{
          padding: "20px 24px",
          borderBottom: "1px solid var(--border-subtle)",
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          background: "var(--bg-surface)"
        }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "6px" }}>
              <span className={`badge ${currentLead.priority === "HIGH" ? "badge-hot" : "badge-medium"}`}>
                {currentLead.priority}
              </span>
              <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
                Sourced via {currentLead.source}
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <h2 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                {currentLead.title}
              </h2>
              <span style={{ fontSize: "0.625rem", fontWeight: 700, padding: "2px 6px", borderRadius: "4px", backgroundColor: currentLead.company_name ? "var(--primary-light)" : "var(--amber-light)", color: currentLead.company_name ? "var(--primary-dark)" : "var(--amber-dark)" }}>
                {currentLead.company_name ? "B2B" : "B2C"}
              </span>
            </div>
            {currentLead.company_name && (
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                {currentLead.company_name}
              </p>
            )}
          </div>

          <button
            onClick={onClose}
            style={{
              padding: "6px",
              borderRadius: "8px",
              border: "1px solid var(--border-subtle)",
              background: "transparent",
              color: "var(--text-secondary)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center"
            }}
          >
            <X style={{ width: "20px", height: "20px" }} />
          </button>
        </div>

        {/* Quick Action & Stage Progression Bar */}
        <div style={{
          padding: "14px 24px",
          borderBottom: "1px solid var(--border-subtle)",
          background: "var(--bg-surface-subtle)",
          display: "flex",
          flexWrap: "wrap",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "12px"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)" }}>
              Current Stage:
            </span>
            <select
              value={currentLead.pipeline_stage_id}
              onChange={(e) => handleStageChange(e.target.value)}
              className="select-dropdown"
              style={{ fontWeight: 700, fontSize: "0.75rem", padding: "4px 8px", width: "auto" }}
            >
              {stages.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </div>

          {/* Quick Communication Triggers */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <button
              onClick={async () => {
                if (currentLead.contact_phone && !currentLead.is_phone_masked) {
                  try {
                    const res = await api.dialLead(currentLead.id);
                    if (res.tel_url) {
                      window.location.href = res.tel_url;
                    }
                  } catch (e) {
                    console.warn("Call dialer error", e);
                  }
                }
              }}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "5px 10px" }}
              title={currentLead.is_phone_masked ? "Phone is protected" : `Call (+91 ${format10DigitPhone(currentLead.contact_phone)})`}
            >
              <Phone style={{ width: "13px", height: "13px", color: "var(--emerald)" }} />
              Call
            </button>

            <button
              onClick={async () => {
                try {
                  const res = await api.triggerLeadAction(currentLead.id, "whatsapp");
                  if (res.whatsapp_url) {
                    window.open(res.whatsapp_url, "_blank", "noopener,noreferrer");
                  } else {
                    openWhatsApp(currentLead.contact_phone, `Hello ${currentLead.contact_name || ""}, regarding ${currentLead.title}.`);
                  }
                } catch {
                  openWhatsApp(currentLead.contact_phone, `Hello ${currentLead.contact_name || ""}, regarding ${currentLead.title}.`);
                }
              }}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "5px 10px" }}
              title="Open WhatsApp chat in new tab"
            >
              <MessageCircle style={{ width: "13px", height: "13px", color: "var(--emerald)" }} />
              WhatsApp
            </button>

            <button
              onClick={() => {
                if (currentLead.contact_email) {
                  handleCopyEmail(currentLead.contact_email);
                }
              }}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "5px 10px", color: "#dc2626", borderColor: "#fecaca" }}
              title="Copy email to clipboard"
            >
              <Mail style={{ width: "13px", height: "13px", color: "#dc2626" }} />
              {copiedEmail === currentLead.contact_email ? "Copied!" : "Copy Email"}
            </button>

            <button
              onClick={() => api.downloadLeadVCard(currentLead.id).catch((error: Error) => alert(error.message))}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "5px 10px" }}
              title="Download vCard"
            >
              <Download style={{ width: "13px", height: "13px", color: "var(--primary)" }} />
              vCard
            </button>
          </div>
        </div>

        {/* Scrollable Drawer Body */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px", display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Primary Contact Card */}
          <div className="card" style={{ padding: "16px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px", paddingBottom: "8px", borderBottom: "1px solid var(--border-subtle)" }}>
              <h3 style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Primary Contact Information
              </h3>
              {currentLead.is_phone_masked && (
                <span className="badge badge-masked" style={{ fontSize: "0.625rem" }}>
                  <Shield style={{ width: "11px", height: "11px" }} />
                  Anti-Theft Data Masking Active
                </span>
              )}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.8125rem" }}>
              <div>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Contact Name</span>
                <p style={{ fontWeight: 700, color: "var(--text-primary)", marginTop: "2px" }}>
                  {currentLead.contact_name || "—"}
                </p>
              </div>

              <div>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Phone Number</span>
                <p style={{ fontWeight: 700, color: "var(--text-primary)", marginTop: "2px", display: "flex", alignItems: "center", gap: "6px" }}>
                  {format10DigitPhone(currentLead.contact_phone) || "—"}
                  {currentLead.is_phone_masked && (
                    <span style={{ fontSize: "0.625rem", color: "var(--purple-dark)", fontStyle: "italic" }}>(Protected)</span>
                  )}
                </p>
              </div>

              <div>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Email Address</span>
                <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "2px" }}>
                  <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                    {currentLead.contact_email || "—"}
                  </p>
                  {currentLead.contact_email && (
                    <button
                      onClick={() => handleCopyEmail(currentLead.contact_email!)}
                      title="Copy email to clipboard"
                      style={{
                        background: "var(--bg-surface-subtle)",
                        border: "1px solid var(--border-medium)",
                        borderRadius: "4px",
                        padding: "2px 6px",
                        fontSize: "0.6875rem",
                        color: "#dc2626",
                        cursor: "pointer",
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "3px"
                      }}
                    >
                      <Mail style={{ width: "11px", height: "11px", color: "#dc2626" }} />
                      {copiedEmail === currentLead.contact_email ? "Copied!" : "Copy Email"}
                    </button>
                  )}
                </div>
              </div>

              {currentLead.company_name && (
                <div>
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Deal Value</span>
                  <p style={{ fontWeight: 800, fontFamily: "monospace", color: "var(--emerald-dark)", marginTop: "2px" }}>
                    ₹{Number(currentLead.value || 0).toLocaleString("en-IN")}
                  </p>
                </div>
              )}
              {!currentLead.company_name && (
                <div>
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Individual Value</span>
                  <p style={{ fontWeight: 800, fontFamily: "monospace", color: "var(--emerald-dark)", marginTop: "2px" }}>
                    ₹{Number(currentLead.value || 0).toLocaleString("en-IN")}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Sub Navigation Tabs */}
          <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
            <button
              onClick={() => setActiveTab("timeline")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeTab === "timeline" ? "2px solid var(--primary)" : "2px solid transparent",
                color: activeTab === "timeline" ? "var(--primary)" : "var(--text-secondary)",
                fontWeight: 700,
                fontSize: "0.8125rem",
                padding: "6px 12px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <Clock style={{ width: "14px", height: "14px" }} />
              Timeline
            </button>

            <button
              onClick={() => setActiveTab("templates")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeTab === "templates" ? "2px solid var(--primary)" : "2px solid transparent",
                color: activeTab === "templates" ? "var(--primary)" : "var(--text-secondary)",
                fontWeight: 700,
                fontSize: "0.8125rem",
                padding: "6px 12px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <MessageCircle style={{ width: "14px", height: "14px" }} />
              Templates
            </button>

            <button
              onClick={() => setActiveTab("payments")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeTab === "payments" ? "2px solid var(--primary)" : "2px solid transparent",
                color: activeTab === "payments" ? "var(--primary)" : "var(--text-secondary)",
                fontWeight: 700,
                fontSize: "0.8125rem",
                padding: "6px 12px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <ActivitySquare style={{ width: "14px", height: "14px" }} />
              Payments
            </button>

            <button
              onClick={() => setActiveTab("ai")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeTab === "ai" ? "2px solid var(--primary)" : "2px solid transparent",
                color: activeTab === "ai" ? "var(--primary)" : "var(--text-secondary)",
                fontWeight: 700,
                fontSize: "0.8125rem",
                padding: "6px 12px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <Sparkles style={{ width: "14px", height: "14px", color: "var(--amber)" }} />
              AI Copilot & Radar
            </button>

            <button
              onClick={() => setActiveTab("history")}
              style={{
                background: "transparent",
                border: "none",
                borderBottom: activeTab === "history" ? "2px solid var(--primary)" : "2px solid transparent",
                color: activeTab === "history" ? "var(--primary)" : "var(--text-secondary)",
                fontWeight: 700,
                fontSize: "0.8125rem",
                padding: "6px 12px",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "6px"
              }}
            >
              <History style={{ width: "14px", height: "14px" }} />
              Stage Audit
            </button>
          </div>

          {/* Tab 1: Timeline & Log Activity */}
          {activeTab === "timeline" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              {/* Log Activity Box */}
              <form onSubmit={handleLogActivity} className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>Quick Log Activity</span>
                  <div style={{ display: "flex", gap: "4px" }}>
                    {["CALL", "WHATSAPP", "EMAIL", "NOTE"].map((t) => (
                      <button
                        key={t}
                        type="button"
                        onClick={() => setActivityType(t)}
                        style={{
                          fontSize: "0.6875rem",
                          fontWeight: 700,
                          padding: "3px 8px",
                          borderRadius: "6px",
                          border: "none",
                          cursor: "pointer",
                          background: activityType === t ? "var(--primary)" : "var(--bg-surface-subtle)",
                          color: activityType === t ? "#ffffff" : "var(--text-secondary)",
                          transition: "all 0.15s ease"
                        }}
                      >
                        {t}
                      </button>
                    ))}
                  </div>
                </div>

                <input
                  type="text"
                  value={activitySubject}
                  onChange={(e) => setActivitySubject(e.target.value)}
                  placeholder="Subject / key discussion points..."
                  className="input-text"
                  required
                />

                <textarea
                  value={activityDesc}
                  onChange={(e) => setActivityDesc(e.target.value)}
                  placeholder="Additional remarks or client feedback..."
                  rows={2}
                  className="textarea-field"
                />

                <div style={{ display: "flex", justifyContent: "flex-end" }}>
                  <button type="submit" disabled={submittingAct} className="btn-primary" style={{ padding: "6px 14px" }}>
                    <Send style={{ width: "13px", height: "13px" }} />
                    {submittingAct ? "Saving..." : "Log Interaction"}
                  </button>
                </div>
              </form>

              {/* Chronological Timeline List */}
              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                {timeline.map((act) => (
                  <div
                    key={act.id}
                    style={{
                      padding: "12px 16px",
                      borderRadius: "8px",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                      borderLeft: "3px solid var(--primary)",
                      boxShadow: "var(--shadow-xs)",
                      fontSize: "0.8125rem"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "4px" }}>
                      <span style={{ fontWeight: 700, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                        {act.activity_type === "CALL" && <Phone style={{ width: "13px", height: "13px", color: "var(--emerald)" }} />}
                        {act.activity_type === "WHATSAPP" && <MessageCircle style={{ width: "13px", height: "13px", color: "var(--emerald)" }} />}
                        {act.activity_type === "EMAIL" && <Mail style={{ width: "13px", height: "13px", color: "var(--primary)" }} />}
                        {act.subject || act.activity_type}
                      </span>
                      <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                        {new Date(act.occurred_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </span>
                    </div>
                    {act.description && <p style={{ color: "var(--text-secondary)", marginTop: "4px", fontSize: "0.75rem" }}>{act.description}</p>}
                    <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px" }}>Logged by {act.user_name || "System"}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Tab 2: AI Copilot */}
          {activeTab === "ai" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "8px" }}>
                <button
                  onClick={handleRunAiScore}
                  disabled={aiLoading}
                  className="btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "8px 6px" }}
                >
                  <Sparkles style={{ width: "14px", height: "14px", color: "var(--amber)" }} />
                  Evaluate Score
                </button>
                <button
                  onClick={handleRunAiSummary}
                  disabled={aiLoading}
                  className="btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "8px 6px" }}
                >
                  <Sparkles style={{ width: "14px", height: "14px", color: "var(--primary)" }} />
                  Account Brief
                </button>
                <button
                  onClick={handleRunAiAction}
                  disabled={aiLoading}
                  className="btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "8px 6px" }}
                >
                  <Sparkles style={{ width: "14px", height: "14px", color: "var(--cyan)" }} />
                  Next Best Action
                </button>
              </div>

              {aiLoading && (
                <div style={{ textAlign: "center", padding: "24px 0", fontSize: "0.8125rem", color: "var(--primary)", fontWeight: 600 }}>
                  JARVIS AI analyzing account signals and engagement patterns...
                </div>
              )}

              {aiScoreData && (
                <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px", borderLeft: "4px solid var(--amber)" }}>
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--amber-dark)" }}>Score Assessment</span>
                    <span className="badge badge-hot">{aiScoreData.qualification_tier} TIER</span>
                  </div>
                  <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", fontFamily: "monospace" }}>
                    {aiScoreData.score} <span style={{ fontSize: "1rem", color: "var(--text-muted)" }}>/ 100</span>
                  </div>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    Estimated Conversion Probability: <strong>{(aiScoreData.conversion_probability * 100).toFixed(0)}%</strong>
                  </p>
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", paddingTop: "8px" }}>
                    {aiScoreData.key_signals.map((sig: string, idx: number) => (
                      <div key={idx} style={{ fontSize: "0.75rem", color: "var(--text-secondary)", display: "flex", alignItems: "center", gap: "6px" }}>
                        <CheckCircle style={{ width: "13px", height: "13px", color: "var(--emerald)", flexShrink: 0 }} />
                        <span>{sig}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {aiSummaryData && (
                <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px", borderLeft: "4px solid var(--primary)" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--primary)", textTransform: "uppercase" }}>
                    Executive Account Brief
                  </span>
                  <h4 style={{ fontSize: "0.9375rem", fontWeight: 800, color: "var(--text-primary)" }}>{aiSummaryData.headline}</h4>
                  <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: "1.5" }}>{aiSummaryData.business_context}</p>
                  <div style={{ paddingTop: "8px", borderTop: "1px solid var(--border-subtle)" }}>
                    <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>Recommended Next Step:</span>
                    <p style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--primary)", marginTop: "2px" }}>{aiSummaryData.suggested_next_step}</p>
                  </div>
                </div>
              )}

              {aiNextAction && (
                <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px", borderLeft: "4px solid var(--cyan)" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--cyan-dark)", textTransform: "uppercase" }}>
                    Autonomous Next Best Action
                  </span>
                  <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>{aiNextAction.recommended_action}</p>
                  <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>{aiNextAction.reason}</p>
                  {aiNextAction.suggested_message && (
                    <div style={{ padding: "10px", borderRadius: "6px", background: "var(--bg-surface-subtle)", border: "1px solid var(--border-subtle)", fontSize: "0.75rem", color: "var(--text-primary)", fontFamily: "monospace" }}>
                      "{aiNextAction.suggested_message}"
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Stage Audit History */}
          {activeTab === "history" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {stageHistories.map((hist) => (
                <div
                  key={hist.id}
                  style={{
                    padding: "12px",
                    borderRadius: "8px",
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    fontSize: "0.8125rem"
                  }}
                >
                  <div>
                    <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>
                      {hist.from_stage_name ? `${hist.from_stage_name} → ${hist.to_stage_name}` : `Created in ${hist.to_stage_name}`}
                    </p>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>{hist.reason || "Stage transition"}</p>
                    <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>By {hist.changed_by_name || "System"}</p>
                  </div>
                  <div style={{ textAlign: "right" }}>
                    <span style={{ fontSize: "0.75rem", fontFamily: "monospace", color: "var(--text-muted)" }}>
                      {new Date(hist.created_at).toLocaleDateString()}
                    </span>
                    {hist.duration_seconds > 0 && (
                      <p style={{ fontSize: "0.6875rem", color: "var(--primary)", fontWeight: 600 }}>
                        Stayed {Math.round(hist.duration_seconds / 60)} min
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Tab 4: Templates */}
          {activeTab === "templates" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              {templates.length === 0 ? (
                <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No templates available.</p>
              ) : (
                templates.map(t => (
                  <div key={t.id} className="card" style={{ padding: "12px", display: "flex", flexDirection: "column", gap: "8px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>{t.name}</span>
                      <span className="badge badge-medium">{t.medium}</span>
                    </div>
                    {renderedTemplate?.id === t.id ? (
                      <div style={{ background: "var(--bg-surface-subtle)", padding: "12px", borderRadius: "6px", fontSize: "0.8125rem", whiteSpace: "pre-wrap" }}>
                        {renderedTemplate?.text || ""}
                      </div>
                    ) : (
                      <button onClick={() => handleRenderTemplate(t.id)} className="btn-secondary" style={{ width: "fit-content", fontSize: "0.75rem", padding: "4px 8px" }}>
                        Preview Rendered Message
                      </button>
                    )}
                    {renderedTemplate?.id === t.id && (
                      <div style={{ display: "flex", gap: "8px", marginTop: "4px" }}>
                        {t.medium === "EMAIL" && (
                          <a href={`mailto:${currentLead.contact_email}?subject=${encodeURIComponent(t.subject || '')}&body=${encodeURIComponent(renderedTemplate?.text || '')}`} className="btn-primary" style={{ fontSize: "0.75rem", padding: "4px 12px" }}>
                            Open in Mail
                          </a>
                        )}
                        {t.medium === "WHATSAPP" && (
                          <a href={`https://wa.me/${currentLead.contact_phone}?text=${encodeURIComponent(renderedTemplate?.text || '')}`} target="_blank" rel="noreferrer" className="btn-primary" style={{ fontSize: "0.75rem", padding: "4px 12px", background: "#25D366" }}>
                            Open in WhatsApp
                          </a>
                        )}
                        <button onClick={() => navigator.clipboard.writeText(renderedTemplate?.text || "")} className="btn-secondary" style={{ fontSize: "0.75rem", padding: "4px 12px" }}>
                          Copy Text
                        </button>
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Tab 5: Payments & Conversions */}
          {activeTab === "payments" && (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", gap: "8px" }}>
                <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>Generate Payment Link</span>
                <div style={{ display: "flex", gap: "8px" }}>
                  <input
                    type="number"
                    className="form-input"
                    placeholder="Amount (INR)"
                    value={paymentAmount || ""}
                    onChange={e => setPaymentAmount(parseFloat(e.target.value))}
                    style={{ flex: 1 }}
                  />
                  <button onClick={handleGeneratePayment} className="btn-primary">Generate</button>
                </div>
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Payment Links</span>
                {payments.length === 0 ? (
                  <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>No payments generated.</p>
                ) : (
                  payments.map(p => (
                    <div key={p.id} className="card" style={{ padding: "12px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: "0.875rem" }}>₹{Number(p.amount).toLocaleString("en-IN")}</div>
                        <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{p.reference_id}</div>
                      </div>
                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span className={`badge ${p.status === "PAID" ? "badge-hot" : "badge-medium"}`}>{p.status}</span>
                        {p.status === "PENDING" && (
                          <button onClick={() => handleSimulatePayment(p.id)} className="btn-secondary" style={{ fontSize: "0.75rem", padding: "4px 8px" }}>
                            Simulate Payment
                          </button>
                        )}
                        {p.status === "PAID" && (
                          <CheckCircle style={{ width: 16, height: 16, color: "var(--emerald)" }} />
                        )}
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
