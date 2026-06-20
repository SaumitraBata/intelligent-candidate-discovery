// src/components/Header.jsx
import { Link, useLocation } from "react-router-dom";

export default function Header() {
  const { pathname } = useLocation();

  return (
    <header className="border-b border-neutral-900 bg-neutral-950/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between">

        {/* Logo */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-7 h-7 rounded-md bg-gradient-to-br from-neutral-100 to-neutral-300 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" className="text-neutral-900">
              <path d="M12 2L2 7l10 5 10-5-10-5z" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
              <path d="M2 17l10 5 10-5M2 12l10 5 10-5" stroke="currentColor" strokeWidth="2" strokeLinejoin="round"/>
            </svg>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="font-semibold text-neutral-100 text-sm tracking-tight">
              CandidateIQ
            </span>
            <span className="text-[11px] text-neutral-600 hidden sm:inline">
              v1.0
            </span>
          </div>
        </Link>

        {/* Nav */}
        <nav className="hidden md:flex items-center gap-1">
          {[
            { to: "/",        label: "Search" },
            { to: "/results", label: "Results" },
          ].map((item) => (
            <Link
              key={item.to}
              to={item.to}
              className={`text-[13px] px-3 py-1.5 rounded-md transition-colors ${
                pathname === item.to
                  ? "text-neutral-100 bg-neutral-900"
                  : "text-neutral-500 hover:text-neutral-200"
              }`}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        {/* Right */}
        <div className="flex items-center gap-3">
          <a
            href="#"
            className="text-neutral-500 hover:text-neutral-300 transition-colors"
            title="GitHub"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.3 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.4 3-.405 1.02.005 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 21.795 24 17.3 24 12c0-6.63-5.37-12-12-12z"/>
            </svg>
          </a>

          {/* Status pill */}
          <div className="flex items-center gap-1.5 bg-neutral-900 border border-neutral-800 rounded-full px-2.5 py-1">
            <span className="relative flex w-1.5 h-1.5">
              <span className="absolute inset-0 rounded-full bg-emerald-500 animate-ping opacity-75" />
              <span className="relative w-1.5 h-1.5 rounded-full bg-emerald-500" />
            </span>
            <span className="text-[11px] text-neutral-400 font-medium">
              Ready
            </span>
          </div>
        </div>
      </div>
    </header>
  );
}