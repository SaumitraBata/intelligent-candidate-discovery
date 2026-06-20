import { useState } from "react";
import { Search, Sparkles } from "lucide-react";

const EXAMPLE_QUERIES = [
  "Senior Python developer with machine learning experience",
  "Data engineer with Apache Spark and AWS, 5+ years",
  "Full stack React and Node.js developer, open to work immediately",
  "ML engineer with NLP and LLM experience, Bangalore",
  "DevOps engineer with Kubernetes and Terraform expertise",
];

export default function QueryInput({ onSearch, loading }) {
  const [query, setQuery] = useState("");
  const [topK, setTopK] = useState(20);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!query.trim()) return;
    onSearch(query, topK);
  };

  return (
    <div className="space-y-4">
      {/* Search bar */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <div className="flex-1 relative">
          <Search
            size={18}
            className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-400"
          />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Describe the candidate you're looking for..."
            className="input-field pl-11"
            disabled={loading}
          />
        </div>
        <select
          value={topK}
          onChange={(e) => setTopK(Number(e.target.value))}
          className="input-field w-28"
          disabled={loading}
        >
          <option value={10}>Top 10</option>
          <option value={20}>Top 20</option>
          <option value={50}>Top 50</option>
          <option value={100}>Top 100</option>
        </select>
        <button type="submit" className="btn-primary" disabled={loading || !query.trim()}>
          {loading ? (
            <span className="animate-spin">⟳</span>
          ) : (
            <Search size={18} />
          )}
          {loading ? "Searching..." : "Search"}
        </button>
      </form>

      {/* Example queries */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-gray-500 flex items-center gap-1 mr-1">
          <Sparkles size={12} className="text-accent-400" />
          Try:
        </span>
        {EXAMPLE_QUERIES.map((q, i) => (
          <button
            key={i}
            onClick={() => setQuery(q)}
            className="text-xs bg-white/5 hover:bg-white/10 border border-white/10
                       text-gray-300 px-3 py-1 rounded-full transition-all duration-200
                       hover:border-primary-500/50 hover:text-primary-300"
            disabled={loading}
          >
            {q.length > 50 ? q.slice(0, 50) + "..." : q}
          </button>
        ))}
      </div>
    </div>
  );
}