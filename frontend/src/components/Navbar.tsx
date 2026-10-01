import React, { useState, useEffect, useRef } from "react";
import { User } from "../services/api";
import { 
  Building2, Users, PhoneCall, Sparkles, LogOut, Kanban, Globe2, 
  UploadCloud, ActivitySquare, Lock, Menu, X, ShieldCheck, 
  UserCheck, BrainCircuit, Shield, Key, Briefcase, ChevronDown
} from "lucide-react";
import { ActionCenterDropdown } from "./ActionCenterDropdown";

interface NavbarProps {
  user: User;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  onLogout: () => void;
  onNewLeadClick?: () => void;
}

interface NavModule {
  id: string;
  label: string;
  icon: React.ElementType;
  iconColor?: string;
  visible: (user: User) => boolean;
}

const isDataEntry = (u: User) => Boolean(u.is_data_entry || u.platform_role === "DATA_ENTRY" || u.tenant_role === "DATA_ENTRY");
const isSuperAdmin = (u: User) => Boolean(u.is_super_admin);
const isTelecaller = (u: User) => u.tenant_role === "TELECALLER";
const isOrgAdmin = (u: User) => u.tenant_role === "ORG_ADMIN";

const NAVIGATION_CONFIG: NavModule[] = [
  // Platform / Super Admin Modules
  { id: "dashboard", label: "Dashboard", icon: ActivitySquare, visible: isSuperAdmin },
  { id: "organizations", label: "Organizations", icon: Building2, visible: isSuperAdmin },
  { id: "global_edits", label: "Global Edits", icon: ActivitySquare, iconColor: "var(--amber)", visible: isSuperAdmin },
  { id: "users", label: "Users", icon: Users, visible: isSuperAdmin },
  { id: "audit", label: "Platform Activities", icon: ActivitySquare, visible: isSuperAdmin },

  // Data Entry Exclusive Modules (Hidden from Tenant Admins)
  { id: "global", label: "Company Intelligence", icon: Globe2, iconColor: "var(--cyan)", visible: (u) => isDataEntry(u) || isSuperAdmin(u) },
  { id: "people", label: "People Intelligence", icon: UserCheck, iconColor: "var(--emerald)", visible: (u) => isDataEntry(u) || isSuperAdmin(u) },

  // Telecaller Desk
  { id: "telecaller", label: "Calling Desk", icon: PhoneCall, visible: isTelecaller },

  // Locked Tenant Module Structure
  { id: "radar", label: "Radar Insights", icon: Sparkles, iconColor: "var(--amber)", visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "global_intelligence", label: "Global Registry", icon: BrainCircuit, iconColor: "var(--primary)", visible: (u) => !isTelecaller(u) },
  { id: "leads", label: "Leads & Contacts", icon: Users, visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "pipeline", label: "Pipeline", icon: Kanban, visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "team", label: "Team & Telecallers", icon: UserCheck, iconColor: "var(--emerald)", visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "import", label: "Data Ingestion", icon: UploadCloud, iconColor: "#6366f1", visible: (u) => isDataEntry(u) || (!isSuperAdmin(u) && !isTelecaller(u)) },
  { id: "products", label: "Products & Services", icon: Briefcase, visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "templates", label: "Templates", icon: ActivitySquare, iconColor: "var(--primary)", visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "governance", label: "Data Governance", icon: Shield, iconColor: "var(--primary)", visible: (u) => !isSuperAdmin(u) && !isTelecaller(u) && !isDataEntry(u) },
  { id: "api_keys", label: "Developer Settings", icon: Key, iconColor: "var(--amber)", visible: (u) => !isTelecaller(u) && !isDataEntry(u) }
];

export const Navbar: React.FC<NavbarProps> = ({ user, activeTab, setActiveTab, onLogout, onNewLeadClick }) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [visibleCount, setVisibleCount] = useState(10);
  const containerRef = useRef<HTMLDivElement>(null);
  const [moreDropdownOpen, setMoreDropdownOpen] = useState(false);

  const allowedTabs = NAVIGATION_CONFIG.filter(mod => mod.visible(user));

  useEffect(() => {
    const handleResize = () => {
      if (containerRef.current) {
        // Approximate width: each tab is ~160px
        const containerWidth = containerRef.current.offsetWidth;
        const estimatedFit = Math.floor(containerWidth / 160);
        setVisibleCount(Math.max(1, estimatedFit - 1)); // -1 for the "More" button
      }
    };
    
    // Slight delay to allow flexbox to calculate initial width
    const timer = setTimeout(handleResize, 100);
    window.addEventListener("resize", handleResize);
    return () => {
      clearTimeout(timer);
      window.removeEventListener("resize", handleResize);
    };
  }, [allowedTabs.length]);

  const handleTabClick = (tab: string) => {
    setActiveTab(tab);
    setMobileMenuOpen(false);
    setMoreDropdownOpen(false);
  };

  const visibleNavTabs = allowedTabs.slice(0, visibleCount);
  const hiddenNavTabs = allowedTabs.slice(visibleCount);

  return (
    <header className="nav-header">
      <div className="nav-container">
        {/* Brand & Workspace */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexShrink: 0 }}>
          <img
            src="/jarvis-icon.png"
            alt="JARVIS CRM"
            style={{
              width: "32px",
              height: "32px",
              objectFit: "contain",
              flexShrink: 0,
              filter: "drop-shadow(0 2px 6px rgba(6, 182, 212, 0.4))"
            }}
          />
          <div style={{ minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
              <span style={{ fontWeight: 800, fontSize: "0.95rem", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                JARVIS
              </span>
              <span style={{
                fontSize: "0.5625rem",
                fontWeight: 700,
                padding: "1px 5px",
                borderRadius: "3px",
                background: "var(--primary-light)",
                color: "var(--primary)",
                border: "1px solid var(--primary-border)",
                letterSpacing: "0.03em"
              }}>
                RADAR CRM
              </span>
            </div>
            <p style={{
              fontSize: "0.6875rem",
              color: "var(--text-secondary)",
              fontWeight: 500,
              whiteSpace: "nowrap",
              overflow: "hidden",
              textOverflow: "ellipsis",
              maxWidth: "135px"
            }} title={user.organization ? user.organization.name : undefined}>
              {user.organization ? user.organization.name : isDataEntry(user) ? "Data Operations" : "Platform Management"}
            </p>
          </div>
        </div>

        {/* Desktop Navigation Tabs */}
        <nav className="nav-tabs-wrapper" style={{ display: "flex", flex: 1, overflow: "visible", position: "relative" }} ref={containerRef}>
          {visibleNavTabs.map((tab) => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={`nav-tab-btn ${activeTab === tab.id ? "active" : ""}`}
              >
                <Icon style={{ width: "14px", height: "14px", color: tab.iconColor || "inherit" }} />
                {tab.label}
              </button>
            );
          })}
          
          {hiddenNavTabs.length > 0 && (
            <div style={{ position: "relative" }}>
              <button
                onClick={() => setMoreDropdownOpen(!moreDropdownOpen)}
                className={`nav-tab-btn ${hiddenNavTabs.some(t => t.id === activeTab) ? "active" : ""}`}
              >
                More <ChevronDown style={{ width: "14px", height: "14px", marginLeft: "2px" }} />
              </button>
              {moreDropdownOpen && (
                <div style={{
                  position: "absolute",
                  top: "100%",
                  right: 0,
                  marginTop: "4px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "8px",
                  boxShadow: "var(--shadow-md)",
                  zIndex: 1000,
                  minWidth: "220px",
                  padding: "8px"
                }}>
                  {hiddenNavTabs.map(tab => {
                    const Icon = tab.icon;
                    return (
                      <button
                        key={tab.id}
                        onClick={() => handleTabClick(tab.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "8px",
                          width: "100%",
                          padding: "10px 12px",
                          background: activeTab === tab.id ? "var(--bg-subtle)" : "transparent",
                          border: "none",
                          borderRadius: "4px",
                          cursor: "pointer",
                          color: activeTab === tab.id ? "var(--primary)" : "var(--text-primary)",
                          fontSize: "0.8125rem",
                          fontWeight: 500,
                          textAlign: "left"
                        }}
                      >
                        <Icon style={{ width: "16px", height: "16px", color: tab.iconColor || "var(--text-secondary)" }} />
                        {tab.label}
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          )}
        </nav>

        {/* User Profile & Actions */}
        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
          <div style={{ textAlign: "right" }} className="user-profile-meta">
            <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", maxWidth: "125px" }} title={user.full_name}>
              {user.full_name}
            </p>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "4px" }}>
              {isTelecaller(user) ? (
                <span className="badge badge-masked" style={{ fontSize: "0.625rem" }}>
                  <Lock style={{ width: "10px", height: "10px" }} />
                  TELECALLER
                </span>
              ) : isSuperAdmin(user) ? (
                <span className="badge badge-hot" style={{ fontSize: "0.625rem" }}>
                  <ShieldCheck style={{ width: "10px", height: "10px" }} />
                  SUPER ADMIN
                </span>
              ) : isDataEntry(user) ? (
                <span className="badge" style={{ fontSize: "0.625rem", background: "rgba(245, 158, 11, 0.15)", color: "#b45309", border: "1px solid rgba(245, 158, 11, 0.3)", fontWeight: 700 }}>
                  DATA ENTRY
                </span>
              ) : (
                <span className="badge badge-medium" style={{ fontSize: "0.625rem" }}>
                  {user.effective_role}
                </span>
              )}
            </div>
          </div>

          <ActionCenterDropdown />

          <button
            onClick={onLogout}
            title="Sign out"
            style={{
              padding: "7px",
              borderRadius: "7px",
              border: "1px solid var(--border-subtle)",
              background: "var(--bg-surface)",
              color: "var(--text-secondary)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "all 0.15s ease"
            }}
            onMouseOver={(e) => {
              e.currentTarget.style.color = "var(--rose)";
              e.currentTarget.style.borderColor = "var(--rose-border)";
              e.currentTarget.style.background = "var(--rose-light)";
            }}
            onMouseOut={(e) => {
              e.currentTarget.style.color = "var(--text-secondary)";
              e.currentTarget.style.borderColor = "var(--border-subtle)";
              e.currentTarget.style.background = "var(--bg-surface)";
            }}
          >
            <LogOut style={{ width: "15px", height: "15px" }} />
          </button>

          {/* Mobile Hamburger Toggle */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="mobile-hamburger-btn"
            style={{
              padding: "8px",
              borderRadius: "8px",
              border: "1px solid var(--border-subtle)",
              background: "var(--bg-surface)",
              color: "var(--text-primary)",
              cursor: "pointer",
              display: "none"
            }}
          >
            {mobileMenuOpen ? <X style={{ width: "18px", height: "18px" }} /> : <Menu style={{ width: "18px", height: "18px" }} />}
          </button>
        </div>
      </div>

      {/* Responsive Mobile Dropdown Menu */}
      {mobileMenuOpen && (
        <div style={{
          marginTop: "12px",
          paddingTop: "12px",
          borderTop: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          gap: "6px"
        }}>
          {allowedTabs.map(tab => {
            const Icon = tab.icon;
            return (
              <button
                key={tab.id}
                onClick={() => handleTabClick(tab.id)}
                className={`nav-tab-btn ${activeTab === tab.id ? "active" : ""}`}
                style={{ justifyContent: "flex-start", padding: "10px 14px", width: "100%" }}
              >
                <Icon style={{ width: "16px", height: "16px", color: tab.iconColor || "inherit" }} />
                {tab.label}
              </button>
            )
          })}
        </div>
      )}
    </header>
  );
};
