// src/pages/HomePage.jsx
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { CandidateSearchInput } from "../components/ui/candidate-search-input";
import { ProgressiveFluxLoader } from "../components/ui/progressive-flux-loader";
import { useSearch } from "../hooks/useSearch";
import { useWebSocket } from "../hooks/useWebSocket";
import { getStats } from "../api/client";

const SEARCH_PHASES = [
  { at: 0,   label: "starting the search" },
  { at: 14,  label: "understanding the role" },
  { at: 28,  label: "exploring the talent pool" },
  { at: 44,  label: "finding the right fits" },
  { at: 60,  label: "weighing skills and experience" },
  { at: 75,  label: "checking who's available" },
  { at: 88,  label: "ranking the best matches" },
  { at: 96,  label: "almost there" },
  { at: 100, label: "your top candidates are ready" },
];

export default function HomePage() {
  const navigate = useNavigate();
  const [topK, setTopK]       = useState(20);
  const [stats, setStats]     = useState(null);
  const [progress, setProgress] = useState(0);

  const {
    loading, error, sessionId,
    runSearch, runUpload, reset,
  } = useSearch();

  const { progress: wsProgress } = useWebSocket(sessionId);

  useEffect(() => {
    if (wsProgress) setProgress(wsProgress.percent || 0);
  }, [wsProgress]);




  useEffect(() => {
    if (loading && !sessionId) {
      let p = 0;
      // Slow, smooth progression — increments of 2 every 180ms
      // Total: ~92% in 8.3 seconds (gives time to read each phase)
      const interval = setInterval(() => {
        // Slow down as we approach the end (feels more natural)
        const increment = p < 30 ? 2.5 : p < 60 ? 1.8 : p < 85 ? 1.2 : 0.6;
        p = Math.min(p + increment, 92);
        setProgress(p);
      }, 180);
      return () => clearInterval(interval);
    }
    if (!loading) setProgress(0);
  }, [loading, sessionId]);



  useEffect(() => {
    getStats().then(({ data }) => setStats(data)).catch(() => {});
  }, []);

  const handleSearch = async (query, topKVal) => {
    reset();
    setProgress(5);
    try {
      const data = await runSearch(query, topKVal || topK, {});
      setProgress(100);
      setTimeout(() => {
        navigate("/results", {
          state: {
            results:        data.candidates,
            jdRequirements: data.jd_requirements,
            query,
            totalSearched:  data.total_searched,
          },
        });
      }, 400);
    } catch {
      setProgress(0);
    }
  };

  const handleUpload = async (file, topKVal) => {
    reset();
    setProgress(5);
    try {
      const data = await runUpload(file, topKVal || topK);
      setProgress(100);
      setTimeout(() => {
        navigate("/results", {
          state: {
            results:        data.candidates,
            jdRequirements: data.jd_requirements,
            uploadedFile:   data.uploaded_filename,
          },
        });
      }, 400);
    } catch {
      setProgress(0);
    }
  };

  return (
    <div className="min-h-[calc(100vh-56px)] flex flex-col relative">

      {/* Subtle grain overlay */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.015]"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
        }}
      />

      {/* Soft ambient highlight */}
      <div className="absolute inset-x-0 top-0 pointer-events-none overflow-hidden">
        <div className="absolute top-[-15rem] left-1/2 -translate-x-1/2 w-[60rem] h-[40rem] bg-gradient-to-b from-blue-500/[0.04] via-violet-500/[0.02] to-transparent rounded-full blur-3xl" />
      </div>

      {/* Main content */}
      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 py-20 max-w-3xl mx-auto w-full">

        {/* Eyebrow */}
        <div className="inline-flex items-center gap-2 mb-8 text-[11px] text-neutral-500 uppercase tracking-[0.15em]">
          <span className="w-6 h-px bg-neutral-700" />
          Talent Intelligence
          <span className="w-6 h-px bg-neutral-700" />
        </div>

        {/* Headline — minimal, refined */}
        <h1 className="text-center text-[44px] md:text-[56px] font-semibold leading-[1.05] tracking-[-0.03em] text-neutral-100 mb-4 animate-slide-up">
          Find your next hire,
          <br />
          <span className="text-neutral-500">
            with precision
          </span>
        </h1>

        <p className="text-center text-[15px] text-neutral-500 mb-12 max-w-xl leading-relaxed">
          Search verified candidate profiles using natural language.
          Backed by semantic understanding, behavioral signals, and transparent ranking.
        </p>

        {/* Search */}
        <div className="w-full">
          <CandidateSearchInput
            onSearch={handleSearch}
            onUpload={handleUpload}
            loading={loading}
            topK={topK}
            onTopKChange={setTopK}
          />
        </div>

        {/* Error */}
        {error && !loading && (
          <div className="w-full mt-6 panel border-red-900/40 bg-red-950/20 px-4 py-3 animate-fade-in">
            <p className="text-red-400 text-sm">{error}</p>
          </div>
        )}

        {/* Stats — minimal inline */}
        {stats && (
          <div className="mt-16 w-full">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-neutral-900 rounded-lg overflow-hidden border border-neutral-900">
              <StatCell
                value={stats.total_candidates?.toLocaleString()}
                label="Candidates"
              />
              <StatCell
                value={stats.open_to_work?.toLocaleString()}
                label="Open to work"
              />
              <StatCell
                value={`${stats.avg_experience_years}y`}
                label="Avg experience"
              />
              <StatCell
                value={Object.keys(stats.top_countries || {}).length}
                label="Countries"
              />
            </div>
          </div>
        )}
      </main>

      {/* Bottom progress indicator */}
      {loading && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 bg-neutral-900 rounded-xl shadow-2xl border border-neutral-800 min-w-[420px] max-w-[90vw] animate-slide-up">

          <div className="px-5 py-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <span className="relative flex w-2 h-2">
                  <span className="absolute inset-0 rounded-full bg-blue-500 animate-ping opacity-75" />
                  <span className="relative w-2 h-2 rounded-full bg-blue-500" />
                </span>

                <span className="text-[13px] text-neutral-200 font-medium capitalize">
                  {wsProgress?.message ||
                    [...SEARCH_PHASES].reverse().find(p => progress >= p.at)?.label ||
                    "starting the search"}
                </span>

              </div>
              <span className="text-[11px] text-neutral-500 font-mono tabular-nums">
                {Math.round(progress)}%
              </span>
            </div>

            {/* Slim progress bar */}
            <div className="h-1 bg-neutral-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-cyan-400 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCell({ value, label }) {
  return (
    <div className="bg-neutral-950 px-5 py-4">
      <div className="text-[20px] font-semibold text-neutral-100 tabular-nums tracking-tight">
        {value}
      </div>
      <div className="text-[11px] text-neutral-500 mt-1 tracking-wide">
        {label}
      </div>
    </div>
  );
}