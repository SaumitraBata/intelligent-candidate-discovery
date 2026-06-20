// src/components/FilterPanel.jsx
import { useState } from "react";
import { SlidersHorizontal, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "../lib/utils";

const SENIORITY_OPTIONS = [
  "intern", "junior", "mid", "senior",
  "lead", "principal", "director", "vp", "c-level",
];

export default function FilterPanel({ filters, onChange }) {
  const [open, setOpen] = useState(false);

  const update = (key, value) => onChange({ ...filters, [key]: value });

  const activeCount = Object.values(filters || {}).filter(
    (v) =>
      v !== null &&
      v !== undefined &&
      v !== false &&
      v !== "" &&
      !(Array.isArray(v) && v.length === 0)
  ).length;

  return (
    <div className="glass-card overflow-hidden">
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-white/[0.03] transition-colors"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-white/70">
          <SlidersHorizontal size={15} className="text-primary-400" />
          Filters
          {activeCount > 0 && (
            <span className="bg-primary-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center">
              {activeCount}
            </span>
          )}
        </span>
        {open ? (
          <ChevronUp size={15} className="text-white/30" />
        ) : (
          <ChevronDown size={15} className="text-white/30" />
        )}
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-white/[0.05] grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pt-4">
          {/* Min Experience */}
          <div className="space-y-1">
            <label className="text-xs text-white/40 font-medium">
              Min Experience (yrs)
            </label>
            <input
              type="number"
              min="0"
              max="30"
              value={filters?.min_experience ?? ""}
              onChange={(e) =>
                update("min_experience", e.target.value ? Number(e.target.value) : null)
              }
              className="input-field py-2 text-sm"
              placeholder="0"
            />
          </div>

          {/* Max Experience */}
          <div className="space-y-1">
            <label className="text-xs text-white/40 font-medium">
              Max Experience (yrs)
            </label>
            <input
              type="number"
              min="0"
              max="50"
              value={filters?.max_experience ?? ""}
              onChange={(e) =>
                update("max_experience", e.target.value ? Number(e.target.value) : null)
              }
              className="input-field py-2 text-sm"
              placeholder="50"
            />
          </div>

          {/* Notice Period */}
          <div className="space-y-1">
            <label className="text-xs text-white/40 font-medium">
              Max Notice Period (days)
            </label>
            <input
              type="number"
              min="0"
              max="180"
              value={filters?.max_notice_period ?? ""}
              onChange={(e) =>
                update("max_notice_period", e.target.value ? Number(e.target.value) : null)
              }
              className="input-field py-2 text-sm"
              placeholder="90"
            />
          </div>

          {/* Location */}
          <div className="space-y-1">
            <label className="text-xs text-white/40 font-medium">Location</label>
            <input
              type="text"
              value={filters?.location ?? ""}
              onChange={(e) => update("location", e.target.value || null)}
              className="input-field py-2 text-sm"
              placeholder="e.g. Bangalore"
            />
          </div>

          {/* Open to Work */}
          <div className="space-y-1">
            <label className="text-xs text-white/40 font-medium">Availability</label>
            <button
              onClick={() => update("open_to_work_only", !filters?.open_to_work_only)}
              className={cn(
                "w-full py-2 px-3 rounded-lg text-sm font-medium border transition-all",
                filters?.open_to_work_only
                  ? "bg-green-500/20 border-green-500/40 text-green-400"
                  : "bg-white/[0.04] border-white/[0.08] text-white/40 hover:text-white"
              )}
            >
              {filters?.open_to_work_only ? "✓ Open to Work" : "Any Availability"}
            </button>
          </div>

          {/* Seniority */}
          <div className="space-y-1 col-span-2">
            <label className="text-xs text-white/40 font-medium">Seniority Levels</label>
            <div className="flex flex-wrap gap-1">
              {SENIORITY_OPTIONS.map((level) => {
                const selected = (filters?.seniority_levels || []).includes(level);
                return (
                  <button
                    key={level}
                    onClick={() => {
                      const curr = filters?.seniority_levels || [];
                      update(
                        "seniority_levels",
                        selected
                          ? curr.filter((l) => l !== level)
                          : [...curr, level]
                      );
                    }}
                    className={cn(
                      "text-xs px-2.5 py-1 rounded-lg border transition-all capitalize",
                      selected
                        ? "bg-primary-500/20 border-primary-500/40 text-primary-300"
                        : "bg-white/[0.04] border-white/[0.06] text-white/40 hover:text-white"
                    )}
                  >
                    {level}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Clear */}
          <div className="flex items-end">
            <button
              onClick={() => onChange({})}
              className="text-sm text-red-400/70 hover:text-red-400 transition-colors"
            >
              Clear All
            </button>
          </div>
        </div>
      )}
    </div>
  );
}