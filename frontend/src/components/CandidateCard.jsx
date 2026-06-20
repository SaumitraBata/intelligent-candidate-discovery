import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  MapPin, Briefcase, Star, Clock, Github,
  CheckCircle, AlertTriangle, ChevronDown, ChevronUp,
  Zap, Award,
} from "lucide-react";
import clsx from "clsx";
import ScoreChart from "./ScoreChart";

const SCORE_COLOR = (s) => {
  if (s >= 0.8) return "text-green-400";
  if (s >= 0.6) return "text-yellow-400";
  if (s >= 0.4) return "text-orange-400";
  return "text-red-400";
};

const SCORE_BG = (s) => {
  if (s >= 0.8) return "bg-green-500";
  if (s >= 0.6) return "bg-yellow-500";
  if (s >= 0.4) return "bg-orange-500";
  return "bg-red-500";
};

export default function CandidateCard({ candidate, rank }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const r = candidate.redrob_highlights || {};

  return (
    <div className="glass-card overflow-hidden hover:border-white/20 transition-all duration-300">
      {/* Main Row */}
      <div className="p-5">
        <div className="flex items-start gap-4">
          {/* Rank badge */}
          <div className={clsx(
            "w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0",
            rank <= 3
              ? "bg-gradient-to-br from-yellow-400 to-orange-500 text-gray-900"
              : "bg-white/10 text-gray-300"
          )}>
            {rank <= 3 ? <Star size={16} /> : `#${rank}`}
          </div>

          {/* Candidate info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <h3 className="font-semibold text-white truncate">
                  {candidate.name || candidate.candidate_id}
                </h3>
                <p className="text-sm text-gray-400">
                  {candidate.current_title}
                  {candidate.current_company && (
                    <span className="text-gray-500"> @ {candidate.current_company}</span>
                  )}
                </p>
              </div>

              {/* Score */}
              <div className="text-right flex-shrink-0">
                <div className={clsx("text-2xl font-bold", SCORE_COLOR(candidate.final_score))}>
                  {(candidate.final_score * 100).toFixed(1)}
                </div>
                <div className="text-xs text-gray-500">match score</div>
              </div>
            </div>

            {/* Meta tags */}
            <div className="flex flex-wrap gap-2 mt-3">
              {candidate.location && (
                <span className="flex items-center gap-1 text-xs text-gray-400">
                  <MapPin size={11} />
                  {candidate.location}
                </span>
              )}
              <span className="flex items-center gap-1 text-xs text-gray-400">
                <Briefcase size={11} />
                {candidate.experience_years?.toFixed(1)} yrs
              </span>
              <span className="text-xs bg-white/10 text-gray-300 px-2 py-0.5 rounded-full capitalize">
                {candidate.seniority_level}
              </span>

              {r.open_to_work && (
                <span className="flex items-center gap-1 text-xs bg-green-500/15 text-green-400 border border-green-500/30 px-2 py-0.5 rounded-full">
                  <Zap size={10} />
                  Open to Work
                </span>
              )}
              {r.verified && (
                <span className="flex items-center gap-1 text-xs bg-blue-500/15 text-blue-400 border border-blue-500/30 px-2 py-0.5 rounded-full">
                  <CheckCircle size={10} />
                  Verified
                </span>
              )}
              {candidate.anomaly_flags?.length > 0 && (
                <span className="flex items-center gap-1 text-xs bg-yellow-500/15 text-yellow-400 border border-yellow-500/30 px-2 py-0.5 rounded-full">
                  <AlertTriangle size={10} />
                  {candidate.anomaly_flags.length} flag{candidate.anomaly_flags.length > 1 ? "s" : ""}
                </span>
              )}
            </div>

            {/* Score bars */}
            <div className="grid grid-cols-3 gap-2 mt-4">
              {Object.entries(candidate.score_breakdown || {}).map(([key, val]) => (
                <div key={key}>
                  <div className="flex justify-between mb-1">
                    <span className="text-xs text-gray-500 capitalize">
                      {key.replace(/_/g, " ")}
                    </span>
                    <span className={clsx("text-xs font-medium", SCORE_COLOR(val))}>
                      {(val * 100).toFixed(0)}
                    </span>
                  </div>
                  <div className="score-bar">
                    <div
                      className={clsx("score-fill", SCORE_BG(val))}
                      style={{ width: `${val * 100}%`, opacity: 0.8 }}
                    />
                  </div>
                </div>
              ))}
            </div>

            {/* Reasoning */}
            <p className="text-xs text-gray-400 mt-3 leading-relaxed">
              {candidate.reasoning}
            </p>
          </div>
        </div>

        {/* Expand button */}
        <div className="flex gap-2 mt-4 pt-3 border-t border-white/5">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
          >
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            {expanded ? "Less details" : "More details"}
          </button>
          <button
            onClick={() => navigate(`/candidate/${candidate.candidate_id}`)}
            className="text-xs text-primary-400 hover:text-primary-300 ml-auto transition-colors"
          >
            Full Profile →
          </button>
        </div>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="px-5 pb-5 border-t border-white/5 grid md:grid-cols-2 gap-6 pt-4">
          {/* Radar chart */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Score Breakdown
            </h4>
            <ScoreChart breakdown={candidate.score_breakdown} />
          </div>

          {/* Platform signals */}
          <div className="space-y-3">
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Platform Signals
            </h4>
            <div className="grid grid-cols-2 gap-3">
              <Signal label="Response Rate" value={`${((r.response_rate || 0) * 100).toFixed(0)}%`} />
              <Signal label="Notice Period" value={`${r.notice_period_days ?? "N/A"}d`} />
              {r.github_score >= 0 && (
                <Signal label="GitHub Score" value={`${r.github_score}/100`} icon={Github} />
              )}
              <Signal label="Profile Complete" value={`${r.profile_completeness?.toFixed(0) ?? 0}%`} />
            </div>

            {/* Skills */}
            <div>
              <p className="text-xs text-gray-500 mb-2">Top Skills</p>
              <div className="flex flex-wrap gap-1">
                {(candidate.skills || []).slice(0, 10).map((s) => (
                  <span
                    key={s}
                    className="text-xs bg-primary-500/10 border border-primary-500/20
                               text-primary-300 px-2 py-0.5 rounded-md"
                  >
                    {s}
                  </span>
                ))}
              </div>
            </div>

            {/* Anomaly flags */}
            {candidate.anomaly_flags?.length > 0 && (
              <div>
                <p className="text-xs text-yellow-500 mb-1">⚠ Flags</p>
                {candidate.anomaly_flags.map((f) => (
                  <p key={f} className="text-xs text-yellow-400/70">{f.replace(/_/g, " ")}</p>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Signal({ label, value, icon: Icon }) {
  return (
    <div className="bg-white/5 rounded-lg px-3 py-2">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-sm font-semibold text-white flex items-center gap-1 mt-0.5">
        {Icon && <Icon size={12} className="text-gray-400" />}
        {value}
      </p>
    </div>
  );
}