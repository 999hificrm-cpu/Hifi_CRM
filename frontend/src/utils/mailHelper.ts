/**
 * Utilities for Gmail and communication actions across all Jarvis CRM dashboards.
 * Direct Gmail compose URL standard:
 * https://mail.google.com/mail/?view=cm&fs=1&to=...&su=...&body=...
 */

export const getGmailUrl = (
  to?: string | null,
  subject?: string,
  body?: string,
  fromEmail?: string | null,
  authAccount?: string | null
): string => {
  // 1. Resolve configured authorized sender identity
  let configuredSender = fromEmail;
  if (!configuredSender) {
    try {
      const persistedSender =
        localStorage.getItem("jarvis_configured_sender_email") ||
        localStorage.getItem("jarvis_sender_email");
      if (persistedSender && persistedSender.trim()) {
        configuredSender = persistedSender.trim();
      } else {
        const storedOrg = localStorage.getItem("jarvis_org");
        if (storedOrg) {
          const org = JSON.parse(storedOrg);
          if (org?.authorized_sender_email) {
            configuredSender = org.authorized_sender_email;
          }
        }
        if (!configuredSender) {
          const storedUser = localStorage.getItem("jarvis_user");
          if (storedUser) {
            const u = JSON.parse(storedUser);
            configuredSender = u?.email;
          }
        }
      }
    } catch {}
  }

  // 2. Resolve Google account session identifier
  // If user has specified a host Google account email (e.g. for a Send-As alias), use it.
  // Otherwise use the configured sender identity.
  let sessionAccount = authAccount;
  if (!sessionAccount) {
    try {
      const googleAuth = localStorage.getItem("jarvis_google_auth_email");
      if (googleAuth && googleAuth.trim()) {
        sessionAccount = googleAuth.trim();
      } else if (configuredSender && configuredSender.trim()) {
        sessionAccount = configuredSender.trim();
      } else {
        const storedUser = localStorage.getItem("jarvis_user");
        if (storedUser) {
          const u = JSON.parse(storedUser);
          sessionAccount = u?.email;
        }
      }
    } catch {}
  }

  const cleanTo = (to || "").trim();
  const cleanSession = (sessionAccount || "").trim();

  const params = new URLSearchParams();
  params.set("view", "cm");
  params.set("fs", "1");
  params.set("tf", "cm");

  // "To" must strictly be the recipient lead's or company's email
  if (cleanTo && !cleanTo.includes("*")) {
    params.set("to", cleanTo);
  }

  // Set authuser for Google multi-account selection
  if (cleanSession) {
    params.set("authuser", cleanSession);
  }

  if (subject) {
    params.set("su", subject.trim());
  }
  if (body) {
    params.set("body", body.trim());
  }

  // Direct session URL path ensures switching to the authorized Google session
  const basePath = cleanSession
    ? `https://mail.google.com/mail/u/${encodeURIComponent(cleanSession)}/`
    : `https://mail.google.com/mail/`;

  return `${basePath}?${params.toString()}`;
};

export const getMailtoUrl = (
  to?: string | null,
  subject?: string,
  body?: string
): string => {
  const cleanTo = (to || "").trim();
  const params = new URLSearchParams();
  if (subject) params.set("subject", subject.trim());
  if (body) params.set("body", body.trim());
  const queryString = params.toString();
  return `mailto:${cleanTo}${queryString ? "?" + queryString : ""}`;
};

export const openMailto = (
  to?: string | null,
  subject?: string,
  body?: string
): void => {
  const url = getMailtoUrl(to, subject, body);
  window.location.href = url;
};

export const openGmail = (
  to?: string | null,
  subject?: string,
  body?: string,
  fromEmail?: string | null,
  authAccount?: string | null
): Window | null => {
  const url = getGmailUrl(to, subject, body, fromEmail, authAccount);
  return window.open(url, "_blank", "noopener,noreferrer");
};

import { getWhatsAppDigits } from "./phoneHelper";

export const getWhatsAppUrl = (
  phone?: string | null,
  text?: string
): string => {
  if (!phone) return "https://web.whatsapp.com";
  const params = new URLSearchParams();
  if (!phone.includes("*")) {
    const waDigits = getWhatsAppDigits(phone);
    if (waDigits) {
      params.set("phone", waDigits);
    }
  }
  if (text) {
    params.set("text", text);
  }
  return `https://api.whatsapp.com/send?${params.toString()}`;
};

export const openWhatsApp = (
  phone?: string | null,
  text?: string
): Window | null => {
  const url = getWhatsAppUrl(phone, text);
  return window.open(url, "_blank", "noopener,noreferrer");
};
