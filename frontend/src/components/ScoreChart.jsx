import {
  RadarChart, Radar, PolarGrid, PolarAngleAxis,
  ResponsiveContainer, Tooltip,
} from "recharts";

const SCORE_LABELS = {
  semantic_fit: "Semantic",
  skill_match: "Skills",
  redrob_signals: "Platform",
  career_trajectory: "Career",
  experience_fit: "Experience",
  profile_quality: "Quality",
};

export default function ScoreChart({ breakdown }) {
  const data = Object.entries(breakdown || {}).map(([key, value]) => ({
    subject: SCORE_LABELS[key] || key,
    score: Math.round(value * 100),
    fullMark: 100,
  }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <RadarChart data={data}>
        <PolarGrid stroke="rgba(255,255,255,0.1)" />
        <PolarAngleAxis
          dataKey="subject"
          tick={{ fill: "#9ca3af", fontSize: 11 }}
        />
        <Radar
          dataKey="score"
          stroke="#3b82f6"
          fill="#3b82f6"
          fillOpacity={0.3}
          strokeWidth={2}
        />
        <Tooltip
          contentStyle={{
            background: "#1f2937",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "8px",
            fontSize: "12px",
          }}
          formatter={(v) => [`${v}/100`, "Score"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}