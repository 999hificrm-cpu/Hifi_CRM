import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { api, User, Lead, PipelineStage } from "./services/api";
import { Navbar } from "./components/Navbar";
import { LoginScreen } from "./components/LoginScreen";
import { KanbanBoard } from "./components/KanbanBoard";
import { LeadsTable } from "./components/LeadsTable";
import { LeadDetailModal } from "./components/LeadDetailModal";
import { ImportModal } from "./components/ImportModal";
import { TelecallerDesk } from "./components/TelecallerDesk";
import { GlobalRegistryView } from "./components/GlobalRegistryView";
import { RadarView } from "./components/RadarView";
import { SuperAdminView } from "./components/SuperAdminView";
import { PeopleIntelligenceView } from "./components/PeopleIntelligenceView";
import { GlobalIntelligenceView } from "./components/GlobalIntelligenceView";
import { GlobalEditsView } from "./components/GlobalEditsView";
import { TeamManagementView } from "./components/TeamManagementView";
import { DataGovernanceView } from "./components/DataGovernanceView";
import { OperationsView } from "./components/OperationsView";
import { ApiKeysManagement } from "./components/ApiKeysManagement";
import { ProductsServicesView } from "./components/ProductsServicesView";
import { NewLeadModal } from "./components/NewLeadModal";
import { TemplatesView } from "./components/TemplatesView";
import { ExpiredScreen } from "./components/ExpiredScreen";
import { Building2, Search, DownloadCloud, Key, UserCheck, ShieldAlert, FileText, ArrowRightCircle, RefreshCcw, Bell, LogOut, ChevronRight, ActivitySquare, LayoutGrid, CheckCircle2, AlertCircle, FileSpreadsheet, ListTodo, Users, Mail, Phone, Calendar, Clock, BarChart3, Settings, MoreVertical, SearchCode, Database, Layers, ArrowUpRight, FolderOpen, PieChart, Shield, Target, Plus, UploadCloud, Download, MessageSquare, Briefcase, Zap, Star, Filter, Share2, Trash2, BrainCircuit, Globe2 } from "lucide-react";

export const TAB_TO_ROUTE: Record<string, string> = {
  radar: "/radar_insights",
  pipeline: "/pipeline",
  leads: "/leads",
  import: "/imports",
  global_intelligence: "/global_intelligence",
  global: "/global_registry",
  team: "/team",
  templates: "/templates",
  telecaller: "/telecaller_desk",
  people: "/people",
  organizations: "/organizations",
  audit: "/audit",
  security: "/super_admin_security",
  recovery: "/super_admin_recovery",
  dashboard: "/super_admin_dashboard",
  users: "/super_admin_users",
  operations: "/super_admin_operations",
  governance: "/data_governance",
  api_keys: "/api_keys",
  products: "/products",
  global_edits: "/global_edits",
};

export const ROUTE_TO_TAB: Record<string, string> = {
  "/radar_insights": "radar",
  "/radar": "radar",
  "/pipeline": "pipeline",
  "/leads": "leads",
  "/imports": "import",
  "/import": "import",
  "/global_intelligence": "global_intelligence",
  "/global": "global",
  "/global_registry": "global",
  "/team": "team",
  "/templates": "templates",
  "/telecaller_desk": "telecaller",
  "/telecaller": "telecaller",
  "/people": "people",
  "/super_admin": "dashboard",
  "/super_admin_dashboard": "dashboard",
  "/super_admin_users": "users",
  "/organizations": "organizations",
  "/audit": "audit",
  "/security": "security",
  "/super_admin_security": "security",
  "/recovery": "recovery",
  "/super_admin_recovery": "recovery",
  "/super_admin_operations": "operations",
  "/operations": "operations",
  "/data_governance": "governance",
  "/governance": "governance",
  "/api_keys": "api_keys",
  "/products": "products",
  "/global_edits": "global_edits",
};

export const App: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const [currentUser, setCurrentUser] = useState<User | null>(null);
  const [loadingUser, setLoadingUser] = useState(true);
  const [activeTab, setActiveTab] = useState<string>("pipeline");

  // CRM Data
  const [stages, setStages] = useState<PipelineStage[]>([]);
  const [leads, setLeads] = useState<Lead[]>([]);
  const [selectedLead, setSelectedLead] = useState<Lead | null>(null);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showNewLeadModal, setShowNewLeadModal] = useState(false);

  const getDefaultTabAndRoute = (user: User) => {
    if (user.is_super_admin) return { tab: "dashboard", route: "/super_admin_dashboard" };
    if (user.is_data_entry || user.platform_role === "DATA_ENTRY" || user.tenant_role === "DATA_ENTRY") {
      return { tab: "global_intelligence", route: "/global_intelligence" };
    }
    if (user.tenant_role === "TELECALLER") return { tab: "telecaller", route: "/telecaller_desk" };
    return { tab: "radar", route: "/radar_insights" };
  };

  const handleTabChange = (newTab: string) => {
    setActiveTab(newTab);
    const targetRoute = TAB_TO_ROUTE[newTab] || `/${newTab}`;
    if (location.pathname !== targetRoute) {
      navigate(targetRoute);
    }
  };

  useEffect(() => {
    checkCurrentUser();
  }, []);

  // Listen to browser URL changes (back/forward navigation & deep linking)
  useEffect(() => {
    if (!currentUser) return;
    const currentPath = location.pathname;
    let matchedTab = ROUTE_TO_TAB[currentPath] || null;
    
    // --- SECURITY ROUTE GUARD ---
    if (matchedTab) {
      const superAdminTabs = ['dashboard', 'organizations', 'users', 'security', 'audit', 'recovery', 'operations', 'global_edits'];
      const orgAdminTabs = ['team', 'governance', 'api_keys', 'templates', 'organizations', 'security', 'audit', 'recovery', 'products', 'global', 'global_intelligence', 'people'];
      const dataEntryTabs = ['global_intelligence', 'global', 'people', 'import'];
      const isDataEntry = Boolean(currentUser.is_data_entry || currentUser.platform_role === 'DATA_ENTRY' || currentUser.tenant_role === 'DATA_ENTRY');

      if (!currentUser.is_super_admin && superAdminTabs.includes(matchedTab)) {
        matchedTab = null;
      } else if (isDataEntry && !dataEntryTabs.includes(matchedTab)) {
        matchedTab = null;
      } else if (currentUser.tenant_role === 'TELECALLER' && matchedTab !== 'telecaller') {
        matchedTab = null;
      }
    }
    // -----------------------------

    if (matchedTab) {
      if (activeTab !== matchedTab) {
        setActiveTab(matchedTab);
      }
    } else if (currentPath === "/" || currentPath === "/login" || !matchedTab) {
      const def = getDefaultTabAndRoute(currentUser);
      setActiveTab(def.tab);
      navigate(def.route, { replace: true });
    }
  }, [location.pathname, currentUser]);

  const checkCurrentUser = async () => {
    const token = api.getToken();
    if (!token) {
      setLoadingUser(false);
      if (location.pathname !== "/login") {
        navigate("/login", { replace: true });
      }
      return;
    }
    try {
      const user = await api.getMe();
      setCurrentUser(user);
      localStorage.setItem("jarvis_user", JSON.stringify(user));

      const currentPath = window.location.pathname;
      let matchedTab = ROUTE_TO_TAB[currentPath] || null;
      
      // --- SECURITY ROUTE GUARD ---
      if (matchedTab) {
        const superAdminTabs = ['dashboard', 'organizations', 'users', 'security', 'audit', 'recovery', 'operations', 'global_edits'];
        const orgAdminTabs = ['team', 'governance', 'api_keys', 'templates', 'organizations', 'security', 'audit', 'recovery', 'products', 'global', 'global_intelligence', 'people'];
        const dataEntryTabs = ['global_intelligence', 'global', 'people', 'import'];
        const isDataEntry = Boolean(user.is_data_entry || user.platform_role === 'DATA_ENTRY' || user.tenant_role === 'DATA_ENTRY');

        if (!user.is_super_admin && superAdminTabs.includes(matchedTab)) {
          matchedTab = null;
        } else if (isDataEntry && !dataEntryTabs.includes(matchedTab)) {
          matchedTab = null;
        } else if (user.tenant_role === 'TELECALLER' && matchedTab !== 'telecaller') {
          matchedTab = null;
        }
      }
      // -----------------------------

      if (matchedTab) {
        setActiveTab(matchedTab);
      } else {
        const def = getDefaultTabAndRoute(user);
        setActiveTab(def.tab);
        navigate(def.route, { replace: true });
      }
    } catch (e) {
      api.clearToken();
      navigate("/login", { replace: true });
    } finally {
      setLoadingUser(false);
    }
  };

  useEffect(() => {
    if (currentUser && !currentUser.is_super_admin && !(currentUser.is_data_entry || currentUser.platform_role === "DATA_ENTRY")) {
      loadCRMData();
    }
  }, [currentUser]);

  // --- SECURITY GUARDRAIL: IDLE SESSION TIMEOUT ---
  useEffect(() => {
    if (!currentUser) return;
    
    let timeoutId: number | undefined;
    const resetTimer = () => {
      window.clearTimeout(timeoutId);
      timeoutId = window.setTimeout(() => {
        api.clearToken();
        localStorage.removeItem("jarvis_user");
        setCurrentUser(null);
        navigate("/login", { replace: true });
        alert("🔒 Security Guardrail: You have been automatically logged out due to 15 minutes of inactivity.");
      }, 15 * 60 * 1000);
    };

    window.addEventListener("mousemove", resetTimer);
    window.addEventListener("keydown", resetTimer);
    window.addEventListener("click", resetTimer);
    window.addEventListener("scroll", resetTimer);

    resetTimer();

    return () => {
      clearTimeout(timeoutId);
      window.removeEventListener("mousemove", resetTimer);
      window.removeEventListener("keydown", resetTimer);
      window.removeEventListener("click", resetTimer);
      window.removeEventListener("scroll", resetTimer);
    };
  }, [currentUser]);
  // ------------------------------------------------

  const loadCRMData = async () => {
    try {
      const [pipe, leadList] = await Promise.all([
        api.getPipeline(),
        api.getLeads(),
      ]);
      setStages(pipe.stages || []);
      setLeads(leadList || []);
    } catch (e) {
      console.error("Error loading CRM data:", e);
    }
  };

  const handleMoveStage = async (leadId: string, stageId: string) => {
    try {
      await api.updateLeadStage(leadId, stageId, "Quick stage movement from board");
      loadCRMData();
    } catch (err: any) {
      alert(err.message || "Failed to update stage");
    }
  };

  const handleLogout = () => {
    api.clearToken();
    localStorage.removeItem("jarvis_user");
    setCurrentUser(null);
    navigate("/login");
  };

  if (loadingUser) {
    return (
      <div style={{
        minHeight: "100vh",
        background: "var(--bg-canvas)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: "0.8125rem",
        color: "var(--primary)",
        fontFamily: "monospace",
        fontWeight: 600
      }}>
        Initializing JARVIS CRM Engine...
      </div>
    );
  }

  if (location.pathname === "/expired") {
    return <ExpiredScreen />;
  }

  if (!currentUser) {
    return (
      <LoginScreen
        onSuccess={(u) => {
          setCurrentUser(u);
          localStorage.setItem("jarvis_user", JSON.stringify(u));
          const def = getDefaultTabAndRoute(u);
          setActiveTab(def.tab);
          navigate(def.route, { replace: true });
        }}
      />
    );
  }

  return (
    <div className="app-wrapper" style={currentUser.is_super_admin ? { display: "flex", flexDirection: "row", height: "100vh", overflow: "hidden", background: "var(--bg-canvas)" } : undefined}>
      {currentUser.is_super_admin && (
        <aside style={{ width: '260px', background: '#0f172a', borderRight: '1px solid #1e293b', display: 'flex', flexDirection: 'column', flexShrink: 0, height: '100%' }}>
            <div style={{ padding: '20px 20px', display: 'flex', alignItems: 'center', gap: '12px', borderBottom: '1px solid #1e293b' }}>
              <img
                src="/jarvis-icon.png"
                alt="JARVIS"
                style={{ width: '38px', height: '38px', objectFit: 'contain', filter: 'drop-shadow(0 2px 8px rgba(6, 182, 212, 0.4))' }}
              />
              <div>
                 <span style={{ fontWeight: 800, fontSize: '1.1rem', color: '#f8fafc', letterSpacing: '-0.02em', display: 'block' }}>JARVIS</span>
                 <span style={{ fontSize: '0.625rem', fontWeight: 700, padding: '3px 8px', borderRadius: '4px', background: 'rgba(79,70,229,0.2)', color: '#818cf8', border: '1px solid rgba(79,70,229,0.3)', display: 'inline-block', marginTop: '2px' }}>SUPER ADMIN</span>
              </div>
            </div>
           
           <div style={{ padding: '24px 16px', display: 'flex', flexDirection: 'column', gap: '4px', flex: 1, overflowY: 'auto' }}>
              <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '8px', paddingLeft: '12px' }}>Platform</span>
              <button onClick={() => handleTabChange('dashboard')} className={`nav-tab-btn ${activeTab === 'dashboard' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'dashboard' ? '#fff' : '#94a3b8', background: activeTab === 'dashboard' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <ActivitySquare style={{ width: '16px', height: '16px' }} /> Dashboard
              </button>
              <button onClick={() => handleTabChange('organizations')} className={`nav-tab-btn ${activeTab === 'organizations' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'organizations' ? '#fff' : '#94a3b8', background: activeTab === 'organizations' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <Building2 style={{ width: '16px', height: '16px' }} /> Organizations
              </button>
              <button onClick={() => handleTabChange('users')} className={`nav-tab-btn ${activeTab === 'users' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'users' ? '#fff' : '#94a3b8', background: activeTab === 'users' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <Users style={{ width: '16px', height: '16px' }} /> Users
              </button>
              
              <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '20px', marginBottom: '8px', paddingLeft: '12px' }}>Global Data</span>
              <button onClick={() => handleTabChange('global_intelligence')} className={`nav-tab-btn ${activeTab === 'global_intelligence' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'global_intelligence' ? '#fff' : '#94a3b8', background: activeTab === 'global_intelligence' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <BrainCircuit style={{ width: '16px', height: '16px', color: activeTab === 'global_intelligence' ? '#818cf8' : '#6366f1' }} /> Intelligence Graph
              </button>
              <button onClick={() => handleTabChange('global')} className={`nav-tab-btn ${activeTab === 'global' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'global' ? '#fff' : '#94a3b8', background: activeTab === 'global' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <Globe2 style={{ width: '16px', height: '16px', color: activeTab === 'global' ? '#22d3ee' : '#06b6d4' }} /> Company Registry
              </button>
              <button onClick={() => handleTabChange('people')} className={`nav-tab-btn ${activeTab === 'people' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'people' ? '#fff' : '#94a3b8', background: activeTab === 'people' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <UserCheck style={{ width: '16px', height: '16px', color: activeTab === 'people' ? '#34d399' : '#10b981' }} /> People Directory
              </button>

              <span style={{ fontSize: '0.7rem', fontWeight: 800, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.08em', marginTop: '20px', marginBottom: '8px', paddingLeft: '12px' }}>System</span>
              <button onClick={() => handleTabChange('security')} className={`nav-tab-btn ${activeTab === 'security' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'security' ? '#fff' : '#94a3b8', background: activeTab === 'security' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <ShieldAlert style={{ width: '16px', height: '16px', color: activeTab === 'security' ? '#f59e0b' : '#d97706' }} /> Access & Security
              </button>
              <button onClick={() => handleTabChange('audit')} className={`nav-tab-btn ${activeTab === 'audit' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'audit' ? '#fff' : '#94a3b8', background: activeTab === 'audit' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <ActivitySquare style={{ width: '16px', height: '16px' }} /> Audit Logs
              </button>
              <button onClick={() => handleTabChange('operations')} className={`nav-tab-btn ${activeTab === 'operations' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'operations' ? '#fff' : '#94a3b8', background: activeTab === 'operations' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <ActivitySquare style={{ width: '16px', height: '16px', color: activeTab === 'operations' ? '#10b981' : '#059669' }} /> System Operations
              </button>
              <button onClick={() => handleTabChange('recovery')} className={`nav-tab-btn ${activeTab === 'recovery' ? 'active' : ''}`} style={{ justifyContent: 'flex-start', padding: '10px 12px', width: '100%', color: activeTab === 'recovery' ? '#fff' : '#94a3b8', background: activeTab === 'recovery' ? 'rgba(255,255,255,0.1)' : 'transparent' }}>
                 <Trash2 style={{ width: '16px', height: '16px', color: activeTab === 'recovery' ? '#ef4444' : '#dc2626' }} /> Recycle Bin
              </button>
           </div>
           
           <div style={{ padding: '20px', borderTop: '1px solid #1e293b', background: '#0f172a' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
                <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#1e293b', border: '1px solid #334155', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: '0.8125rem', color: '#f8fafc' }}>
                  {currentUser.full_name.charAt(0).toUpperCase()}
                </div>
                <div style={{ flex: 1, overflow: 'hidden' }}>
                  <p style={{ fontSize: '0.8125rem', fontWeight: 700, color: '#f8fafc', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{currentUser.full_name}</p>
                  <p style={{ fontSize: '0.6875rem', color: '#94a3b8', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{currentUser.email}</p>
                </div>
              </div>
              <button onClick={handleLogout} className="btn-secondary" style={{ width: '100%', justifyContent: 'center', background: '#1e293b', color: '#f8fafc', border: '1px solid #334155' }}>
                 <LogOut style={{ width: '14px', height: '14px' }} /> Sign Out
              </button>
           </div>
        </aside>
      )}

      <div style={currentUser.is_super_admin ? { flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', position: 'relative' } : {}}>
        {!currentUser.is_super_admin && (
          <Navbar
            user={currentUser}
            activeTab={activeTab}
            setActiveTab={handleTabChange}
            onLogout={handleLogout}
            onNewLeadClick={() => setShowNewLeadModal(true)}
          />
        )}

        <main className="main-content" style={currentUser.is_super_admin ? { padding: '24px 32px', overflowY: 'auto', flex: 1 } : {}}>
        {/* Telecaller Desk */}
        {activeTab === "telecaller" && <TelecallerDesk />}

        {/* Executive Radar */}
        {activeTab === "radar" && (
          <RadarView onSelectLead={(l) => setSelectedLead(l)} />
        )}

        {/* Pipeline Kanban */}
        {activeTab === "pipeline" && (
          <KanbanBoard
            stages={stages}
            leads={leads}
            onSelectLead={(l) => setSelectedLead(l)}
            onMoveStage={handleMoveStage}
            onNewLeadClick={() => setShowNewLeadModal(true)}
            onRefreshPipeline={loadCRMData}
          />
        )}

        {/* Leads & Contacts Directory */}
        {activeTab === "leads" && (
          <LeadsTable
            leads={leads}
            stages={stages}
            onSelectLead={(l) => setSelectedLead(l)}
            onMoveStage={handleMoveStage}
            onNewLeadClick={() => setShowNewLeadModal(true)}
            onRefresh={loadCRMData}
          />
        )}

        {/* Team & Telecaller Management */}
        {activeTab === "team" && (
          <TeamManagementView onNavigateToLeads={() => handleTabChange("leads")} />
        )}

        {/* Templates Management */}
        {activeTab === "templates" && (
          <TemplatesView />
        )}

        {/* Import Leads Landing */}
        {activeTab === "import" && (
          <div className="card" style={{ padding: "48px 32px", textAlign: "center", maxWidth: "560px", margin: "48px auto" }}>
            <div style={{
              width: "64px",
              height: "64px",
              borderRadius: "16px",
              background: "var(--primary-light)",
              border: "1px solid var(--primary-border)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 20px auto",
              color: "var(--primary)",
              boxShadow: "0 8px 16px rgba(79, 70, 229, 0.12)"
            }}>
              <UploadCloud style={{ width: "32px", height: "32px" }} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
                Bulk Lead & Contact Ingestion
              </h3>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "6px", maxWidth: "380px", marginInline: "auto" }}>
                Ingest 1,000 to 100,000 leads with smart column auto-detection, E.164 phone normalization, and guaranteed pipeline immutability.
              </p>
            </div>

            <div style={{ marginTop: "24px" }}>
              <button
                onClick={() => setShowImportModal(true)}
                className="btn-primary"
                style={{ padding: "10px 24px" }}
              >
                <FileSpreadsheet style={{ width: "16px", height: "16px" }} />
                Launch Ingestion Wizard
              </button>
            </div>
          </div>
        )}

        {/* Global Intelligence Graph (Unified Company & People) */}
        {activeTab === "global_intelligence" && (
          <GlobalIntelligenceView isOrgAdmin={false} currentUser={currentUser} />
        )}

        {/* Global Registry in ORG Admin / Company Intelligence in Super Admin & Data Entry */}
        {activeTab === "global" && (
          (currentUser.is_super_admin || currentUser.is_data_entry || currentUser.platform_role === "DATA_ENTRY" || currentUser.tenant_role === "DATA_ENTRY") ? (
            <GlobalRegistryView currentUser={currentUser} />
          ) : (
            <GlobalIntelligenceView isOrgAdmin={true} currentUser={currentUser} />
          )
        )}

        {/* Global People Intelligence (Super Admin & Data Entry) */}
        {activeTab === "people" && <PeopleIntelligenceView currentUser={currentUser} />}

        {/* Data Governance & Data Quality */}
        {activeTab === "governance" && <DataGovernanceView />}

        {/* API Keys */}
        {activeTab === "api_keys" && <ApiKeysManagement />}

        {/* Products & Services */}
        {activeTab === "products" && <ProductsServicesView />}

        {/* Super Admin Control */}
        {activeTab === "dashboard" && <SuperAdminView viewMode="dashboard" />}
        {activeTab === "organizations" && <SuperAdminView viewMode="organizations" />}
        {activeTab === "users" && <SuperAdminView viewMode="users" />}
        {activeTab === "security" && <SuperAdminView viewMode="security" />}
        {activeTab === "audit" && <SuperAdminView viewMode="audit" />}
        {activeTab === "recovery" && <SuperAdminView viewMode="recovery" />}
        {activeTab === "global_edits" && <GlobalEditsView />}
        {activeTab === "operations" && <OperationsView />}
        </main>
      </div>

      {/* Modals */}
      {selectedLead && (
        <LeadDetailModal
          lead={selectedLead}
          stages={stages}
          onClose={() => setSelectedLead(null)}
          onRefresh={loadCRMData}
        />
      )}

      {showImportModal && (
        <ImportModal
          jobType={currentUser.is_data_entry || currentUser.platform_role === "DATA_ENTRY" ? "GLOBAL_COMPANIES" : undefined}
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            if (currentUser.is_data_entry || currentUser.platform_role === "DATA_ENTRY") {
              handleTabChange("global_intelligence");
            } else {
              loadCRMData();
              handleTabChange("pipeline");
            }
          }}
        />
      )}

      {showNewLeadModal && (
        <NewLeadModal
          stages={stages}
          onClose={() => setShowNewLeadModal(false)}
          onSuccess={loadCRMData}
        />
      )}
    </div>
  );
};

export default App;
