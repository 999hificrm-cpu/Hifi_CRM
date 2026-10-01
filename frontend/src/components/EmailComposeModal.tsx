import React, { useState, useEffect } from "react";
import { Lead, api } from "../services/api";
import { openMailto } from "../utils/mailHelper";
import {
  X,
  Mail,
  Send,
  AlertTriangle,
  User,
  CheckCircle2,
  ExternalLink,
  Laptop,
  ShieldCheck,
  ChevronDown,
  ChevronRight,
  Link2,
  Unlink
} from "lucide-react";

interface SendAsIdentity {
  email: string;
  display_name: string;
  is_primary: boolean;
  is_default: boolean;
  verification_status: string;
}

interface EmailComposeModalProps {
  isOpen: boolean;
  onClose: () => void;
  lead: Lead | null;
  onSent?: () => void;
}

export const EmailComposeModal: React.FC<EmailComposeModalProps> = ({
  isOpen,
  onClose,
  lead,
  onSent,
}) => {
  // Sender configuration
  const [senderName, setSenderName] = useState("Apex Admin");
  const [senderEmail, setSenderEmail] = useState("admin@apex.com");
  const [orgName, setOrgName] = useState("Jarvis CRM");

  // Gmail connection state
  const [gmailConnected, setGmailConnected] = useState(false);
  const [gmailConfigured, setGmailConfigured] = useState(false);
  const [gmailAccount, setGmailAccount] = useState<string | null>(null);
  const [sendAsIdentities, setSendAsIdentities] = useState<SendAsIdentity[]>([]);
  const [gmailLoading, setGmailLoading] = useState(true);
  const [gmailError, setGmailError] = useState<string | null>(null);

  // Recipient info for "TO" stage
  const [recipientEmail, setRecipientEmail] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [logging, setLogging] = useState(false);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Check Gmail connection status on mount
  const checkGmailStatus = async () => {
    setGmailLoading(true);
    setGmailError(null);
    try {
      const status = await api.gmailStatus();
      setGmailConfigured(status.configured);
      setGmailConnected(status.connected);
      setGmailAccount(status.google_account || null);
      setSendAsIdentities(status.send_as_identities || []);

      // If connected and has Send-As identities, default to first verified one
      if (status.connected && status.send_as_identities && status.send_as_identities.length > 0) {
        const defaultIdentity = status.send_as_identities.find(i => i.is_default) || status.send_as_identities[0];
        const persistedSender = localStorage.getItem("jarvis_configured_sender_email");
        // Only auto-set if user hasn't explicitly chosen one, or chosen one is valid
        if (persistedSender) {
          const isValid = status.send_as_identities.some(i => i.email.toLowerCase() === persistedSender.toLowerCase());
          if (isValid) {
            setSenderEmail(persistedSender);
            const persistedName = localStorage.getItem("jarvis_configured_sender_name");
            if (persistedName) setSenderName(persistedName);
          } else {
            setSenderEmail(defaultIdentity.email);
            if (defaultIdentity.display_name) setSenderName(defaultIdentity.display_name);
          }
        } else {
          setSenderEmail(defaultIdentity.email);
          if (defaultIdentity.display_name) setSenderName(defaultIdentity.display_name);
        }
      }
    } catch (err: any) {
      setGmailError(err.message || "Failed to check Gmail status");
    } finally {
      setGmailLoading(false);
    }
  };

  useEffect(() => {
    if (!isOpen || !lead) return;

    try {
      const storedUser = localStorage.getItem("jarvis_user");
      let defaultName = "Apex Admin";
      let defaultEmail = "admin@apex.com";

      if (storedUser) {
        const u = JSON.parse(storedUser);
        if (u.full_name) defaultName = u.full_name;
        if (u.email) defaultEmail = u.email;
      }

      const storedOrg = localStorage.getItem("jarvis_org");
      if (storedOrg) {
        const o = JSON.parse(storedOrg);
        if (o.name) setOrgName(o.name);
      }

      const persistedSenderName = localStorage.getItem("jarvis_configured_sender_name");
      const persistedSenderEmail = localStorage.getItem("jarvis_configured_sender_email");
      setSenderName(persistedSenderName || defaultName);
      setSenderEmail(persistedSenderEmail || defaultEmail);
    } catch {}

    const contactGreeting = lead.contact_name ? `Hello ${lead.contact_name},` : "Hello there,";
    setRecipientEmail(lead.contact_email || "");
    setSubject(`Regarding ${lead.title} - ${lead.company_name || "Opportunity"}`);
    setBody(
      `${contactGreeting}\n\nI am reaching out regarding ${lead.title}.\nWe would love to discuss how we can partner with ${lead.company_name || "your team"}.\n\nBest regards,\n${senderName || "Apex Admin"}\n${orgName || "Jarvis CRM"}`
    );
    setSuccessMessage(null);
    setGmailError(null);

    // Check Gmail status
    checkGmailStatus();

    // Listen for OAuth callback completion
    const handleMessage = (event: MessageEvent) => {
      if (event.data === "gmail_connected") {
        checkGmailStatus();
      }
    };
    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, [lead, isOpen]);

  // Hooks must be called on every render.  Render nothing only after all
  // state/effect hooks have been declared so opening or closing the modal
  // cannot change React's hook order.
  if (!isOpen || !lead) return null;

  const handleSenderChange = (email: string) => {
    setSenderEmail(email);
    try { localStorage.setItem("jarvis_configured_sender_email", email.trim()); } catch {}
    // Update display name from Send-As identity if available
    const identity = sendAsIdentities.find(i => i.email.toLowerCase() === email.toLowerCase());
    if (identity && identity.display_name) {
      setSenderName(identity.display_name);
      try { localStorage.setItem("jarvis_configured_sender_name", identity.display_name); } catch {}
    }
  };

  const handleSenderNameChange = (name: string) => {
    setSenderName(name);
    try { localStorage.setItem("jarvis_configured_sender_name", name.trim()); } catch {}
  };

  const isSelfSend =
    senderEmail.trim().toLowerCase() !== "" &&
    recipientEmail.trim().toLowerCase() !== "" &&
    senderEmail.trim().toLowerCase() === recipientEmail.trim().toLowerCase();

  const handleApplyTemplate = (type: "intro" | "followup" | "meeting") => {
    const greeting = lead.contact_name ? `Hello ${lead.contact_name},` : "Hello there,";
    if (type === "intro") {
      setSubject(`Introduction: Solution for ${lead.company_name || lead.title}`);
      setBody(
        `${greeting}\n\nI hope this email finds you well. I am reaching out to introduce our comprehensive solutions tailored for ${lead.company_name || "your organization"}.\n\nWould you be open to a brief 10-minute introductory conversation this week?\n\nBest regards,\n${senderName}\n${orgName}`
      );
    } else if (type === "followup") {
      setSubject(`Follow-up: Regarding ${lead.title}`);
      setBody(
        `${greeting}\n\nI wanted to follow up on our previous communication regarding ${lead.title}. We are eager to see if you have any questions or require additional details.\n\nLooking forward to hearing your thoughts.\n\nBest regards,\n${senderName}\n${orgName}`
      );
    } else if (type === "meeting") {
      setSubject(`Meeting Request: Scheduling demo for ${lead.company_name || lead.title}`);
      setBody(
        `${greeting}\n\nCould we schedule a convenient 20-minute product demonstration for ${lead.company_name || "your team"} next Tuesday or Wednesday?\n\nPlease let me know your availability.\n\nBest regards,\n${senderName}\n${orgName}`
      );
    }
  };

  const logActivityInCrm = async (channel: string) => {
    try {
      await api.logActivity({
        lead_id: lead.id,
        activity_type: "EMAIL",
        subject: subject,
        description: `Dispatched via ${channel}\n\nFROM: ${senderName} <${senderEmail}>\nTO: ${recipientEmail}\n\n${body}`,
        direction: "OUTBOUND",
        status: "COMPLETED",
        duration_seconds: 0,
        metadata_json: {
          channel,
          from_email: senderEmail,
          to_email: recipientEmail,
        },
      });
      if (onSent) onSent();
    } catch (err) {
      console.warn("Could not log email activity automatically:", err);
    }
  };

  const handleConnectGmail = async () => {
    try {
      const res = await api.gmailAuthorize();
      if (res.authorization_url) {
        window.open(res.authorization_url, "gmail_oauth", "width=600,height=700");
      }
    } catch (err: any) {
      setGmailError(err.message || "Failed to start Gmail authorization");
    }
  };

  const handleSendViaGmail = async () => {
    if (!recipientEmail.trim()) {
      alert("Please provide a recipient email address.");
      return;
    }
    if (!gmailConnected) {
      alert("Gmail is not connected. Please connect your Gmail account first.");
      return;
    }

    // Validate sender is a verified Send-As identity
    const isValidSender = sendAsIdentities.some(
      i => i.email.toLowerCase() === senderEmail.trim().toLowerCase()
    );
    if (!isValidSender) {
      setGmailError(
        `"${senderEmail}" is not a verified Send-As identity on your connected Gmail account (${gmailAccount}). ` +
        `Available verified senders: ${sendAsIdentities.map(i => i.email).join(", ")}. ` +
        `Add and verify this address in Gmail Settings → Accounts → Send mail as.`
      );
      return;
    }

    setLogging(true);
    setGmailError(null);
    try {
      const res = await api.gmailSend({
        to_email: recipientEmail.trim(),
        from_email: senderEmail.trim(),
        from_name: senderName.trim(),
        subject: subject,
        body: body,
        lead_id: lead.id,
      });
      setSuccessMessage(res.message || `Email sent via Gmail API from ${senderName} <${senderEmail}> to ${recipientEmail}!`);
      if (onSent) onSent();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      setGmailError(err.message || "Failed to send email via Gmail API.");
    } finally {
      setLogging(false);
    }
  };

  const handleOpenMailto = async () => {
    if (!recipientEmail.trim()) {
      alert("Please provide a recipient email address.");
      return;
    }
    setLogging(true);
    await logActivityInCrm("Default Mail Client");
    setLogging(false);
    openMailto(recipientEmail, subject, body);
    setSuccessMessage("Opened in your mail app and logged in CRM Timeline!");
    setTimeout(() => {
      onClose();
    }, 1200);
  };

  const handleDirectLog = async () => {
    if (!recipientEmail.trim()) {
      alert("Please provide a recipient email address.");
      return;
    }
    setLogging(true);
    await logActivityInCrm("Direct CRM Dispatch");
    setLogging(false);
    setSuccessMessage("Email communication recorded in CRM Timeline!");
    setTimeout(() => {
      onClose();
    }, 1000);
  };

  const handleSendFromAdmin = async () => {
    if (!recipientEmail.trim()) {
      alert("Please provide a recipient email address.");
      return;
    }
    setLogging(true);
    try {
      const res = await api.sendLeadEmail(lead.id, {
        subject: subject,
        body: body,
        to_email: recipientEmail.trim(),
      });
      setSuccessMessage(res.message || `Email sent successfully to ${recipientEmail} from ${senderName} <${senderEmail || "admin@apex.com"}>!`);
      if (onSent) onSent();
      setTimeout(() => {
        onClose();
      }, 1500);
    } catch (err: any) {
      alert(err.message || "Failed to dispatch email from Admin.");
    } finally {
      setLogging(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.65)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 9999,
        padding: "16px",
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          background: "var(--bg-surface)",
          border: "1px solid var(--border-medium)",
          borderRadius: "14px",
          width: "100%",
          maxWidth: "680px",
          maxHeight: "90vh",
          display: "flex",
          flexDirection: "column",
          boxShadow: "0 25px 50px -12px rgba(0, 0, 0, 0.25)",
          overflow: "hidden",
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
            background: "linear-gradient(180deg, var(--bg-surface-subtle) 0%, var(--bg-surface) 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Mail style={{ width: "18px", height: "18px", color: "#dc2626" }} />
            </div>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Compose & Dispatch Email
              </h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Target Lead: <strong>{lead.title}</strong> ({lead.company_name || "No Account"})
              </p>
            </div>
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
            }}
          >
            <X style={{ width: "18px", height: "18px" }} />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <div style={{ padding: "20px 24px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Status Message */}
          {successMessage && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "8px",
                background: "#ecfdf5",
                border: "1px solid #a7f3d0",
                color: "#065f46",
                fontSize: "0.8125rem",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <CheckCircle2 style={{ width: "16px", height: "16px", color: "#10b981" }} />
              {successMessage}
            </div>
          )}

          {/* Warning: Self-send check */}
          {isSelfSend && (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: "8px",
                background: "#fffbeb",
                border: "1px solid #fde68a",
                color: "#92400e",
                fontSize: "0.75rem",
                lineHeight: "1.4",
                display: "flex",
                alignItems: "flex-start",
                gap: "8px",
              }}
            >
              <AlertTriangle style={{ width: "16px", height: "16px", color: "#d97706", flexShrink: 0, marginTop: "2px" }} />
              <div>
                <strong>Notice: Sender and Recipient addresses are identical ({recipientEmail}).</strong>
                <p style={{ marginTop: "2px" }}>
                  Sending will deliver this email directly to your own inbox. If testing communication with a lead, please change the <strong>"To"</strong> field below to the actual client email.
                </p>
              </div>
            </div>
          )}

          {/* STAGE 1: FROM (Sender Details) */}
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "8px",
              background: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <label style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em", display: "flex", alignItems: "center", gap: "6px" }}>
                <ShieldCheck style={{ width: "13px", height: "13px", color: "var(--primary)" }} />
                1. From (Authorized Sender / Send-As Stage)
              </label>
              
              {/* Gmail Connection Status */}
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {gmailLoading ? (
                  <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Checking connection...</span>
                ) : gmailConnected ? (
                  <span style={{ fontSize: "0.6875rem", color: "#10b981", display: "flex", alignItems: "center", gap: "4px", fontWeight: 600 }}>
                    <Link2 style={{ width: "11px", height: "11px" }} /> Connected: {gmailAccount}
                  </span>
                ) : gmailConfigured ? (
                  <button
                    type="button"
                    onClick={handleConnectGmail}
                    style={{
                      fontSize: "0.6875rem",
                      padding: "2px 8px",
                      borderRadius: "4px",
                      background: "#fef2f2",
                      color: "#dc2626",
                      border: "1px solid #fecaca",
                      cursor: "pointer",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      fontWeight: 600
                    }}
                  >
                    <Unlink style={{ width: "11px", height: "11px" }} /> Connect Gmail
                  </button>
                ) : (
                  <span style={{ fontSize: "0.6875rem", color: "#f59e0b", display: "flex", alignItems: "center", gap: "4px" }}>
                    <AlertTriangle style={{ width: "11px", height: "11px" }} /> Gmail not configured by Admin
                  </span>
                )}
              </div>
            </div>

            {/* Error Message */}
            {gmailError && (
              <div style={{ marginBottom: "12px", padding: "8px 10px", borderRadius: "6px", background: "#fef2f2", border: "1px solid #fecaca", color: "#991b1b", fontSize: "0.75rem" }}>
                {gmailError}
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
              <div>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>Sender Name</span>
                <input
                  type="text"
                  value={senderName}
                  onChange={(e) => handleSenderNameChange(e.target.value)}
                  className="input-field"
                  style={{ fontSize: "0.8125rem", padding: "6px 10px", marginTop: "2px" }}
                  placeholder="Your Full Name"
                />
              </div>
              <div>
                <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>
                  Sender Email Address (Send-As / From)
                </span>
                
                {/* Send-As Dropdown if connected, otherwise normal input */}
                {gmailConnected && sendAsIdentities.length > 0 ? (
                  <select
                    value={senderEmail}
                    onChange={(e) => handleSenderChange(e.target.value)}
                    className="input-field"
                    style={{ fontSize: "0.8125rem", padding: "6px 10px", marginTop: "2px", width: "100%", appearance: "auto" }}
                  >
                    {sendAsIdentities.map(identity => (
                      <option key={identity.email} value={identity.email}>
                        {identity.email} {identity.is_primary ? "(Primary)" : ""}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="email"
                    value={senderEmail}
                    onChange={(e) => handleSenderChange(e.target.value)}
                    className="input-field"
                    style={{ fontSize: "0.8125rem", padding: "6px 10px", marginTop: "2px" }}
                    placeholder="e.g. admin@apex.com"
                  />
                )}
              </div>
            </div>

            {/* Explanatory note */}
            <div style={{ marginTop: "10px", paddingTop: "8px", borderTop: "1px dashed var(--border-subtle)", fontSize: "0.6875rem" }}>
              <span style={{ color: "var(--text-muted)", display: "inline-flex", alignItems: "center", gap: "4px" }}>
                ℹ️ The "From" address must be a verified Send-As alias or primary account when sending via Gmail API.
              </span>
            </div>
          </div>

          {/* STAGE 2: TO (Recipient Details) */}
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "8px",
              background: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
              <label style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                2. To (Recipient Stage)
              </label>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                Recipient Lead or Organization Contact
              </span>
            </div>
            <div>
              <input
                type="email"
                value={recipientEmail}
                onChange={(e) => setRecipientEmail(e.target.value)}
                className="input-field"
                style={{ fontSize: "0.8125rem", padding: "6px 10px" }}
                placeholder="recipient@domain.com"
                required
              />
            </div>
          </div>

          {/* STAGE 3: SUBJECT & TEMPLATES */}
          <div>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
              <label style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>
                Subject
              </label>
              <div style={{ display: "flex", gap: "6px" }}>
                <button
                  type="button"
                  onClick={() => handleApplyTemplate("intro")}
                  style={{
                    fontSize: "0.625rem",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle)",
                    background: "transparent",
                    color: "var(--primary)",
                    cursor: "pointer",
                  }}
                >
                  + Intro
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyTemplate("followup")}
                  style={{
                    fontSize: "0.625rem",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle)",
                    background: "transparent",
                    color: "var(--primary)",
                    cursor: "pointer",
                  }}
                >
                  + Follow-up
                </button>
                <button
                  type="button"
                  onClick={() => handleApplyTemplate("meeting")}
                  style={{
                    fontSize: "0.625rem",
                    padding: "2px 6px",
                    borderRadius: "4px",
                    border: "1px solid var(--border-subtle)",
                    background: "transparent",
                    color: "var(--primary)",
                    cursor: "pointer",
                  }}
                >
                  + Demo Request
                </button>
              </div>
            </div>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="input-field"
              style={{ fontSize: "0.8125rem", padding: "6px 10px" }}
              placeholder="Email subject..."
            />
          </div>

          {/* STAGE 4: MESSAGE BODY */}
          <div>
            <label style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", display: "block", marginBottom: "6px" }}>
              Message Content
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              className="textarea-field"
              rows={6}
              style={{ fontSize: "0.8125rem", lineHeight: "1.5", resize: "vertical" }}
              placeholder="Write your email draft here..."
            />
          </div>
        </div>

        {/* Dispatch Action Footer */}
        <div
          style={{
            padding: "16px 24px",
            borderTop: "1px solid var(--border-subtle)",
            background: "var(--bg-surface-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "10px",
          }}
        >
          <button
            type="button"
            onClick={onClose}
            style={{
              padding: "8px 14px",
              borderRadius: "8px",
              border: "1px solid var(--border-medium)",
              background: "transparent",
              color: "var(--text-secondary)",
              fontSize: "0.8125rem",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            Cancel
          </button>

          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
            {/* Option A: Default Mail Client (Outlook/Thunderbird) */}
            <button
              type="button"
              disabled={logging}
              onClick={handleOpenMailto}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 12px",
                borderRadius: "8px",
                border: "1px solid var(--border-medium)",
                background: "var(--bg-surface)",
                color: "var(--text-primary)",
                fontSize: "0.75rem",
                fontWeight: 700,
                cursor: "pointer",
              }}
              title="Open in your default desktop mail client (Outlook / Windows Mail / Mac Mail)"
            >
              <Laptop style={{ width: "13px", height: "13px", color: "var(--primary)" }} />
              Desktop Mail
            </button>

            {/* Option B: Google Workspace / Gmail API */}
            <button
              type="button"
              disabled={logging || (!gmailConnected && gmailConfigured)}
              onClick={handleSendViaGmail}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 12px",
                borderRadius: "8px",
                border: "1px solid #fecaca",
                background: "#fef2f2",
                color: "#dc2626",
                fontSize: "0.75rem",
                fontWeight: 700,
                cursor: (logging || (!gmailConnected && gmailConfigured)) ? "not-allowed" : "pointer",
                opacity: (logging || (!gmailConnected && gmailConfigured)) ? 0.6 : 1
              }}
              title="Send email securely via Gmail API using your Send-As identity"
            >
              <Mail style={{ width: "13px", height: "13px" }} />
              {logging ? "Sending..." : "Send via Gmail"}
            </button>

            {/* Primary Option: Send Directly from Admin with distinct sender */}
            <button
              type="button"
              id="btn-send-from-admin"
              disabled={logging}
              onClick={handleSendFromAdmin}
              className="btn-primary"
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 18px",
                borderRadius: "8px",
                fontSize: "0.8125rem",
                fontWeight: 800,
                cursor: "pointer",
              }}
              title="Send email from Admin with From and To as distinct addresses"
            >
              <Send style={{ width: "13px", height: "13px" }} />
              {logging ? "Sending..." : "Send from Admin"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
