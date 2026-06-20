// src/components/ui/candidate-card-animated.jsx
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MapPin, Briefcase, Star, CheckCircle, ChevronDown, ChevronUp,
  Zap, ExternalLink, Calendar,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useNavigate } from "react-router-dom";
import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip,
} from "recharts";

const FRIENDLY_LABELS = {
  semantic_fit:      "Profile Match",
  skill_match:       "Skills Match",
  redrob_signals:    "Engagement",
  career_trajectory: "Career Growth",
  experience_fit:    "Experience Fit",
  profile_quality:   "Profile Quality",
};

const FRIENDLY_DESCRIPTIONS = {
  semantic_fit:      "How well their background aligns with the role",
  skill_match:       "How many required skills they have",
  redrob_signals:    "How active and responsive they are on the platform",
  career_trajectory: "Quality of career progression and company history",
  experience_fit:    "Whether their years of experience match what you need",
  profile_quality:   "Completeness and credibility of their profile",
};

const scoreColor = (s) => {
  if (s >= 0.8) return "text-emerald-400";
  if (s >= 0.6) return "text-amber-400";
  if (s >= 0.4) return "text-orange-400";
  return "text-red-400";
};

const scoreLabel = (s) => {
  if (s >= 0.85) return "Excellent";
  if (s >= 0.70) return "Strong";
  if (s >= 0.55) return "Good";
  if (s >= 0.40) return "Fair";
  return "Weak";
};

const scoreBg = (s) => {
  if (s >= 0.8) return "from-emerald-500 to-teal-500";
  if (s >= 0.6) return "from-amber-500 to-orange-400";
  if (s >= 0.4) return "from-orange-500 to-red-400";
  return "from-red-500 to-red-700";
};

const matchStrength = (score) => {
  if (score >= 0.85) return { label: "Excellent Match" };
  if (score >= 0.75) return { label: "Strong Match" };
  if (score >= 0.65) return { label: "Good Match" };
  if (score >= 0.50) return { label: "Possible Match" };
  return { label: "Weak Match" };
};

function ScoreBar({ label, description, value }) {
  return (
    <div className="group">
      <div className="flex justify-between mb-1 items-baseline">
        <span className="text-[12px] text-neutral-300 font-medium" title={description}>
          {label}
        </span>
        <span className={cn("text-[11px] font-semibold tabular-nums", scoreColor(value))}>
          {scoreLabel(value)}
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-neutral-800 overflow-hidden">
        <motion.div
          className={cn("h-full rounded-full bg-gradient-to-r", scoreBg(value))}
          initial={{ width: 0 }}
          animate={{ width: `${value * 100}%` }}
          transition={{ duration: 0.8, ease: "easeOut", delay: 0.1 }}
        />
      </div>
    </div>
  );
}

function RadarScoreChart({ breakdown }) {
  const data = Object.entries(breakdown || {}).map(([key, value]) => ({
    subject:  FRIENDLY_LABELS[key] || key,
    score:    Math.round(value * 100),
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.08)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "rgba(255,255,255,0.5)", fontSize: 10 }}
        />
        <Radar
          dataKey="score"
          stroke="#10b981"
          fill="#10b981"
          fillOpacity={0.25}
          strokeWidth={1.5}
        />
        <Tooltip
          contentStyle={{
            background: "rgba(0,0,0,0.9)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "8px",
            fontSize: "12px",
            color: "#fff",
          }}
          formatter={(v) => [`${v}/100`, "Score"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}

function HumanReasoning({ candidate }) {
  const r = candidate.redrob_highlights || {};
  const reasons = [];

  if (candidate.score_breakdown?.skill_match >= 0.75) {
    reasons.push({ type: "good", text: "Has most of the required skills" });
  }
  if (candidate.score_breakdown?.semantic_fit >= 0.80) {
    reasons.push({ type: "good", text: "Background closely matches the role" });
  }
  if (r.open_to_work) {
    reasons.push({ type: "good", text: "Actively looking for new opportunities" });
  }
  if (r.notice_period_days <= 30 && r.notice_period_days > 0) {
    reasons.push({ type: "good", text: `Available in ${r.notice_period_days} days` });
  }
  if (r.response_rate >= 0.7) {
    reasons.push({ type: "good", text: "Responds quickly to recruiters" });
  }
  if (r.verified) {
    reasons.push({ type: "good", text: "Identity and credentials verified" });
  }
  if (r.github_score >= 70) {
    reasons.push({ type: "good", text: "Strong open-source contributions" });
  }

  if (candidate.score_breakdown?.experience_fit < 0.5) {
    reasons.push({ type: "warning", text: "Experience level may not match" });
  }
  if (r.response_rate < 0.3 && r.response_rate > 0) {
    reasons.push({ type: "warning", text: "Slow to respond to messages" });
  }
  if (r.notice_period_days > 60) {
    reasons.push({ type: "warning", text: `Long notice period (${r.notice_period_days} days)` });
  }

  return (
    <div className="space-y-1.5">
      {reasons.slice(0, 6).map((reason, i) => (
        <div key={i} className="flex items-start gap-2 text-[12px]">
          <span className={cn(
            "mt-0.5 flex-shrink-0",
            reason.type === "good" ? "text-emerald-400" : "text-amber-400"
          )}>
            {reason.type === "good" ? "✓" : "⚠"}
          </span>
          <span className="text-neutral-300 leading-relaxed">{reason.text}</span>
        </div>
      ))}
    </div>
  );
}

export function CandidateCardAnimated({ candidate, rank, index = 0 }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  const r = candidate.redrob_highlights || {};
  const isTop3 = rank <= 3;
  const match = matchStrength(candidate.final_score);

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, delay: index * 0.04, ease: "easeOut" }}
      className={cn(
        "relative rounded-xl border transition-all duration-300 overflow-hidden",
        isTop3
          ? "border-amber-500/30 bg-gradient-to-br from-amber-500/[0.04] to-neutral-900/40"
          : "border-neutral-800 bg-neutral-900/40",
        "hover:border-neutral-700 hover:bg-neutral-900/60",
        "backdrop-blur-sm"
      )}
    >
      {isTop3 && (
        <div className={cn(
          "absolute top-0 left-0 right-0 h-[2px]",
          rank === 1 ? "bg-gradient-to-r from-amber-500/0 via-amber-400 to-amber-500/0" :
          rank === 2 ? "bg-gradient-to-r from-slate-400/0 via-slate-300 to-slate-400/0" :
                       "bg-gradient-to-r from-amber-700/0 via-amber-600 to-amber-700/0"
        )} />
      )}

      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className={cn(
            "w-11 h-11 rounded-xl flex items-center justify-center text-sm font-bold flex-shrink-0 border",
            rank === 1 ? "bg-amber-500/20 border-amber-500/40 text-amber-400" :
            rank === 2 ? "bg-slate-400/15 border-slate-400/30 text-slate-300" :
            rank === 3 ? "bg-amber-700/20 border-amber-700/40 text-amber-500" :
                         "bg-neutral-800/60 border-neutral-700 text-neutral-400"
          )}>
            {rank <= 3 ? <Star size={16} fill="currentColor" /> : `#${rank}`}
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="min-w-0">
                <h3 className="font-semibold text-neutral-100 truncate text-base">
                  {candidate.name || candidate.candidate_id}
                </h3>
                <p className="text-sm text-neutral-400 mt-0.5">
                  {candidate.current_title}
                  {candidate.current_company && (
                    <span className="text-neutral-500"> · {candidate.current_company}</span>
                  )}
                </p>
              </div>

              <div className="flex-shrink-0 text-right">
                <div className={cn(
                  "text-2xl font-bold tabular-nums leading-none",
                  scoreColor(candidate.final_score)
                )}>
                  {(candidate.final_score * 100).toFixed(0)}%
                </div>
                <div className={cn(
                  "text-[10px] uppercase tracking-wider mt-1 font-medium",
                  scoreColor(candidate.final_score)
                )}>
                  {match.label}
                </div>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              {candidate.location && (
                <span className="flex items-center gap-1 text-[11px] text-neutral-400">
                  <MapPin size={11} />
                  {candidate.location}
                </span>
              )}
              <span className="flex items-center gap-1 text-[11px] text-neutral-400">
                <Briefcase size={11} />
                {candidate.experience_years?.toFixed(0)} years
              </span>
              <span className="text-[11px] bg-neutral-800 text-neutral-300 px-2 py-0.5 rounded capitalize border border-neutral-700">
                {candidate.seniority_level}
              </span>

              {r.open_to_work && (
                <span className="flex items-center gap-1 text-[11px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded">
                  <Zap size={9} />
                  Open to Opportunities
                </span>
              )}

              {r.verified && (
                <span className="flex items-center gap-1 text-[11px] bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2 py-0.5 rounded">
                  <CheckCircle size={9} />
                  Verified
                </span>
              )}

              {r.notice_period_days <= 30 && r.notice_period_days > 0 && (
                <span className="flex items-center gap-1 text-[11px] bg-violet-500/10 text-violet-400 border border-violet-500/20 px-2 py-0.5 rounded">
                  <Calendar size={9} />
                  Available in {r.notice_period_days}d
                </span>
              )}
            </div>

            <div className="mt-4 bg-neutral-900/50 border border-neutral-800/60 rounded-lg p-3">
              <HumanReasoning candidate={candidate} />
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-neutral-800/60">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="flex items-center gap-1.5 text-[12px] text-neutral-400 hover:text-neutral-100 transition-colors px-3 py-1.5 rounded-md hover:bg-neutral-800/60"
          >
            {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {expanded ? "Hide details" : "Show full analysis"}
          </button>
          <button
            onClick={() => navigate(`/candidate/${candidate.candidate_id}`)}
            className="ml-auto flex items-center gap-1.5 text-[12px] text-emerald-400 hover:text-emerald-300 transition-colors px-3 py-1.5 rounded-md hover:bg-emerald-500/10"
          >
            View Profile
            <ExternalLink size={11} />
          </button>
        </div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 border-t border-neutral-800/60 grid md:grid-cols-2 gap-6 pt-5">
              <div className="space-y-3">
                <h4 className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider mb-3">
                  Detailed Analysis
                </h4>
                {Object.entries(candidate.score_breakdown || {}).map(([key, val]) => (
                  <ScoreBar
                    key={key}
                    label={FRIENDLY_LABELS[key] || key}
                    description={FRIENDLY_DESCRIPTIONS[key]}
                    value={val}
                  />
                ))}
              </div>

              <div className="space-y-4">
                <h4 className="text-[11px] font-semibold text-neutral-500 uppercase tracking-wider">
                  Overall View
                </h4>
                <RadarScoreChart breakdown={candidate.score_breakdown} />

                <div className="grid grid-cols-2 gap-2">
                  {[
                    { label: "Replies to recruiters",  value: `${((r.response_rate || 0) * 100).toFixed(0)}%` },
                    { label: "Ready to start",         value: `${r.notice_period_days ?? "?"} days` },
                    { label: "Profile complete",       value: `${r.profile_completeness?.toFixed(0) ?? 0}%` },
                    { label: "GitHub activity",        value: r.github_score >= 0 ? `${r.github_score}/100` : "Not linked" },
                  ].map(({ label, value }) => (
                    <div key={label} className="bg-neutral-900/60 border border-neutral-800 rounded-lg px-3 py-2">
                      <p className="text-[10px] text-neutral-500 uppercase tracking-wider">{label}</p>
                      <p className="text-sm font-semibold text-neutral-100 mt-1">{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="md:col-span-2">
                <p className="text-[11px] text-neutral-500 mb-2 uppercase tracking-wider">
                  Skills & Expertise
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {(candidate.skills || []).slice(0, 15).map((s) => (
                    <span
                      key={s}
                      className="text-[11px] bg-emerald-500/[0.08] border border-emerald-500/[0.20] text-emerald-300/90 px-2 py-1 rounded-md"
                    >
                      {s}
                    </span>
                  ))}
                </div>
              </div>

              {candidate.anomaly_flags?.length > 0 && (
                <div className="md:col-span-2">
                  <p className="text-[11px] text-amber-500/80 mb-2 uppercase tracking-wider">
                    Things to Verify
                  </p>
                  {candidate.anomaly_flags.map((f) => (
                    <p key={f} className="text-[12px] text-amber-400/70">
                      • {f.replace(/_/g, " ").replace(/^./, c => c.toUpperCase())}
                    </p>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

export default CandidateCardAnimated;