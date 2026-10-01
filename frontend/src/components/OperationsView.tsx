import React, { useState, useEffect } from "react";
import { api, JobRun } from "../services/api";
import { ActivitySquare, Database, Server, Clock, AlertTriangle, CheckCircle, XCircle } from "lucide-react";

export const OperationsView: React.FC = () => {
  const [health, setHealth] = useState<any>(null);
  const [jobs, setJobs] = useState<JobRun[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const fetchData = async () => {
    try {
      const [healthRes, jobsRes] = await Promise.all([
        api.getSystemHealth(),
        api.getJobs()
      ]);
      setHealth(healthRes);
      setJobs(jobsRes || []);
    } catch (e) {
      console.error("Operations fetch failed:", e);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "healthy":
      case "connected":
      case "SUCCESS":
        return "var(--success)";
      case "degraded":
      case "STARTED":
        return "var(--warning)";
      default:
        return "var(--danger)";
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto", padding: "24px 0" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
            <ActivitySquare style={{ width: "24px", height: "24px", color: "var(--primary)" }} />
            System Operations
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "4px" }}>
            Real-time infrastructure health and background job execution monitor.
          </p>
        </div>
      </div>

      {loading && !health ? (
        <div style={{ textAlign: "center", padding: "40px", color: "var(--text-secondary)" }}>Loading Operations Data...</div>
      ) : (
        <>
          {/* Health Widgets */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "24px", marginBottom: "32px" }}>
            <div className="card" style={{ padding: "24px", display: "flex", alignItems: "center", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(79,70,229,0.1)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <ActivitySquare style={{ width: "24px", height: "24px" }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 700, textTransform: "uppercase" }}>Overall Status</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: getStatusColor(health?.status) }}>
                  {health?.status.toUpperCase()}
                </div>
              </div>
            </div>

            <div className="card" style={{ padding: "24px", display: "flex", alignItems: "center", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(16,185,129,0.1)", color: "var(--success)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Database style={{ width: "24px", height: "24px" }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 700, textTransform: "uppercase" }}>PostgreSQL Database</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: getStatusColor(health?.database) }}>
                  {health?.database.toUpperCase()}
                </div>
              </div>
            </div>

            <div className="card" style={{ padding: "24px", display: "flex", alignItems: "center", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "rgba(239,68,68,0.1)", color: "var(--danger)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                <Server style={{ width: "24px", height: "24px" }} />
              </div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 700, textTransform: "uppercase" }}>Redis Message Broker</div>
                <div style={{ fontSize: "1.25rem", fontWeight: 800, color: getStatusColor(health?.redis_broker) }}>
                  {health?.redis_broker.toUpperCase()}
                </div>
              </div>
            </div>
          </div>

          {/* Job Monitor Table */}
          <h3 style={{ fontSize: "1.25rem", fontWeight: 800, marginBottom: "16px" }}>Background Execution Tracker</h3>
          <div className="card table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Job Type</th>
                  <th>Task ID</th>
                  <th>Status</th>
                  <th>Started At</th>
                  <th>Duration</th>
                </tr>
              </thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td style={{ fontWeight: 600 }}>{job.job_type}</td>
                    <td><code style={{ fontSize: "0.75rem", color: "var(--text-tertiary)" }}>{job.job_id.substring(0, 12)}...</code></td>
                    <td>
                      <span style={{ 
                        display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", fontWeight: 700, 
                        color: getStatusColor(job.status) 
                      }}>
                        {job.status === "SUCCESS" && <CheckCircle style={{ width: "14px", height: "14px" }} />}
                        {job.status === "FAILED" && <XCircle style={{ width: "14px", height: "14px" }} />}
                        {job.status === "STARTED" && <ActivitySquare style={{ width: "14px", height: "14px" }} />}
                        {job.status}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                      {new Date(job.started_at).toLocaleString()}
                    </td>
                    <td style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>
                      {job.duration_seconds !== null ? `${job.duration_seconds}s` : "-"}
                    </td>
                  </tr>
                ))}
                {jobs.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
                      No recent jobs found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
};
