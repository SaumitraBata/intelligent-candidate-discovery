// src/components/ExportPanel.jsx
import { Download, CheckCircle } from "lucide-react";
import { useState } from "react";
import { exportResults } from "../api/client";

export default function ExportPanel({ candidates }) {
  const [exporting, setExporting] = useState(false);
  const [done, setDone] = useState(false);

  const handleExport = async () => {
    if (!candidates?.length) return;
    setExporting(true);
    try {
      const resp = await exportResults(candidates);
      const url = URL.createObjectURL(new Blob([resp.data]));
      const a = document.createElement("a");
      a.href = url;
      a.download = "submission.csv";
      a.click();
      URL.revokeObjectURL(url);
      setDone(true);
      setTimeout(() => setDone(false), 3000);
    } catch (e) {
      console.error("Export failed:", e);
    } finally {
      setExporting(false);
    }
  };

  return (
    <button
      onClick={handleExport}
      disabled={exporting || !candidates?.length}
      className="btn-secondary flex items-center gap-2 text-sm"
    >
      {done ? (
        <>
          <CheckCircle size={16} className="text-green-400" />
          <span className="text-green-400">Downloaded!</span>
        </>
      ) : (
        <>
          <Download size={16} />
          Export CSV ({candidates?.length ?? 0})
        </>
      )}
    </button>
  );
}