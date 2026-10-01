import React, { useState } from "react";
import { api, ImportJob } from "../services/api";
import {
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  FileText,
  ArrowRight,
  X,
  Download,
  Info,
  Building2,
  UserCheck,
  Check
} from "lucide-react";

interface ImportModalProps {
  jobType?: "TENANT_LEADS" | "GLOBAL_COMPANIES" | "GLOBAL_PEOPLE";
  onClose: () => void;
  onSuccess: () => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ jobType = "TENANT_LEADS", onClose, onSuccess }) => {
  const [step, setStep] = useState<"upload" | "mapping" | "processing" | "complete">("upload");
  const [, setSelectedFile] = useState<File | null>(null);
  const [previewData, setPreviewData] = useState<any>(null);
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [activeJob, setActiveJob] = useState<ImportJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formatWarning, setFormatWarning] = useState<string | null>(null);
  const [isDraggingOver, setIsDraggingOver] = useState(false);
  const [productServices, setProductServices] = useState<any[]>([]);
  const [defaultProductServiceId, setDefaultProductServiceId] = useState<string>("");

  React.useEffect(() => {
    if (jobType === "TENANT_LEADS") {
      api.getProductServices(true).then(setProductServices).catch(() => {});
    }
  }, [jobType]);

  const SYSTEM_FIELDS = [
    { value: "ignore", label: "— Ignore Column —" },
    { value: "company_name", label: "Company Name" },
    { value: "id", label: "Company ID (UUID from our side)" },
    { value: "cin", label: "CIN (Corporate Identification Number)" },
    { value: "registration_number", label: "Registration Number" },
    { value: "gst_number", label: "GST Number" },
    { value: "address", label: "Address" },
    { value: "city", label: "City" },
    { value: "postal_code", label: "Pincode / Postal Code" },
    { value: "state", label: "State" },
    { value: "website", label: "Website" },
    { value: "contact_email", label: "Email ID" },
    { value: "contact_phone", label: "Company Contact Number / Mobile" },
    { value: "contact_name", label: "Name (Person / Contact Name)" },
    { value: "associated_companies", label: "Associated Companies (Multiple)" },
    { value: "designation", label: "Designation with Each Company" },
    { value: "industry", label: "Industry / Sector" },
    { value: "seniority", label: "Seniority (C-Level, Director, etc.)" },
    { value: "department", label: "Department (Eng, Sales, etc.)" },
    { value: "linkedin_url", label: "LinkedIn Profile URL" },
    { value: "value", label: "Estimated Opportunity Value (₹)" },
    { value: "title", label: "Opportunity Title" },
    { value: "product_service", label: "Product/Service Name" },
    { value: "purpose", label: "Lead/Call Purpose" },
    { value: "notes", label: "Notes / Persona Bio" },
  ];

  // Column Guides per Job Type
  const getNeededColumnsGuide = () => {
    if (jobType === "GLOBAL_COMPANIES") {
      return {
        title: "Company Intelligence Needed Columns",
        required: [
          { field: "company_name", label: "Company Name", note: "Primary legal or trade name (e.g. Acme Technologies Pvt Ltd)" }
        ],
        recommended: [
          { field: "id", label: "id", note: "Unique UUID from our side (auto-generated if empty)" },
          { field: "cin", label: "CIN", note: "Corporate Identification Number (e.g. U72200MH2020PTC123456)" },
          { field: "registration_number", label: "Registration Number", note: "Company registration or incorporation number" },
          { field: "gst_number", label: "GST Number", note: "15-digit GSTIN (e.g. 27AAAAA0000A1Z5)" },
          { field: "address", label: "Address", note: "Street, office suite, or premises" },
          { field: "city", label: "City", note: "e.g. Pune, Mumbai, Bengaluru" },
          { field: "pincode", label: "Pincode", note: "6-digit postal code (e.g. 411001)" },
          { field: "state", label: "State", note: "e.g. Maharashtra, Karnataka" },
          { field: "website", label: "Website", note: "e.g. https://acme.com" },
          { field: "email", label: "Email", note: "Official corporate contact email" },
          { field: "company_contact_number", label: "Company Contact Number", note: "Official telephone/mobile number" },
          { field: "industry", label: "Industry", note: "e.g. IT, Manufacturing, BFSI" }
        ],
        sampleFileName: "company_intelligence_sample_template.csv",
        sampleContent: `company_name,id,cin,registration_number,gst_number,address,city,pincode,state,website,email,company_contact_number,industry
Tata Advanced Systems Ltd,,U72200MH2015PLC123456,REG-847291,27AAACT1234A1Z1,Plot 42 Hinjewadi Phase 1,Pune,411057,Maharashtra,https://tataadvanced.com,contact@tataadvanced.com,+912012345678,Aerospace & Defense
Acme Infotech Pvt Ltd,,U72900KA2018PTC987654,REG-109283,29AABCA9876B1Z2,100 Feet Road Indiranagar,Bengaluru,560038,Karnataka,https://acmeinfo.in,info@acmeinfo.in,+918098765432,Information Technology`,
        sampleJsonFileName: "company_intelligence_sample_template.json",
        sampleJsonContent: JSON.stringify([
          {
            "company_name": "Tata Advanced Systems Ltd",
            "cin": "U72200MH2015PLC123456",
            "registration_number": "REG-847291",
            "gst_number": "27AAACT1234A1Z1",
            "address": "Plot 42 Hinjewadi Phase 1",
            "city": "Pune",
            "postal_code": "411057",
            "state": "Maharashtra",
            "website": "https://tataadvanced.com",
            "contact_email": "contact@tataadvanced.com",
            "contact_phone": "+912012345678",
            "industry": "Aerospace & Defense"
          },
          {
            "company_name": "Acme Infotech Pvt Ltd",
            "cin": "U72900KA2018PTC987654",
            "registration_number": "REG-109283",
            "gst_number": "29AABCA9876B1Z2",
            "address": "100 Feet Road Indiranagar",
            "city": "Bengaluru",
            "postal_code": "560038",
            "state": "Karnataka",
            "website": "https://acmeinfo.in",
            "contact_email": "info@acmeinfo.in",
            "contact_phone": "+918098765432",
            "industry": "Information Technology"
          }
        ], null, 2)
      };
    }

    if (jobType === "GLOBAL_PEOPLE") {
      return {
        title: "People Intelligence Needed Columns",
        required: [
          { field: "name", label: "Name", note: "Full name of executive or lead (e.g. Rajesh Sharma)" }
        ],
        recommended: [
          { field: "mobile", label: "Mobile", note: "Phone number with country code (e.g. +91 98765 43210)" },
          { field: "email_id", label: "Email ID", note: "Personal or work email (e.g. rajesh@tata.com)" },
          { field: "associated_companies", label: "Associated Companies", note: "Single or multiple companies (e.g. 'Tata Advanced Systems, Infosys Ltd')" },
          { field: "designation_with_each_company", label: "Designation with each company", note: "Roles with companies (e.g. 'Director (Tata), Advisor (Infosys)')" },
          { field: "industry", label: "Industry", note: "e.g. Defense, Technology, FinTech" },
          { field: "city", label: "City", note: "e.g. Pune, Mumbai, Delhi" },
          { field: "state", label: "State", note: "e.g. Maharashtra, Karnataka" },
          { field: "linkedin_url", label: "LinkedIn URL", note: "Profile link" }
        ],
        sampleFileName: "people_intelligence_sample_template.csv",
        sampleContent: `name,mobile,email_id,associated_companies,designation_with_each_company,industry,city,state
Rajesh Sharma,+919876543210,rajesh.sharma@tata.com,Tata Advanced Systems,VP of Supply Chain,Aerospace & Defense,Pune,Maharashtra
Sunita Verma,+919812345678,sunita.verma@apex.in,"Apex Health, BioPharma Labs","Board Director (Apex Health), Strategic Advisor (BioPharma Labs)",Healthcare,Mumbai,Maharashtra`,
        sampleJsonFileName: "people_intelligence_sample_template.json",
        sampleJsonContent: JSON.stringify([
          {
            "contact_name": "Rajesh Sharma",
            "contact_phone": "+919876543210",
            "contact_email": "rajesh.sharma@tata.com",
            "associated_companies": "Tata Advanced Systems",
            "designation": "VP of Supply Chain",
            "industry": "Aerospace & Defense",
            "city": "Pune",
            "state": "Maharashtra"
          },
          {
            "contact_name": "Sunita Verma",
            "contact_phone": "+919812345678",
            "contact_email": "sunita.verma@apex.in",
            "associated_companies": "Apex Health, BioPharma Labs",
            "designation": "Board Director",
            "industry": "Healthcare",
            "city": "Mumbai",
            "state": "Maharashtra"
          }
        ], null, 2)
      };
    }

    return {
      title: "CRM Leads Ingestion Needed Columns",
      required: [
        { field: "name_or_company", label: "Contact Name OR Company Name", note: "At least one identifier required per lead row" }
      ],
      recommended: [
        { field: "contact_name", label: "Contact Name", note: "Decision maker name" },
        { field: "company_name", label: "Company Name", note: "Account or business name" },
        { field: "contact_email", label: "Work Email", note: "Email address" },
        { field: "contact_phone", label: "Mobile / Phone", note: "Contact number" },
        { field: "designation", label: "Designation", note: "Role or title" },
        { field: "city", label: "City", note: "Location" },
        { field: "product_service", label: "Product/Service", note: "Mapped to catalog" },
        { field: "purpose", label: "Purpose", note: "Reason for lead" },
        { field: "value", label: "Value (₹)", note: "Opportunity budget" }
      ],
      sampleFileName: "crm_leads_sample_template.csv",
      sampleContent: `contact_name,company_name,designation,contact_email,contact_phone,city,product_service,purpose,value
Vikram Mehta,Mehta Logistics Pvt Ltd,Managing Director,vikram@mehtalogistics.in,+919822011223,Pune,Premium Tech Support,Renew Contract,500000
Pooja Kulkarni,Kulkarni Engineering,Head of Purchasing,pooja@kulkarnieng.com,+919823344556,Nashik,Software License,New Inquiry,350000`,
      sampleJsonFileName: "crm_leads_sample_template.json",
      sampleJsonContent: JSON.stringify([
        {
          "contact_name": "Vikram Mehta",
          "company_name": "Mehta Logistics Pvt Ltd",
          "designation": "Managing Director",
          "contact_email": "vikram@mehtalogistics.in",
          "contact_phone": "+919822011223",
          "city": "Pune",
          "product_service": "Premium Tech Support",
          "purpose": "Renew Contract",
          "value": 500000
        },
        {
          "contact_name": "Pooja Kulkarni",
          "company_name": "Kulkarni Engineering",
          "designation": "Head of Purchasing",
          "contact_email": "pooja@kulkarnieng.com",
          "contact_phone": "+919823344556",
          "city": "Nashik",
          "product_service": "Software License",
          "purpose": "New Inquiry",
          "value": 350000
        }
      ], null, 2)
    };
  };

  const guide = getNeededColumnsGuide();

  const handleDownloadSample = () => {
    const blob = new Blob([guide.sampleContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", guide.sampleFileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const handleDownloadSampleJson = () => {
    const blob = new Blob([guide.sampleJsonContent], { type: "application/json;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", guide.sampleJsonFileName);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const VALID_TABULAR_EXTENSIONS = [".csv", ".xls", ".xlsx", ".xlsb", ".xlsm", ".parquet", ".json"];

  const validateAndProcessFile = async (file: File) => {
    setFormatWarning(null);
    setError(null);

    const ext = file.name ? file.name.substring(file.name.lastIndexOf(".")).toLowerCase() : "";
    if (!VALID_TABULAR_EXTENSIONS.includes(ext)) {
      const detectedFormat = ext ? ext.replace(".", "").toUpperCase() : "NON-TABULAR";
      setFormatWarning(
        `Invalid file format (${detectedFormat}): "${file.name}". Data ingestion exclusively supports tabular files (.CSV, .XLS, .XLSX, .XLSB, .XLSM, .PARQUET, .JSON). Non-tabular formats such as PDF, Word documents, Markdown (.md), or text files (.txt) cannot be processed into database columns and rows.`
      );
      return;
    }

    // SECURITY GUARDRAIL: Bulk Action Limits (Max ~5,000 rows / 5MB)
    const MAX_SIZE_MB = 5;
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      setFormatWarning(`File is too large (${(file.size / (1024*1024)).toFixed(1)}MB). Maximum allowed size is ${MAX_SIZE_MB}MB to prevent database lockups (approx. 5,000 rows). Please split your file into smaller batches and try again.`);
      return;
    }

    setSelectedFile(file);
    setLoading(true);
    try {
      const preview = await api.uploadImportFile(file);
      setPreviewData(preview);
      setColumnMapping(preview.suggested_mappings || {});
      setStep("mapping");
    } catch (err: any) {
      setError(err.message || "Failed to upload file");
    } finally {
      setLoading(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      validateAndProcessFile(e.target.files[0]);
      e.target.value = ""; // Reset file input so user can re-upload or re-select
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDraggingOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleStartImport = async () => {
    if (!previewData) return;
    setLoading(true);
    setError(null);
    try {
      const job = await api.executeImport({
        file_path: previewData.file_path,
        file_name: previewData.file_name,
        file_type: previewData.file_type,
        job_type: jobType,
        column_mapping: columnMapping,
        default_product_service_id: defaultProductServiceId || undefined,
      });
      setActiveJob(job);
      setStep("processing");
      pollJobStatus(job.id);
    } catch (err: any) {
      setError(err.message || "Failed to launch import execution");
    } finally {
      setLoading(false);
    }
  };

  const pollJobStatus = (jobId: string) => {
    const interval = setInterval(async () => {
      try {
        const job = await api.getImportJob(jobId);
        setActiveJob(job);
        if (job.status === "COMPLETED" || job.status === "PARTIAL" || job.status === "FAILED") {
          clearInterval(interval);
          setStep("complete");
          onSuccess();
        }
      } catch (e) {
        clearInterval(interval);
      }
    }, 1000);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "740px", maxHeight: "90vh", overflowY: "auto", padding: "24px" }}>
        {/* Header */}
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "14px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "16px" }}>
          <div>
            <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
              <UploadCloud style={{ width: "20px", height: "20px", color: "var(--primary)" }} />
              {jobType === "GLOBAL_PEOPLE"
                ? "People Intelligence Bulk Ingestion"
                : jobType === "GLOBAL_COMPANIES"
                ? "Company Intelligence Bulk Ingestion"
                : "Lead Ingestion Wizard"}
            </h3>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              {jobType === "GLOBAL_PEOPLE"
                ? "Bulk import executive profiles with multiple associated companies into global_people"
                : jobType === "GLOBAL_COMPANIES"
                ? "Bulk import enterprise companies with CIN, Registration No, GST, Pincode, and address"
                : "Bulk import leads with automated duplicate detection and pipeline immutability"}
            </p>
          </div>
          <button onClick={onClose} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}>
            <X style={{ width: "20px", height: "20px" }} />
          </button>
        </div>

        {error && (
          <div style={{
            marginBottom: "16px",
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
            <AlertTriangle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        {/* Format Warning Alert */}
        {formatWarning && (
          <div
            style={{
              marginBottom: "16px",
              padding: "12px 14px",
              borderRadius: "8px",
              background: "#fffbeb",
              border: "1px solid #fde68a",
              color: "#92400e",
              display: "flex",
              flexDirection: "column",
              gap: "6px"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", fontWeight: 700, fontSize: "0.8125rem" }}>
                <AlertTriangle style={{ width: "16px", height: "16px", color: "#d97706", flexShrink: 0 }} />
                <span>Unsupported File Format</span>
              </div>
              <button
                type="button"
                onClick={() => setFormatWarning(null)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "#92400e", padding: "2px" }}
              >
                <X style={{ width: "14px", height: "14px" }} />
              </button>
            </div>
            <p style={{ fontSize: "0.75rem", margin: 0, lineHeight: 1.4 }}>{formatWarning}</p>
            <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "4px", flexWrap: "wrap" }}>
              <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "#b45309" }}>Valid Tabular Formats:</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.CSV</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.XLS</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.XLSX</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.XLSB</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.XLSM</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.PARQUET</span>
              <span style={{ fontSize: "0.6875rem", padding: "1px 6px", borderRadius: "4px", backgroundColor: "#fef3c7", border: "1px solid #fcd34d", fontWeight: 700, fontFamily: "monospace" }}>.JSON</span>
            </div>
          </div>
        )}

        {/* Step 1: Upload File with Needed Columns Guide */}
        {step === "upload" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {/* Needed Columns Guide Box */}
            <div style={{
              background: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              borderRadius: "12px",
              padding: "16px",
              display: "flex",
              flexDirection: "column",
              gap: "12px"
            }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "8px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Info style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
                  <span style={{ fontSize: "0.8125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                    {guide.title}
                  </span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                  <button
                    type="button"
                    onClick={handleDownloadSample}
                    className="btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "4px 10px", gap: "6px" }}
                    id="download-sample-csv-btn"
                  >
                    <Download style={{ width: "13px", height: "13px" }} />
                    Download Sample (.CSV)
                  </button>
                  <button
                    type="button"
                    onClick={handleDownloadSampleJson}
                    className="btn-secondary"
                    style={{ fontSize: "0.75rem", padding: "4px 10px", gap: "6px" }}
                    id="download-sample-json-btn"
                  >
                    <Download style={{ width: "13px", height: "13px" }} />
                    Download Sample (.JSON)
                  </button>
                </div>
              </div>

              {/* Required Columns */}
              <div>
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--rose-dark)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Required Columns (At least one needed to prevent invalid rows)
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "4px" }}>
                  {guide.required.map((r, i) => (
                    <div key={i} style={{ background: "var(--rose-light)", border: "1px solid var(--rose-border)", borderRadius: "6px", padding: "4px 8px", fontSize: "0.6875rem" }}>
                      <strong style={{ color: "var(--rose-dark)" }}>{r.label}</strong>
                      <span style={{ color: "var(--text-secondary)", marginLeft: "4px" }}>— {r.note}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Recommended Columns */}
              <div>
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--primary-dark)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Supported / Recommended Columns
                </span>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "6px", marginTop: "4px" }}>
                  {guide.recommended.map((r, i) => (
                    <div key={i} style={{ background: "var(--bg-surface)", border: "1px solid var(--border-subtle)", borderRadius: "6px", padding: "4px 8px", fontSize: "0.6875rem" }}>
                      <strong style={{ color: "var(--text-primary)" }}>{r.label}</strong>: <span style={{ color: "var(--text-muted)" }}>{r.note}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Drop Zone */}
            <div
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              style={{
                border: isDraggingOver ? "2px dashed var(--primary)" : "2px dashed var(--border-medium)",
                borderRadius: "12px",
                padding: "32px 20px",
                background: isDraggingOver ? "var(--primary-light)" : "var(--bg-surface-subtle)",
                cursor: "pointer",
                textAlign: "center",
                transition: "all 0.15s ease"
              }}
            >
              <UploadCloud style={{ width: "40px", height: "40px", color: isDraggingOver ? "var(--primary)" : "var(--primary)", margin: "0 auto 10px auto" }} />
              <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {isDraggingOver ? "Drop file here to upload" : "Drag & Drop or Click to select CSV, Excel, Parquet, or JSON file"}
              </p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-muted)", marginTop: "4px" }}>
                Auto-matches column names: company_name, id, address, city, pincode, state, website, email, company_contact_number, cin, gst_number, associated_companies, etc.
              </p>
              <input
                type="file"
                accept=".csv,.xls,.xlsx,.xlsb,.xlsm,.parquet,.json"
                onChange={handleFileChange}
                style={{ display: "none" }}
                id="file-upload-input"
              />
              <label htmlFor="file-upload-input" className="btn-primary" style={{ marginTop: "14px", display: "inline-flex", cursor: "pointer" }}>
                Select File from Disk
              </label>
            </div>
            {loading && <p style={{ fontSize: "0.75rem", color: "var(--primary)", fontWeight: 600, textAlign: "center" }}>Analyzing headers and auto-mapping columns...</p>}
          </div>
        )}

        {/* Step 2: Column Mapping */}
        {step === "mapping" && previewData && (() => {
          const headersList = previewData.headers || previewData.detected_headers || [];
          const sampleRowsList = previewData.preview_rows || previewData.sample_rows || [];
          const totalRows = previewData.total_rows_estimate || previewData.total_detected_rows || 0;

          return (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
                <div>
                  <p style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                    Verify & Confirm Ingestion Column Mappings
                  </p>
                  <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                    Detected {totalRows} rows in {previewData.file_name}. Columns have been auto-matched.
                  </p>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  {jobType === "TENANT_LEADS" && productServices.length > 0 && (
                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Default Product:</span>
                      <select 
                        className="select-dropdown" 
                        style={{ fontSize: "0.75rem", padding: "4px 8px" }}
                        value={defaultProductServiceId}
                        onChange={(e) => setDefaultProductServiceId(e.target.value)}
                      >
                        <option value="">-- Auto-detect from file --</option>
                        {productServices.map(ps => (
                          <option key={ps.id} value={ps.id}>{ps.name}</option>
                        ))}
                      </select>
                    </div>
                  )}
                  <span className="badge badge-medium">Auto-Mapped</span>
                </div>
              </div>

              <div style={{ maxHeight: "320px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "8px", paddingRight: "4px" }}>
                {headersList.map((hdr: string) => (
                  <div
                    key={hdr}
                    style={{
                      padding: "8px 12px",
                      borderRadius: "8px",
                      background: "var(--bg-surface-subtle)",
                      border: "1px solid var(--border-subtle)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px"
                    }}
                  >
                    <div style={{ flex: 1 }}>
                      <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", fontFamily: "monospace" }}>
                        {hdr}
                      </span>
                      {sampleRowsList[0] && (
                        <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>
                          Ex: {String(sampleRowsList[0][hdr] || "—").substring(0, 36)}
                        </span>
                      )}
                    </div>

                    <select
                      value={columnMapping[hdr] || "ignore"}
                      onChange={(e) => setColumnMapping({ ...columnMapping, [hdr]: e.target.value })}
                      className="select-dropdown"
                      style={{ width: "240px", fontSize: "0.75rem" }}
                    >
                      {SYSTEM_FIELDS.map((f) => (
                        <option key={f.value} value={f.value}>
                          {f.label}
                        </option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              <div style={{ paddingTop: "12px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <button onClick={() => setStep("upload")} className="btn-secondary">
                  Back
                </button>
                <button onClick={handleStartImport} disabled={loading} className="btn-primary" id="confirm-import-btn">
                  {loading ? "Starting..." : "Start Ingestion"}
                  <ArrowRight style={{ width: "14px", height: "14px" }} />
                </button>
              </div>
            </div>
          );
        })()}

        {/* Step 3: Ingestion Processing */}
        {step === "processing" && (
          <div style={{ textAlign: "center", padding: "36px 0", display: "flex", flexDirection: "column", gap: "16px" }}>
            <div className="radar-pulse-dot" style={{ width: "16px", height: "16px", margin: "0 auto" }} />
            <div>
              <h4 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Ingesting Records Asynchronously
              </h4>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                Normalizing identifiers, assigning UUIDs, isolating errors, and indexing profiles...
              </p>
            </div>
            {activeJob && activeJob.total_rows > 0 && (
              <div style={{ width: "100%", maxWidth: "400px", margin: "0 auto", marginTop: "12px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  <span>{activeJob.processed_rows} / {activeJob.total_rows} rows processed</span>
                  <span>{Math.round((activeJob.processed_rows / activeJob.total_rows) * 100)}%</span>
                </div>
                <div style={{ width: "100%", height: "8px", background: "var(--bg-surface-subtle)", borderRadius: "4px", overflow: "hidden" }}>
                  <div style={{ 
                    width: `${Math.round((activeJob.processed_rows / activeJob.total_rows) * 100)}%`, 
                    height: "100%", 
                    background: "var(--primary)", 
                    transition: "width 0.3s ease" 
                  }} />
                </div>
              </div>
            )}
          </div>
        )}

        {/* Step 4: Complete */}
        {step === "complete" && activeJob && (
          <div style={{ textAlign: "center", padding: "28px 0", display: "flex", flexDirection: "column", gap: "16px" }}>
            <div style={{ width: "48px", height: "48px", borderRadius: "50%", background: "var(--emerald-light)", color: "var(--emerald)", display: "flex", alignItems: "center", justifyContent: "center", margin: "0 auto" }}>
              <CheckCircle2 style={{ width: "28px", height: "28px" }} />
            </div>
            <div>
              <h4 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Import Completed
              </h4>
              <div style={{ display: "flex", justifyContent: "center", gap: "16px", marginTop: "12px", fontSize: "0.8125rem" }}>
                <span style={{ color: "var(--emerald-dark)", fontWeight: 700 }}>
                  ✓ {activeJob.successful_rows} Successful
                </span>
                <span style={{ color: "var(--text-muted)" }}>
                  • {activeJob.duplicate_rows} Duplicates
                </span>
                {activeJob.error_rows > 0 && (
                  <span style={{ color: "var(--rose)", fontWeight: 700 }}>
                    ✕ {activeJob.error_rows} Errors
                  </span>
                )}
              </div>
            </div>
            <div style={{ marginTop: "8px" }}>
              <button onClick={onClose} className="btn-primary">
                Done
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
