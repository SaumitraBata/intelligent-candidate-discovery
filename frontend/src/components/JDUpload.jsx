import { useState, useRef } from "react";
import { Upload, FileText, X, AlignLeft } from "lucide-react";
import clsx from "clsx";

export default function JDUpload({ onUpload, onTextSubmit, loading }) {
  const [tab, setTab] = useState("text"); // "text" | "file"
  const [jdText, setJdText] = useState("");
  const [file, setFile] = useState(null);
  const [topK, setTopK] = useState(100);
  const [dragging, setDragging] = useState(false);
  const fileRef = useRef(null);

  const handleTextSubmit = (e) => {
    e.preventDefault();
    if (!jdText.trim()) return;
    onTextSubmit(jdText, topK);
  };

  const handleFileSubmit = (e) => {
    e.preventDefault();
    if (!file) return;
    onUpload(file, topK);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && (dropped.name.endsWith(".docx") || dropped.name.endsWith(".txt"))) {
      setFile(dropped);
    }
  };

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex gap-1 bg-white/5 p-1 rounded-xl w-fit">
        {[
          { id: "text", label: "Paste JD Text", icon: AlignLeft },
          { id: "file", label: "Upload File", icon: Upload },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setTab(id)}
            className={clsx(
              "flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all",
              tab === id
                ? "bg-primary-600 text-white"
                : "text-gray-400 hover:text-white"
            )}
          >
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      {/* Text Tab */}
      {tab === "text" && (
        <form onSubmit={handleTextSubmit} className="space-y-3">
          <textarea
            value={jdText}
            onChange={(e) => setJdText(e.target.value)}
            placeholder="Paste your full job description here...&#10;&#10;Include: role title, required skills, experience, responsibilities, etc."
            className="input-field min-h-48 resize-y font-mono text-sm"
            disabled={loading}
          />
          <div className="flex items-center gap-3 justify-between">
            <span className="text-xs text-gray-500">
              {jdText.length} characters
            </span>
            <div className="flex items-center gap-3">
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="input-field w-32 py-2 text-sm"
                disabled={loading}
              >
                <option value={20}>Top 20</option>
                <option value={50}>Top 50</option>
                <option value={100}>Top 100</option>
              </select>
              <button
                type="submit"
                className="btn-primary"
                disabled={loading || !jdText.trim()}
              >
                {loading ? "Ranking..." : "Rank Candidates"}
              </button>
            </div>
          </div>
        </form>
      )}

      {/* File Tab */}
      {tab === "file" && (
        <form onSubmit={handleFileSubmit} className="space-y-3">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={handleDrop}
            onClick={() => !file && fileRef.current?.click()}
            className={clsx(
              "border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all",
              dragging
                ? "border-primary-500 bg-primary-500/10"
                : "border-white/20 hover:border-white/40 hover:bg-white/5",
              file && "cursor-default"
            )}
          >
            {file ? (
              <div className="flex items-center justify-center gap-3">
                <FileText size={24} className="text-primary-400" />
                <span className="text-white font-medium">{file.name}</span>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setFile(null); }}
                  className="text-gray-400 hover:text-red-400"
                >
                  <X size={18} />
                </button>
              </div>
            ) : (
              <>
                <Upload size={32} className="mx-auto mb-3 text-gray-500" />
                <p className="text-gray-300 font-medium">Drop your JD file here</p>
                <p className="text-gray-500 text-sm mt-1">
                  Supports .docx and .txt files
                </p>
              </>
            )}
          </div>
          <input
            ref={fileRef}
            type="file"
            accept=".docx,.txt"
            className="hidden"
            onChange={(e) => setFile(e.target.files[0])}
          />
          <div className="flex justify-end gap-3">
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
              className="input-field w-32 py-2 text-sm"
              disabled={loading}
            >
              <option value={20}>Top 20</option>
              <option value={50}>Top 50</option>
              <option value={100}>Top 100</option>
            </select>
            <button
              type="submit"
              className="btn-primary"
              disabled={loading || !file}
            >
              {loading ? "Processing..." : "Rank from File"}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}