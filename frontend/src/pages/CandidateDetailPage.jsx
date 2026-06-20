import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, MapPin, Briefcase, GraduationCap,
         Award, Github, CheckCircle } from "lucide-react";
import { getCandidateDetail } from "../api/client";

export default function CandidateDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getCandidateDetail(id)
      .then(({ data }) => setProfile(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <div className="w-10 h-10 border-2 border-primary-500 border-t-transparent rounded-full animate-spin mx-auto" />
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="max-w-4xl mx-auto px-6 py-20 text-center">
        <p className="text-gray-400">Candidate not found.</p>
      </div>
    );
  }

  const r = profile.redrob || {};

  return (
    <div className="max-w-4xl mx-auto px-6 py-8 space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="btn-secondary flex items-center gap-2 py-2"
      >
        <ArrowLeft size={16} /> Back
      </button>

      {/* Header */}
      <div className="glass-card p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-white">{profile.name}</h1>
            <p className="text-gray-400 mt-1">{profile.current_title} @ {profile.current_company}</p>
            <div className="flex flex-wrap gap-3 mt-3 text-sm text-gray-400">
              {profile.location && (
                <span className="flex items-center gap-1">
                  <MapPin size={14} /> {profile.location}
                </span>
              )}
              <span className="flex items-center gap-1">
                <Briefcase size={14} /> {profile.experience_years?.toFixed(1)} yrs
              </span>
              <span className="capitalize bg-white/10 px-3 py-0.5 rounded-full text-xs">
                {profile.seniority_level}
              </span>
              {r.open_to_work_flag && (
                <span className="text-green-400 flex items-center gap-1 text-xs">
                  <CheckCircle size={12} /> Open to Work
                </span>
              )}
            </div>
          </div>
          <div className="text-right text-sm text-gray-400 space-y-1">
            <p>Notice: <span className="text-white">{r.notice_period_days}d</span></p>
            <p>Response: <span className="text-white">{((r.recruiter_response_rate || 0) * 100).toFixed(0)}%</span></p>
            {r.github_score >= 0 && (
              <p className="flex items-center gap-1 justify-end">
                <Github size={12} />
                <span className="text-white">{r.github_score}/100</span>
              </p>
            )}
          </div>
        </div>
        {profile.summary && (
          <p className="text-gray-400 text-sm mt-4 leading-relaxed">{profile.summary}</p>
        )}
      </div>

      {/* Skills */}
      <div className="glass-card p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
          <Award size={16} className="text-primary-400" /> Skills
        </h2>
        <div className="flex flex-wrap gap-2">
          {Object.entries(profile.skills_with_proficiency || {}).map(([skill, level]) => (
            <span key={skill}
              className="text-xs border rounded-lg px-2 py-1 capitalize"
              style={{
                borderColor: level === "expert" ? "#8b5cf6" : level === "advanced" ? "#3b82f6" : "#374151",
                color: level === "expert" ? "#a78bfa" : level === "advanced" ? "#60a5fa" : "#9ca3af",
                background: "rgba(255,255,255,0.03)",
              }}
            >
              {skill}
              <span className="ml-1 opacity-60 text-[10px]">({level})</span>
            </span>
          ))}
        </div>
      </div>

      {/* Career History */}
      <div className="glass-card p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
          <Briefcase size={16} className="text-primary-400" /> Career History
        </h2>
        <div className="space-y-4">
          {(profile.career_history || []).map((job, i) => (
            <div key={i} className="border-l-2 border-white/10 pl-4">
              <p className="font-medium text-white">{job.title}</p>
              <p className="text-sm text-gray-400">{job.company} · {job.industry}</p>
              <p className="text-xs text-gray-500">
                {job.start_date} — {job.end_date || "Present"} ({job.duration_months}m)
              </p>
              {job.description && (
                <p className="text-xs text-gray-500 mt-1 leading-relaxed line-clamp-3">
                  {job.description}
                </p>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Education */}
      <div className="glass-card p-6">
        <h2 className="font-semibold text-white mb-4 flex items-center gap-2">
          <GraduationCap size={16} className="text-primary-400" /> Education
        </h2>
        <div className="space-y-3">
          {(profile.education_list || []).map((edu, i) => (
            <div key={i}>
              <p className="font-medium text-white">{edu.degree} in {edu.field_of_study}</p>
              <p className="text-sm text-gray-400">{edu.institution}</p>
              <p className="text-xs text-gray-500">{edu.start_year} — {edu.end_year}</p>
              {edu.tier && edu.tier !== "unknown" && (
                <span className="text-xs bg-accent-500/10 text-accent-300 px-2 py-0.5 rounded mt-1 inline-block">
                  {edu.tier.replace("_", " ")}
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Skill Assessments */}
      {Object.keys(r.skill_assessment_scores || {}).length > 0 && (
        <div className="glass-card p-6">
          <h2 className="font-semibold text-white mb-4">Platform Skill Assessments</h2>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(r.skill_assessment_scores).map(([skill, score]) => (
              <div key={skill}>
                <div className="flex justify-between mb-1">
                  <span className="text-xs text-gray-400 capitalize">{skill}</span>
                  <span className="text-xs font-medium text-white">{score}/100</span>
                </div>
                <div className="score-bar">
                  <div className="score-fill bg-accent-500" style={{ width: `${score}%`, opacity: 0.8 }} />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}