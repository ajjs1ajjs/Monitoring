import React from "react";
import DashboardLayout from "../components/DashboardLayout";
import ChartPanel from "../components/ChartPanel";
import { useMetrics, MetricsState } from "../hooks/useMetrics";

/**
 * Dashboard for checking metrics from a specified production exporter endpoint,
 * or falling back to the default configured endpoint if no URL is provided.
 */
const ProdCheckDashboard = () => {
  // Use the specific URL from window context if available, otherwise pass undefined
  // to let the hook fall back to its default configured endpoint.
  const prodUrl =
    (typeof window !== "undefined" && (window as any).__EXPORTER_PROD_URL__) ||
    undefined;

  // Cast useMetrics return type for clarity and safety in component usage
  const { cpu, memory, disk, network } = useMetrics(prodUrl, 5000);
  const status =
    cpu.length > 5
      ? "Online"
      : cpu.length === 0 && memory.length === 0
        ? "Unknown"
        : "Degraded";

  return (
    <DashboardLayout title="Prod Exporter Check" status={status}>
      {/* Ensure ChartPanel always receives data, even if empty */}
      <ChartPanel
        title="CPU"
        data={cpu}
        color="#4e9af6"
        height={210}
        legend="CPU"
      />
      <ChartPanel
        title="Memory"
        data={memory}
        color="#34d399"
        height={210}
        legend="Memory"
      />
      <ChartPanel
        title="Disk"
        data={disk}
        color="#f59e0b"
        height={210}
        legend="Disk"
      />
      <ChartPanel
        title="Network"
        data={network}
        color="#a78bfa"
        height={210}
        legend="Network"
      />
    </DashboardLayout>
  );
};

export default ProdCheckDashboard;
