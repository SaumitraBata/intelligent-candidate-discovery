import { useLocation, useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { ArrowLeft, BarChart3, Search } from "lucide-react";
import { CandidateCardAnimated } from "../components/ui/candidate-card-animated";
import ExportPanel from "../components/ExportPanel";        // ← default import
import FilterPanel from "../components/FilterPanel";        // ← default import
import { useState } from "react";




export default function ResultsPage() {
  const { state }  = useLocation();
  const navigate   = useNavigate();
  const results    = state?.results || [];
  const jdReq      = state?.jdRequirements || {};
  const query      = state?.query;
  const [filters, setFilters] = useState({});

  if (!results.length) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <p className="text-white/40">
          No results found.{" "}
          <button
            onClick={() => navigate("/")}
            className="text-primary-400 hover:underline"
          >
            Go back
          </button>
        </p>
      </div>
    );
  }

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6">

      {/* Header */}
      <motion.div
        className="flex items-center justify-between flex-wrap gap-4"
        initial={{ opacity: 0, y: -12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35 }}
      >
        <div className="flex items-center gap-4">
          <button onClick={() => navigate("/")} className="btn-secondary py-2">
            <ArrowLeft size={15} />
            New Search
          </button>
          <div>
            <h2 className="text-lg font-bold text-white">
              {results.length} Candidates Ranked
            </h2>
            {query && (
              <p className="text-sm text-white/35 flex items-center gap-1">
                <Search size={11} />
                "{query}"
              </p>
            )}
          </div>
        </div>
        <ExportPanel candidates={results} />
      </motion.div>

      {/* JD Requirements summary */}
      {jdReq.hard_skills?.length > 0 && (
        <motion.div
          className="glass-card p-4 flex flex-wrap gap-3 items-center"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.1 }}
        >
          <span className="text-[11px] text-white/30 flex items-center gap-1 uppercase tracking-wider">
            <BarChart3 size={11} />
            Matched against:
          </span>
          <div className="flex flex-wrap gap-1">
            {jdReq.hard_skills.slice(0, 14).map((s) => (
              <span
                key={s}
                className="tag bg-accent-500/[0.08] border-accent-500/[0.15] text-accent-300/80"
              >
                {s}
              </span>
            ))}
            {jdReq.hard_skills.length > 14 && (
              <span className="text-[11px] text-white/25">
                +{jdReq.hard_skills.length - 14} more
              </span>
            )}
          </div>
          {jdReq.experience_range?.[1] < 99 && (
            <span className="tag bg-white/[0.04] border-white/[0.08] text-white/40">
              {jdReq.experience_range[0]}-{jdReq.experience_range[1]} yrs exp
            </span>
          )}
          {jdReq.seniority_level && (
            <span className="tag bg-white/[0.04] border-white/[0.08] text-white/40 capitalize">
              {jdReq.seniority_level} level
            </span>
          )}
        </motion.div>
      )}

      {/* Filter panel */}
      <FilterPanel filters={filters} onChange={setFilters} />

      {/* Results list */}
      <div className="space-y-3">
        {results.map((candidate, index) => (
          <CandidateCardAnimated
            key={candidate.candidate_id}
            candidate={candidate}
            rank={candidate.rank}
            index={index}
          />
        ))}
      </div>
    </div>
  );
}