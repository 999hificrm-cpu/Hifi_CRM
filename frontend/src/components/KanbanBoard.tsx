import React, { useState, useEffect, useRef, useMemo } from "react";
import { Lead, PipelineStage, api } from "../services/api";
import { openGmail } from "../utils/mailHelper";
// import { EmailComposeModal } from "./EmailComposeModal";
import { format10DigitPhone, getCallUrl } from "../utils/phoneHelper";
import {
  Plus,
  Flame,
  Phone,
  Mail,
  ArrowRight,
  GripVertical,
  ArrowDown,
  Search,
  CheckCircle2,
  Sparkles,
  SlidersHorizontal,
  ChevronDown,
  Check,
  Layers,
  Pencil,
  X
} from "lucide-react";

interface KanbanBoardProps {
  stages: PipelineStage[];
  leads: Lead[];
  onSelectLead: (lead: Lead) => void;
  onMoveStage: (leadId: string, stageId: string) => void;
  onNewLeadClick: () => void;
  onRefreshPipeline?: () => void;
}

export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  stages,
  leads,
  onSelectLead,
  onMoveStage,
  onNewLeadClick,
  onRefreshPipeline,
}) => {
  const [localStages, setLocalStages] = useState<PipelineStage[]>(stages);
  const [localLeads, setLocalLeads] = useState<Lead[]>(leads);
  const [selectedStageIds, setSelectedStageIds] = useState<string[]>([]);
  const [showStageDropdown, setShowStageDropdown] = useState(false);
  const [showAddStageModal, setShowAddStageModal] = useState(false);

  // Partition 1: Leads Queue State
  const [leadsPartitionFilter, setLeadsPartitionFilter] = useState<"NEW" | "ALL">("NEW");
  const [leadsPartitionSearch, setLeadsPartitionSearch] = useState("");

  // Partition 2: Drag & Drop State
  const [draggingLeadId, setDraggingLeadId] = useState<string | null>(null);
  const [dragOverStageId, setDragOverStageId] = useState<string | null>(null);
  const [statusMessage, setStatusMessage] = useState<{ text: string; stageName: string } | null>(null);

  // New Custom Stage Form State
  const [newStageName, setNewStageName] = useState("");
  const [newStageColor, setNewStageColor] = useState("#4f46e5");
  const [newStageProbability, setNewStageProbability] = useState("50");
  const [newStageType, setNewStageType] = useState<"STANDARD" | "WON" | "LOST">("STANDARD");
  const [creatingStage, setCreatingStage] = useState(false);
  const [stageError, setStageError] = useState<string | null>(null);
  const [copiedEmailId, setCopiedEmailId] = useState<string | null>(null);

  const handleCopyEmail = (email: string, id: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmailId(id);
    setTimeout(() => setCopiedEmailId(null), 2000);
  };

  // Edit Existing Stage Form State
  const [editingStage, setEditingStage] = useState<PipelineStage | null>(null);
  const [editStageName, setEditStageName] = useState("");
  const [editStageCode, setEditStageCode] = useState("");
  const [editStageColor, setEditStageColor] = useState("#4f46e5");
  const [editStageProbability, setEditStageProbability] = useState("50");
  const [editStageType, setEditStageType] = useState<"STANDARD" | "WON" | "LOST">("STANDARD");
  const [updatingStage, setUpdatingStage] = useState(false);
  const [editStageError, setEditStageError] = useState<string | null>(null);

  const isDraggingRef = useRef(false);
  const dragSourceStageIdRef = useRef<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Synchronize local stages when props change
  useEffect(() => {
    setLocalStages(stages);
    if (selectedStageIds.length === 0 && stages.length > 0) {
      setSelectedStageIds(stages.map((s) => s.id));
    }
  }, [stages]);

  // Synchronize local leads when props change
  useEffect(() => {
    setLocalLeads(leads);
  }, [leads]);

  // Close stage dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowStageDropdown(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Format revenue in Indian currency
  const formatRevenue = (value: number) => {
    if (value >= 10000000) return `₹${(value / 10000000).toFixed(2)} Cr`;
    if (value >= 100000) return `₹${(value / 100000).toFixed(1)} L`;
    if (value >= 1000) return `₹${(value / 1000).toFixed(0)}k`;
    return `₹${value.toLocaleString("en-IN")}`;
  };

  // Visible stages selected via Admin multi-select dropdown
  const visibleStages = useMemo(() => {
    return localStages.filter((s) => selectedStageIds.includes(s.id));
  }, [localStages, selectedStageIds]);

  // Partition 1: Leads Queue (New leads or all leads to pick and drag)
  const partitionLeads = useMemo(() => {
    const initialStageId = localStages[0]?.id;
    return localLeads.filter((lead) => {
      if (leadsPartitionFilter === "NEW") {
        const isNew = !lead.pipeline_stage_id || lead.pipeline_stage_id === initialStageId || lead.status === "NEW";
        if (!isNew) return false;
      }
      if (leadsPartitionSearch.trim()) {
        const q = leadsPartitionSearch.toLowerCase().trim();
        const matchTitle = lead.title?.toLowerCase().includes(q);
        const matchCompany = lead.company_name?.toLowerCase().includes(q);
        const matchContact = lead.contact_name?.toLowerCase().includes(q);
        const matchPhone = lead.contact_phone?.includes(q);
        if (!matchTitle && !matchCompany && !matchContact && !matchPhone) return false;
      }
      return true;
    });
  }, [localLeads, localStages, leadsPartitionFilter, leadsPartitionSearch]);

  // Toggle stage visibility in multi-select dropdown
  const handleToggleStage = (stageId: string) => {
    setSelectedStageIds((prev) => {
      if (prev.includes(stageId)) {
        if (prev.length === 1) return prev; // Keep at least one stage visible
        return prev.filter((id) => id !== stageId);
      } else {
        return [...prev, stageId];
      }
    });
  };

  // Select all or reset stages
  const handleSelectAllStages = () => {
    setSelectedStageIds(localStages.map((s) => s.id));
  };

  // Drag Handlers
  const handleDragStart = (e: React.DragEvent, lead: Lead, stageId: string) => {
    isDraggingRef.current = true;
    dragSourceStageIdRef.current = stageId;
    setDraggingLeadId(lead.id);

    e.dataTransfer.setData("text/plain", lead.id);
    e.dataTransfer.effectAllowed = "move";
  };

  const handleDragEnd = () => {
    setDraggingLeadId(null);
    setDragOverStageId(null);
    dragSourceStageIdRef.current = null;
    // Debounce resetting isDragging so following click event doesn't trigger onSelectLead
    setTimeout(() => {
      isDraggingRef.current = false;
    }, 120);
  };

  const handleDragOver = (e: React.DragEvent, stageId: string) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (dragOverStageId !== stageId) {
      setDragOverStageId(stageId);
    }
  };

  const handleDrop = (e: React.DragEvent, targetStage: PipelineStage) => {
    e.preventDefault();
    const droppedLeadId = e.dataTransfer.getData("text/plain") || draggingLeadId;

    setDraggingLeadId(null);
    setDragOverStageId(null);
    dragSourceStageIdRef.current = null;

    if (!droppedLeadId) return;

    // Check if lead already in this stage
    const currentLead = localLeads.find((l) => l.id === droppedLeadId);
    if (!currentLead || currentLead.pipeline_stage_id === targetStage.id) {
      return;
    }

    // Optimistic UI state update
    setLocalLeads((prev) =>
      prev.map((l) => (l.id === droppedLeadId ? { ...l, pipeline_stage_id: targetStage.id } : l))
    );

    // Flash toast banner
    setStatusMessage({
      text: `Moved "${currentLead.title}"`,
      stageName: targetStage.name,
    });
    setTimeout(() => {
      setStatusMessage(null);
    }, 3500);

    // Trigger backend stage transition
    onMoveStage(droppedLeadId, targetStage.id);
  };

  const handleCardClick = (lead: Lead) => {
    if (isDraggingRef.current) return;
    onSelectLead(lead);
  };

  // Create Custom Stage
  const handleCreateCustomStage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newStageName.trim()) {
      setStageError("Please enter a valid stage name");
      return;
    }

    setCreatingStage(true);
    setStageError(null);

    try {
      const code = newStageName.trim().toUpperCase().replace(/[^A-Z0-9]/g, "_");
      const orderIndex = localStages.length;
      const prob = Number(newStageProbability) || 50;

      const created = await api.createStage({
        name: newStageName.trim(),
        code,
        order_index: orderIndex,
        color: newStageColor,
        win_probability: prob,
        is_won: newStageType === "WON",
        is_lost: newStageType === "LOST"
      });

      // Update local stages and add to selected stages
      setLocalStages((prev) => [...prev, created]);
      setSelectedStageIds((prev) => [...prev, created.id]);

      setStatusMessage({
        text: `Created Custom Stage`,
        stageName: created.name
      });
      setTimeout(() => setStatusMessage(null), 4000);

      // Reset form and close modal
      setNewStageName("");
      setShowAddStageModal(false);

      if (onRefreshPipeline) {
        onRefreshPipeline();
      }
    } catch (err: any) {
      setStageError(err.message || "Failed to create stage");
    } finally {
      setCreatingStage(false);
    }
  };

  const STAGE_PRESETS = [
    { name: "New", code: "NEW", color: "#3b82f6", prob: "10", type: "STANDARD" as const },
    { name: "Contacted", code: "CONTACTED", color: "#8b5cf6", prob: "30", type: "STANDARD" as const },
    { name: "Qualified", code: "QUALIFIED", color: "#06b6d4", prob: "50", type: "STANDARD" as const },
    { name: "Meeting Scheduled", code: "MEETING_SCHEDULED", color: "#d97706", prob: "65", type: "STANDARD" as const },
    { name: "Proposal Sent", code: "PROPOSAL_SENT", color: "#4f46e5", prob: "80", type: "STANDARD" as const },
    { name: "Won", code: "WON", color: "#059669", prob: "100", type: "WON" as const },
    { name: "Lost", code: "LOST", color: "#e11d48", prob: "0", type: "LOST" as const },
  ];

  const handleOpenEditStage = (stage: PipelineStage) => {
    setEditingStage(stage);
    setEditStageName(stage.name);
    setEditStageCode(stage.code || stage.name.toUpperCase().replace(/[^A-Z0-9]/g, "_"));
    setEditStageColor(stage.color || "#4f46e5");
    setEditStageProbability(
      stage.win_probability !== undefined && stage.win_probability !== null
        ? String(stage.win_probability)
        : "50"
    );
    setEditStageType(stage.is_won ? "WON" : stage.is_lost ? "LOST" : "STANDARD");
    setEditStageError(null);
  };

  const applyEditPreset = (preset: (typeof STAGE_PRESETS)[0]) => {
    setEditStageName(preset.name);
    setEditStageCode(preset.code);
    setEditStageColor(preset.color);
    setEditStageProbability(preset.prob);
    setEditStageType(preset.type);
  };

  const handleSaveEditStage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingStage) return;
    if (!editStageName.trim()) {
      setEditStageError("Please enter a valid stage name");
      return;
    }

    setUpdatingStage(true);
    setEditStageError(null);

    try {
      const code = editStageCode.trim()
        ? editStageCode.trim().toUpperCase().replace(/[^A-Z0-9_]/g, "_")
        : editStageName.trim().toUpperCase().replace(/[^A-Z0-9]/g, "_");
      const prob = Number(editStageProbability) || 0;

      const updated = await api.updateStage(editingStage.id, {
        name: editStageName.trim(),
        code,
        color: editStageColor,
        win_probability: prob,
        is_won: editStageType === "WON",
        is_lost: editStageType === "LOST",
      });

      // Update local stages in state
      setLocalStages((prev) =>
        prev.map((s) => (s.id === updated.id ? updated : s))
      );

      setStatusMessage({
        text: `Stage updated to`,
        stageName: updated.name,
      });
      setTimeout(() => setStatusMessage(null), 4000);

      setEditingStage(null);

      if (onRefreshPipeline) {
        onRefreshPipeline();
      }
    } catch (err: any) {
      console.error("Failed to update stage:", err);
      setEditStageError(err?.message || "Failed to update stage");
    } finally {
      setUpdatingStage(false);
    }
  };

  const STAGE_COLORS = [
    { label: "Indigo", value: "#4f46e5" },
    { label: "Emerald", value: "#059669" },
    { label: "Cyan", value: "#06b6d4" },
    { label: "Amber", value: "#d97706" },
    { label: "Rose", value: "#e11d48" },
    { label: "Purple", value: "#8b5cf6" },
    { label: "Blue", value: "#3b82f6" },
    { label: "Slate", value: "#64748b" }
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Top Action Bar */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
              Sales Pipeline & Stages
            </h2>
            <span style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "999px",
              backgroundColor: "var(--primary-light)",
              color: "var(--primary)",
              border: "1px solid var(--primary-border)"
            }}>
              2-Partition Drag & Drop Board
            </span>
          </div>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Pick new leads from the Leads board (Partition 1) and drag into Pipeline Stages (Partition 2).
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Multi-Select Stages Dropdown */}
          <div style={{ position: "relative" }} ref={dropdownRef}>
            <button
              onClick={() => setShowStageDropdown(!showStageDropdown)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "8px 14px",
                borderRadius: "8px",
                border: "1px solid var(--border-medium)",
                background: "var(--bg-surface)",
                color: "var(--text-primary)",
                fontSize: "0.8125rem",
                fontWeight: 600,
                cursor: "pointer",
                boxShadow: "var(--shadow-xs)"
              }}
            >
              <SlidersHorizontal style={{ width: "14px", height: "14px", color: "var(--primary)" }} />
              <span>Stages ({selectedStageIds.length}/{localStages.length} Visible)</span>
              <ChevronDown style={{ width: "14px", height: "14px", color: "var(--text-muted)" }} />
            </button>

            {/* Dropdown Menu Popover */}
            {showStageDropdown && (
              <div
                style={{
                  position: "absolute",
                  top: "calc(100% + 6px)",
                  left: 0,
                  width: "280px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-subtle)",
                  borderRadius: "10px",
                  boxShadow: "var(--shadow-lg)",
                  padding: "12px",
                  zIndex: 100,
                  display: "flex",
                  flexDirection: "column",
                  gap: "10px"
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
                    Configure Visible Stages
                  </span>
                  <button
                    onClick={handleSelectAllStages}
                    style={{ background: "none", border: "none", color: "var(--primary)", fontSize: "0.6875rem", fontWeight: 600, cursor: "pointer" }}
                  >
                    Select All
                  </button>
                </div>

                {/* Stages List with Checkboxes and Edit buttons */}
                <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "220px", overflowY: "auto" }}>
                  {localStages.map((st) => {
                    const isChecked = selectedStageIds.includes(st.id);
                    const count = localLeads.filter((l) => l.pipeline_stage_id === st.id).length;
                    return (
                      <div
                        key={st.id}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "6px 8px",
                          borderRadius: "6px",
                          background: isChecked ? "var(--bg-surface-subtle)" : "transparent",
                          fontSize: "0.75rem",
                          userSelect: "none",
                        }}
                      >
                        <label
                          style={{
                            display: "flex",
                            alignItems: "center",
                            gap: "8px",
                            cursor: "pointer",
                            flex: 1,
                          }}
                        >
                          <input
                            type="checkbox"
                            checked={isChecked}
                            onChange={() => handleToggleStage(st.id)}
                            style={{ cursor: "pointer", accentColor: "var(--primary)" }}
                          />
                          <div style={{ width: "8px", height: "8px", borderRadius: "50%", backgroundColor: st.color || "var(--primary)" }} />
                          <span style={{ fontWeight: isChecked ? 600 : 400, color: "var(--text-primary)" }}>{st.name}</span>
                        </label>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontFamily: "monospace" }}>{count}</span>
                          <button
                            type="button"
                            title={`Edit "${st.name}" stage`}
                            onClick={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              handleOpenEditStage(st);
                            }}
                            style={{
                              background: "none",
                              border: "none",
                              cursor: "pointer",
                              color: "var(--text-muted)",
                              padding: "2px",
                              display: "inline-flex",
                              alignItems: "center",
                              borderRadius: "4px",
                            }}
                          >
                            <Pencil style={{ width: "11px", height: "11px" }} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Add Custom Stage Shortcut */}
                <button
                  onClick={() => {
                    setShowStageDropdown(false);
                    setShowAddStageModal(true);
                  }}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                    width: "100%",
                    padding: "7px",
                    borderRadius: "6px",
                    background: "var(--primary-light)",
                    border: "1px dashed var(--primary-border)",
                    color: "var(--primary)",
                    fontSize: "0.75rem",
                    fontWeight: 700,
                    cursor: "pointer"
                  }}
                >
                  <Plus style={{ width: "13px", height: "13px" }} />
                  + Add Custom Stage
                </button>
              </div>
            )}
          </div>

          {/* Add Custom Stage Header Button */}
          <button
            onClick={() => setShowAddStageModal(true)}
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "8px 14px",
              borderRadius: "8px",
              border: "1px solid var(--border-medium)",
              background: "var(--bg-surface)",
              color: "var(--text-primary)",
              fontSize: "0.8125rem",
              fontWeight: 600,
              cursor: "pointer",
              boxShadow: "var(--shadow-xs)"
            }}
          >
            <Plus style={{ width: "14px", height: "14px", color: "var(--emerald)" }} />
            + Custom Stage
          </button>

          {/* Create New Lead Button */}
          <button onClick={onNewLeadClick} className="btn-primary">
            <Plus style={{ width: "16px", height: "16px" }} />
            Create New Lead
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {statusMessage && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "8px 16px",
            borderRadius: "8px",
            background: "var(--emerald-light)",
            border: "1px solid var(--emerald-border)",
            color: "var(--emerald-dark)",
            fontSize: "0.8125rem",
            fontWeight: 600,
          }}
        >
          <CheckCircle2 style={{ width: "15px", height: "15px", color: "var(--emerald)" }} />
          <span>
            {statusMessage.text} &rarr; <strong>{statusMessage.stageName}</strong>
          </span>
        </div>
      )}

      {/* =========================================================================
          THE TWO-PARTITION BOARD (1. LEADS BOARD & 2. STAGES BOARD)
         ========================================================================= */}
      <div className="kanban-partitions-container" style={{ display: "flex", gap: "20px", alignItems: "flex-start", width: "100%" }}>
        {/* =====================================================================
            PARTITION 1: LEADS BOARD (Incoming / Pickable Leads Queue)
           ===================================================================== */}
        <div
          className="card kanban-partition-leads"
          style={{
            width: "330px",
            flexShrink: 0,
            padding: "16px",
            display: "flex",
            flexDirection: "column",
            gap: "12px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "14px",
            boxShadow: "var(--shadow-sm)",
            maxHeight: "82vh"
          }}
        >
          {/* Partition 1 Header */}
          <div style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: "10px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <Layers style={{ width: "15px", height: "15px", color: "var(--primary)" }} />
                <h3 style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.01em" }}>
                  1. Leads Board
                </h3>
              </div>
              <span style={{
                fontSize: "0.6875rem",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "999px",
                background: "var(--primary-light)",
                color: "var(--primary)"
              }}>
                {partitionLeads.length} leads
              </span>
            </div>
            <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              Pick new leads and drag into any stage column &rarr;
            </p>
          </div>

          {/* Leads Filter Switcher & Search */}
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {/* Toggle: New Leads vs All Leads */}
            <div style={{ display: "flex", background: "var(--bg-surface-subtle)", padding: "3px", borderRadius: "8px" }}>
              <button
                type="button"
                onClick={() => setLeadsPartitionFilter("NEW")}
                style={{
                  flex: 1,
                  padding: "4px 8px",
                  fontSize: "0.6875rem",
                  fontWeight: 700,
                  borderRadius: "6px",
                  border: "none",
                  background: leadsPartitionFilter === "NEW" ? "var(--bg-surface)" : "transparent",
                  color: leadsPartitionFilter === "NEW" ? "var(--primary)" : "var(--text-secondary)",
                  boxShadow: leadsPartitionFilter === "NEW" ? "var(--shadow-xs)" : "none",
                  cursor: "pointer"
                }}
              >
                New Leads
              </button>
              <button
                type="button"
                onClick={() => setLeadsPartitionFilter("ALL")}
                style={{
                  flex: 1,
                  padding: "4px 8px",
                  fontSize: "0.6875rem",
                  fontWeight: 700,
                  borderRadius: "6px",
                  border: "none",
                  background: leadsPartitionFilter === "ALL" ? "var(--bg-surface)" : "transparent",
                  color: leadsPartitionFilter === "ALL" ? "var(--primary)" : "var(--text-secondary)",
                  boxShadow: leadsPartitionFilter === "ALL" ? "var(--shadow-xs)" : "none",
                  cursor: "pointer"
                }}
              >
                All Leads Pool ({localLeads.length})
              </button>
            </div>

            {/* Search within leads pool */}
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "6px 10px",
              background: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "8px"
            }}>
              <Search style={{ width: "13px", height: "13px", color: "var(--text-muted)" }} />
              <input
                type="text"
                value={leadsPartitionSearch}
                onChange={(e) => setLeadsPartitionSearch(e.target.value)}
                placeholder="Search leads to pick..."
                style={{
                  width: "100%",
                  border: "none",
                  background: "transparent",
                  fontSize: "0.75rem",
                  color: "var(--text-primary)",
                  outline: "none"
                }}
              />
              {leadsPartitionSearch && (
                <button
                  onClick={() => setLeadsPartitionSearch("")}
                  style={{ background: "none", border: "none", fontSize: "0.6875rem", color: "var(--text-muted)", cursor: "pointer" }}
                >
                  <X style={{ width: "12px", height: "12px" }} />
                </button>
              )}
            </div>
          </div>

          {/* Partition 1 Cards List (Draggable into Partition 2) */}
          <div style={{ display: "flex", flexDirection: "column", gap: "10px", overflowY: "auto", flex: 1, paddingRight: "4px" }}>
            {partitionLeads.length === 0 ? (
              <div style={{ textAlign: "center", padding: "36px 12px", fontSize: "0.75rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                No leads in this queue. Create or select "All Leads Pool".
              </div>
            ) : (
              partitionLeads.map((lead) => {
                const isBeingDragged = draggingLeadId === lead.id;
                return (
                  <div
                    key={lead.id}
                    draggable={true}
                    onDragStart={(e) => handleDragStart(e, lead, lead.pipeline_stage_id || "leads_queue")}
                    onDragEnd={handleDragEnd}
                    onClick={() => handleCardClick(lead)}
                    className={`kanban-card ${isBeingDragged ? "is-dragging" : ""}`}
                    title="Drag this lead card into any stage column on the right"
                    style={{
                      padding: "12px",
                      background: "var(--bg-surface)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "10px",
                      boxShadow: "var(--shadow-xs)",
                      cursor: "grab"
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "6px" }}>
                      <span className={`badge ${lead.priority === "URGENT" || lead.priority === "HIGH" ? "badge-hot" : "badge-medium"}`}>
                        {lead.priority}
                      </span>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "3px", fontSize: "0.75rem", fontFamily: "monospace", fontWeight: 700, color: "var(--amber-dark)" }}>
                          <Flame style={{ width: "12px", height: "12px", color: "var(--amber)" }} />
                          {lead.score}
                        </div>
                        <GripVertical style={{ width: "14px", height: "14px", color: "var(--text-muted)" }} />
                      </div>
                    </div>

                    <h4 style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "3px", lineHeight: "1.3" }}>
                      {lead.title}
                    </h4>

                    <div style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", marginBottom: "6px" }}>
                      {lead.company_name && <p style={{ fontWeight: 600 }}>{lead.company_name}</p>}
                      {lead.contact_name && <p>{lead.contact_name}</p>}
                    </div>

                    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderTop: "1px dashed var(--border-subtle)", paddingTop: "6px" }}>
                      <span style={{ fontSize: "0.625rem", fontWeight: 700, color: "var(--primary)", display: "flex", alignItems: "center", gap: "3px" }}>
                        Drag to Stage &rarr;
                      </span>
                      {lead.stage && (
                        <span style={{ fontSize: "0.625rem", color: "var(--text-muted)", fontFamily: "monospace" }}>
                          {lead.stage.name}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* =====================================================================
            PARTITION 2: STAGES BOARD (Configurable Pipeline Columns)
           ===================================================================== */}
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", gap: "10px" }}>
          {/* Partition 2 Header Strip */}
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            padding: "8px 14px",
            background: "var(--bg-surface)",
            border: "1px solid var(--border-subtle)",
            borderRadius: "10px"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
              <span style={{ fontSize: "0.8125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                2. Pipeline Stages
              </span>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                Showing {visibleStages.length} of {localStages.length} configured stages
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
              <Sparkles style={{ width: "13px", height: "13px", color: "var(--primary)" }} />
              <span>Drop leads from Partition 1 or drag between stages</span>
            </div>
          </div>

          {/* Horizontal Columns Container */}
          <div
            className="kanban-stages-scroll-container"
            style={{
              display: "flex",
              gap: "16px",
              overflowX: "auto",
              paddingBottom: "16px",
              alignItems: "flex-start",
              minHeight: "calc(100vh - 290px)",
            }}
          >
            {visibleStages.map((stage, idx) => {
              const stageLeads = localLeads.filter((l) => l.pipeline_stage_id === stage.id);
              const totalValue = stageLeads.reduce((acc, curr) => acc + Number(curr.value || 0), 0);
              const isOverTarget = dragOverStageId === stage.id;
              const isDraggingCardFromOtherStage = Boolean(draggingLeadId && dragSourceStageIdRef.current !== stage.id);

              return (
                <div
                  key={stage.id}
                  className={`kanban-column ${isOverTarget && isDraggingCardFromOtherStage ? "drag-over" : ""}`}
                  onDragOver={(e) => handleDragOver(e, stage.id)}
                  onDrop={(e) => handleDrop(e, stage)}
                  style={{
                    width: "310px",
                    flexShrink: 0,
                    background: "var(--bg-surface)",
                    border: "1px solid var(--border-subtle)",
                    borderRadius: "12px",
                    padding: "14px",
                    display: "flex",
                    flexDirection: "column",
                    maxHeight: "82vh",
                    boxShadow: "var(--shadow-sm)",
                  }}
                >
                  {/* Column Stage Header */}
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      paddingBottom: "12px",
                      marginBottom: "12px",
                      borderBottom: "1px solid var(--border-subtle)",
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <div
                        style={{
                          width: "10px",
                          height: "10px",
                          borderRadius: "50%",
                          backgroundColor: stage.color || "var(--primary)",
                        }}
                      />
                      <h3
                        style={{
                          fontSize: "0.8125rem",
                          fontWeight: 700,
                          color: "var(--text-primary)",
                          textTransform: "uppercase",
                          letterSpacing: "0.03em",
                        }}
                      >
                        {stage.name}
                      </h3>
                      <span
                        style={{
                          fontSize: "0.6875rem",
                          fontWeight: 700,
                          padding: "2px 7px",
                          borderRadius: "999px",
                          background: "var(--bg-surface-subtle)",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {stageLeads.length}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <button
                        type="button"
                        onClick={() => handleOpenEditStage(stage)}
                        title={`Edit "${stage.name}" stage`}
                        style={{
                          background: "none",
                          border: "1px solid var(--border-subtle)",
                          cursor: "pointer",
                          color: "var(--text-secondary)",
                          padding: "3px 7px",
                          borderRadius: "5px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "0.6875rem",
                          fontWeight: 600,
                          transition: "all 0.15s ease",
                        }}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.borderColor = "var(--primary)";
                          e.currentTarget.style.color = "var(--primary)";
                          e.currentTarget.style.backgroundColor = "var(--primary-light)";
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.borderColor = "var(--border-subtle)";
                          e.currentTarget.style.color = "var(--text-secondary)";
                          e.currentTarget.style.backgroundColor = "transparent";
                        }}
                      >
                        <Pencil style={{ width: "11px", height: "11px" }} />
                        <span>Edit</span>
                      </button>
                      <span
                        style={{
                          fontSize: "0.75rem",
                          fontFamily: "monospace",
                          fontWeight: 700,
                          color: "var(--text-secondary)",
                        }}
                      >
                        {formatRevenue(totalValue)}
                      </span>
                    </div>
                  </div>

                  {/* Cards Container */}
                  <div
                    style={{
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                      overflowY: "auto",
                      paddingRight: "2px",
                      flex: 1,
                      minHeight: "140px",
                    }}
                  >
                    {stageLeads.length === 0 ? (
                      <div
                        style={{
                          textAlign: "center",
                          padding: "32px 12px",
                          fontSize: "0.75rem",
                          color: "var(--text-muted)",
                          fontStyle: "italic",
                          display: "flex",
                          flexDirection: "column",
                          alignItems: "center",
                          gap: "6px",
                        }}
                      >
                        {isOverTarget && isDraggingCardFromOtherStage ? (
                          <div className="kanban-drop-indicator" style={{ width: "100%" }}>
                            <ArrowDown style={{ width: "14px", height: "14px" }} />
                            <span>Drop lead into {stage.name}</span>
                          </div>
                        ) : (
                          <span>Drop leads here from Partition 1</span>
                        )}
                      </div>
                    ) : (
                      <>
                        {stageLeads.map((lead) => {
                          const isBeingDragged = draggingLeadId === lead.id;

                          return (
                            <div
                              key={lead.id}
                              draggable={true}
                              onDragStart={(e) => handleDragStart(e, lead, stage.id)}
                              onDragEnd={handleDragEnd}
                              onClick={() => handleCardClick(lead)}
                              className={`kanban-card ${isBeingDragged ? "is-dragging" : ""}`}
                              title="Click to view details, or drag to advance stage"
                              style={{
                                padding: "14px",
                                background: "var(--bg-surface)",
                                border: "1px solid var(--border-subtle)",
                                borderRadius: "10px",
                                boxShadow: "var(--shadow-xs)",
                                position: "relative",
                              }}
                              onMouseOver={(e) => {
                                if (!isBeingDragged) {
                                  e.currentTarget.style.boxShadow = "var(--shadow-md)";
                                  e.currentTarget.style.borderColor = "var(--primary-border)";
                                  e.currentTarget.style.transform = "translateY(-1px)";
                                }
                              }}
                              onMouseOut={(e) => {
                                if (!isBeingDragged) {
                                  e.currentTarget.style.boxShadow = "var(--shadow-xs)";
                                  e.currentTarget.style.borderColor = "var(--border-subtle)";
                                  e.currentTarget.style.transform = "translateY(0)";
                                }
                              }}
                            >
                              {/* Priority, Score & Drag Handle */}
                              <div
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  justifyContent: "space-between",
                                  marginBottom: "8px",
                                }}
                              >
                                <span
                                  className={`badge ${
                                    lead.priority === "URGENT" || lead.priority === "HIGH"
                                      ? "badge-hot"
                                      : "badge-medium"
                                  }`}
                                >
                                  {lead.priority}
                                </span>

                                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "4px",
                                      fontSize: "0.75rem",
                                      fontFamily: "monospace",
                                      fontWeight: 700,
                                      color: "var(--amber-dark)",
                                    }}
                                  >
                                    <Flame style={{ width: "13px", height: "13px", color: "var(--amber)" }} />
                                    {lead.score}
                                  </div>

                                  <div
                                    style={{ color: "var(--text-muted)", display: "flex", alignItems: "center" }}
                                    title="Drag card to move stage"
                                  >
                                    <GripVertical style={{ width: "14px", height: "14px" }} />
                                  </div>
                                </div>
                              </div>

                              {/* Title */}
                              <h4
                                style={{
                                  fontSize: "0.8125rem",
                                  fontWeight: 700,
                                  color: "var(--text-primary)",
                                  marginBottom: "4px",
                                  lineHeight: "1.35",
                                }}
                              >
                                {lead.title}
                              </h4>

                              {/* Company & Contact */}
                              <div
                                style={{
                                  fontSize: "0.75rem",
                                  color: "var(--text-secondary)",
                                  marginBottom: "10px",
                                  display: "flex",
                                  flexDirection: "column",
                                  gap: "2px",
                                }}
                              >
                                {lead.company_name && (
                                  <p style={{ fontWeight: 600, color: "var(--text-primary)" }}>{lead.company_name}</p>
                                )}
                                {lead.contact_name && <p style={{ color: "var(--text-secondary)" }}>{lead.contact_name}</p>}
                              </div>

                              {/* Deal Value */}
                              {lead.value && Number(lead.value) > 0 && (
                                <div
                                  style={{
                                    marginBottom: "8px",
                                    fontSize: "0.75rem",
                                    fontWeight: 700,
                                    color: "var(--emerald)",
                                    fontFamily: "monospace",
                                  }}
                                >
                                  Deal Value: {formatRevenue(Number(lead.value))}
                                </div>
                              )}

                              {/* Contact Indicators & Gmail Trigger */}
                              {(lead.contact_phone || lead.contact_email) && (
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "space-between",
                                    paddingTop: "8px",
                                    borderTop: "1px solid var(--border-subtle)",
                                    fontSize: "0.6875rem",
                                    color: "var(--text-secondary)",
                                    flexWrap: "wrap",
                                    gap: "6px",
                                  }}
                                >
                                  {lead.contact_phone && (
                                    <a
                                      href={lead.is_phone_masked ? undefined : getCallUrl(lead.contact_phone)}
                                      onClick={(e) => {
                                        if (lead.is_phone_masked) e.preventDefault();
                                        else e.stopPropagation();
                                      }}
                                      title={lead.is_phone_masked ? "Masked Phone" : `Click to call (+91 ${format10DigitPhone(lead.contact_phone)})`}
                                      style={{ display: "inline-flex", alignItems: "center", gap: "4px", color: "inherit", textDecoration: "none" }}
                                    >
                                      <Phone style={{ width: "12px", height: "12px", color: "var(--emerald)" }} />
                                      <span>{format10DigitPhone(lead.contact_phone)}</span>
                                    </a>
                                  )}

                                  {lead.contact_email && (
                                    <button
                                      type="button"
                                      draggable={false}
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleCopyEmail(lead.contact_email!, lead.id);
                                      }}
                                      title="Copy email to clipboard"
                                      style={{
                                        background: "var(--bg-surface-subtle)",
                                        border: "1px solid var(--border-subtle)",
                                        borderRadius: "4px",
                                        padding: "2px 6px",
                                        color: "#dc2626",
                                        cursor: "pointer",
                                        display: "inline-flex",
                                        alignItems: "center",
                                        gap: "3px",
                                        fontSize: "0.6875rem",
                                      }}
                                    >
                                      <Mail style={{ width: "10px", height: "10px", color: "#dc2626" }} />
                                      <span>{copiedEmailId === lead.id ? "Copied!" : "Email"}</span>
                                    </button>
                                  )}
                                </div>
                              )}

                              {/* Advance stage button */}
                              {idx < visibleStages.length - 1 && (
                                <div
                                  style={{
                                    marginTop: "10px",
                                    paddingTop: "8px",
                                    borderTop: "1px solid var(--border-subtle)",
                                    display: "flex",
                                    justifyContent: "flex-end",
                                  }}
                                >
                                  <button
                                    draggable={false}
                                    onClick={(e) => {
                                      e.stopPropagation();
                                      onMoveStage(lead.id, visibleStages[idx + 1].id);
                                    }}
                                    title={`Advance to ${visibleStages[idx + 1].name}`}
                                    style={{
                                      fontSize: "0.6875rem",
                                      fontWeight: 600,
                                      color: "var(--primary)",
                                      background: "var(--primary-light)",
                                      border: "1px solid var(--primary-border)",
                                      borderRadius: "6px",
                                      padding: "3px 8px",
                                      cursor: "pointer",
                                      display: "inline-flex",
                                      alignItems: "center",
                                      gap: "4px",
                                      transition: "all 0.15s ease",
                                    }}
                                  >
                                    <span>Move to {visibleStages[idx + 1].name}</span>
                                    <ArrowRight style={{ width: "12px", height: "12px" }} />
                                  </button>
                                </div>
                              )}
                            </div>
                          );
                        })}

                        {/* Active Drag Drop Target */}
                        {isOverTarget && isDraggingCardFromOtherStage && (
                          <div className="kanban-drop-indicator">
                            <ArrowDown style={{ width: "14px", height: "14px" }} />
                            <span>Drop lead into {stage.name}</span>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* =========================================================================
          ADD CUSTOM STAGE MODAL
         ========================================================================= */}
      {showAddStageModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.45)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px",
          }}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              borderRadius: "14px",
              border: "1px solid var(--border-subtle)",
              boxShadow: "var(--shadow-xl)",
              width: "100%",
              maxWidth: "460px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div
                  style={{
                    width: "32px",
                    height: "32px",
                    borderRadius: "8px",
                    backgroundColor: "var(--primary-light)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--primary)",
                  }}
                >
                  <Plus style={{ width: "18px", height: "18px" }} />
                </div>
                <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  Add Custom Stage
                </h3>
              </div>
              <button
                onClick={() => setShowAddStageModal(false)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X style={{ width: "18px", height: "18px" }} />
              </button>
            </div>

            {stageError && (
              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: "6px",
                  backgroundColor: "var(--rose-light)",
                  border: "1px solid var(--rose-border)",
                  color: "var(--rose-dark)",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                }}
              >
                {stageError}
              </div>
            )}

            <form onSubmit={handleCreateCustomStage} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Technical Evaluation, Demo Scheduled"
                  value={newStageName}
                  onChange={(e) => setNewStageName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-medium)",
                    fontSize: "0.8125rem",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Color Accent
                </label>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {STAGE_COLORS.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setNewStageColor(c.value)}
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        backgroundColor: c.value,
                        border: newStageColor === c.value ? "3px solid #0f172a" : "1px solid var(--border-subtle)",
                        cursor: "pointer",
                        boxShadow: newStageColor === c.value ? "0 0 0 2px var(--primary-light)" : "none",
                      }}
                      title={c.label}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Win Probability (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={newStageProbability}
                  onChange={(e) => setNewStageProbability(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-medium)",
                    fontSize: "0.8125rem",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Outcome Type
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  {[
                    { key: "STANDARD", label: "Standard Pipeline Stage" },
                    { key: "WON", label: "Won Stage" },
                    { key: "LOST", label: "Lost Stage" },
                  ].map((t) => (
                    <button
                      key={t.key}
                      type="button"
                      onClick={() => setNewStageType(t.key as any)}
                      style={{
                        flex: 1,
                        padding: "6px 10px",
                        borderRadius: "6px",
                        border: newStageType === t.key ? "1px solid var(--primary)" : "1px solid var(--border-subtle)",
                        backgroundColor: newStageType === t.key ? "var(--primary-light)" : "var(--bg-surface-subtle)",
                        color: newStageType === t.key ? "var(--primary)" : "var(--text-secondary)",
                        fontSize: "0.6875rem",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddStageModal(false)}
                  className="btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "8px 14px" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creatingStage}
                  className="btn-primary"
                  style={{ fontSize: "0.75rem", padding: "8px 18px" }}
                >
                  {creatingStage ? "Creating..." : "Save Custom Stage"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Existing Stage Modal */}
      {editingStage && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: "rgba(15, 23, 42, 0.6)",
            backdropFilter: "blur(4px)",
            zIndex: 9999,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
          onClick={(e) => {
            if (e.target === e.currentTarget) setEditingStage(null);
          }}
        >
          <div
            style={{
              backgroundColor: "var(--bg-surface)",
              borderRadius: "14px",
              border: "1px solid var(--border-medium)",
              padding: "24px",
              width: "100%",
              maxWidth: "480px",
              boxShadow: "var(--shadow-xl)",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                  Edit Pipeline Stage
                </h3>
                <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Modify stage name, outcome type, probability, or switch stage role.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setEditingStage(null)}
                style={{
                  background: "none",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "4px",
                }}
              >
                <X style={{ width: "18px", height: "18px" }} />
              </button>
            </div>

            {editStageError && (
              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: "6px",
                  backgroundColor: "var(--rose-light)",
                  border: "1px solid var(--rose-border)",
                  color: "var(--rose-dark)",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                }}
              >
                {editStageError}
              </div>
            )}

            {/* Quick Stage Presets */}
            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
                Quick Presets (1-Click Change)
              </label>
              <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
                {STAGE_PRESETS.map((p) => (
                  <button
                    key={p.name}
                    type="button"
                    onClick={() => applyEditPreset(p)}
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "4px",
                      padding: "4px 8px",
                      borderRadius: "6px",
                      border: editStageName.toLowerCase() === p.name.toLowerCase() ? `1px solid ${p.color}` : "1px solid var(--border-subtle)",
                      backgroundColor: editStageName.toLowerCase() === p.name.toLowerCase() ? "var(--bg-surface-subtle)" : "transparent",
                      color: editStageName.toLowerCase() === p.name.toLowerCase() ? p.color : "var(--text-secondary)",
                      fontSize: "0.6875rem",
                      fontWeight: 600,
                      cursor: "pointer",
                    }}
                  >
                    <div style={{ width: "6px", height: "6px", borderRadius: "50%", backgroundColor: p.color }} />
                    {p.name}
                  </button>
                ))}
              </div>
            </div>

            <form onSubmit={handleSaveEditStage} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Lost, Closed Won, Follow Up"
                  value={editStageName}
                  onChange={(e) => setEditStageName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-medium)",
                    fontSize: "0.8125rem",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Code
                </label>
                <input
                  type="text"
                  placeholder="e.g. LOST, NEW, WON"
                  value={editStageCode}
                  onChange={(e) => setEditStageCode(e.target.value.toUpperCase())}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-medium)",
                    fontSize: "0.8125rem",
                    fontFamily: "monospace",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Color Accent
                </label>
                <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                  {STAGE_COLORS.map((c) => (
                    <button
                      key={c.value}
                      type="button"
                      onClick={() => setEditStageColor(c.value)}
                      style={{
                        width: "28px",
                        height: "28px",
                        borderRadius: "50%",
                        backgroundColor: c.value,
                        border: editStageColor === c.value ? "3px solid #0f172a" : "1px solid var(--border-subtle)",
                        cursor: "pointer",
                        boxShadow: editStageColor === c.value ? "0 0 0 2px var(--primary-light)" : "none",
                      }}
                      title={c.label}
                    />
                  ))}
                </div>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Win Probability (%)
                </label>
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={editStageProbability}
                  onChange={(e) => setEditStageProbability(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: "1px solid var(--border-medium)",
                    fontSize: "0.8125rem",
                    outline: "none",
                  }}
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Stage Outcome Type
                </label>
                <div style={{ display: "flex", gap: "8px" }}>
                  {[
                    { key: "STANDARD", label: "Standard Pipeline Stage" },
                    { key: "WON", label: "Won Stage" },
                    { key: "LOST", label: "Lost Stage" },
                  ].map((t) => (
                    <button
                      key={t.key}
                      type="button"
                      onClick={() => setEditStageType(t.key as any)}
                      style={{
                        flex: 1,
                        padding: "6px 10px",
                        borderRadius: "6px",
                        border: editStageType === t.key ? "1px solid var(--primary)" : "1px solid var(--border-subtle)",
                        backgroundColor: editStageType === t.key ? "var(--primary-light)" : "var(--bg-surface-subtle)",
                        color: editStageType === t.key ? "var(--primary)" : "var(--text-secondary)",
                        fontSize: "0.6875rem",
                        fontWeight: 600,
                        cursor: "pointer",
                      }}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setEditingStage(null)}
                  className="btn-secondary"
                  style={{ fontSize: "0.75rem", padding: "8px 14px" }}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={updatingStage}
                  className="btn-primary"
                  style={{ fontSize: "0.75rem", padding: "8px 18px" }}
                >
                  {updatingStage ? "Saving..." : "Save Stage Changes"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}


    </div>
  );
};
