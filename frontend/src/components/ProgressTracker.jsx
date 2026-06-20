import { CheckCircle, Loader, Circle } from "lucide-react";
import clsx from "clsx";

const STAGES = [
  { id: "parsing_jd", label: "Parsing JD" },
  { id: "embedding", label: "Generating Embeddings" },
  { id: "scoring", label: "Scoring Candidates" },
  { id: "filtering", label: "Applying Filters" },
  { id: "ranking", label: "Ranking" },
  { id: "explaining", label: "Generating Explanations" },
  { id: "complete", label: "Complete" },
];

export default function ProgressTracker({ progress }) {
  if (!progress) return null;

  const currentIdx = STAGES.findIndex((s) => s.id === progress.stage);

  return (
    <div className="glass-card p-6 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-white">Pipeline Progress</h3>
        <span className="text-2xl font-bold text-primary-400">
          {progress.percent}%
        </span>
      </div>

      {/* Progress bar */}
      <div className="score-bar">
        <div
          className="score-fill bg-gradient-to-r from-primary-500 to-accent-500"
          style={{ width: `${progress.percent}%` }}
        />
      </div>

      {/* Stage status */}
      <p className="text-sm text-gray-300">{progress.message}</p>

      {/* Stage list */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        {STAGES.map((stage, idx) => {
          const isDone = idx < currentIdx;
          const isCurrent = idx === currentIdx;
          return (
            <div
              key={stage.id}
              className={clsx(
                "flex items-center gap-2 text-xs px-2 py-1 rounded-lg",
                isDone && "text-green-400",
                isCurrent && "text-primary-300 bg-primary-500/10",
                !isDone && !isCurrent && "text-gray-600"
              )}
            >
              {isDone ? (
                <CheckCircle size={12} />
              ) : isCurrent ? (
                <Loader size={12} className="animate-spin" />
              ) : (
                <Circle size={12} />
              )}
              {stage.label}
            </div>
          );
        })}
      </div>
    </div>
  );
}