// src/components/ui/candidate-search-input.jsx
"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { cn } from "../../lib/utils";
import {
  ArrowRight, Paperclip, Command,
  Code2, MapPin, Briefcase, Zap, Users, Award,
} from "lucide-react";
import * as React from "react";

function useAutoResizeTextarea({ minHeight, maxHeight }) {
  const textareaRef = useRef(null);

  const adjustHeight = useCallback(
    (reset) => {
      const textarea = textareaRef.current;
      if (!textarea) return;
      if (reset) { textarea.style.height = `${minHeight}px`; return; }
      textarea.style.height = `${minHeight}px`;
      const newHeight = Math.max(
        minHeight,
        Math.min(textarea.scrollHeight, maxHeight ?? Number.POSITIVE_INFINITY)
      );
      textarea.style.height = `${newHeight}px`;
    },
    [minHeight, maxHeight]
  );

  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) textarea.style.height = `${minHeight}px`;
  }, [minHeight]);

  useEffect(() => {
    const handleResize = () => adjustHeight();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, [adjustHeight]);

  return { textareaRef, adjustHeight };
}

const COMMAND_SUGGESTIONS = [
  { icon: Code2, label: "skills",   description: "Specify required technologies", prefix: "/skills" },
  { icon: MapPin, label: "location", description: "Filter by geographic location", prefix: "/location" },
  { icon: Briefcase, label: "experience", description: "Set years of experience", prefix: "/exp" },
  { icon: Zap, label: "available",   description: "Show only open-to-work candidates", prefix: "/open" },
];

const QUICK_ACTIONS = [
  { label: "ML Engineer",   query: "Senior ML engineer with Python, TensorFlow and AWS, 5+ years experience" },
  { label: "Full Stack",    query: "Full stack developer with React and Node.js, open to work" },
  { label: "Data Engineer", query: "Data engineer with Apache Spark and cloud platforms, 4+ years" },
  { label: "Tech Lead",     query: "Engineering lead with 8+ years, distributed systems experience" },
];

export function CandidateSearchInput({
  onSearch, onUpload, loading = false, topK = 20, onTopKChange,
}) {
  const [value, setValue] = useState("");
  const [showCommands, setShowCommands] = useState(false);
  const [activeIdx, setActiveIdx] = useState(-1);
  const [isFocused, setIsFocused] = useState(false);
  const fileInputRef = useRef(null);
  const commandRef = useRef(null);

  const { textareaRef, adjustHeight } = useAutoResizeTextarea({
    minHeight: 76,
    maxHeight: 200,
  });

  useEffect(() => {
    if (value.startsWith("/") && !value.includes(" ")) {
      setShowCommands(true);
      const idx = COMMAND_SUGGESTIONS.findIndex((c) => c.prefix.startsWith(value));
      setActiveIdx(idx);
    } else {
      setShowCommands(false);
    }
  }, [value]);

  useEffect(() => {
    const handler = (e) => {
      const cmdBtn = document.querySelector("[data-command-button]");
      if (commandRef.current && !commandRef.current.contains(e.target) && !cmdBtn?.contains(e.target)) {
        setShowCommands(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const handleKeyDown = (e) => {
    if (showCommands) {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveIdx((p) => (p < COMMAND_SUGGESTIONS.length - 1 ? p + 1 : 0));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveIdx((p) => (p > 0 ? p - 1 : COMMAND_SUGGESTIONS.length - 1));
      } else if (e.key === "Tab" || e.key === "Enter") {
        e.preventDefault();
        if (activeIdx >= 0) {
          setValue(COMMAND_SUGGESTIONS[activeIdx].prefix + " ");
          setShowCommands(false);
        }
      } else if (e.key === "Escape") {
        setShowCommands(false);
      }
    } else if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (value.trim() && !loading) onSearch?.(value, topK);
    }
  };

  const handleQuickAction = (query) => {
    setValue(query);
    setTimeout(() => {
      adjustHeight();
      textareaRef.current?.focus();
    }, 0);
  };

  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload?.(file, topK);
  };

  return (
    <div className="w-full">

      {/* Input panel */}
      <div
        className={cn(
          "relative bg-neutral-900/30 backdrop-blur-md rounded-xl border transition-all duration-200",
          isFocused
            ? "border-neutral-700 shadow-[0_0_0_4px_rgba(255,255,255,0.02)]"
            : "border-neutral-800"
        )}
      >
        {/* Command palette */}
        {showCommands && (
          <div
            ref={commandRef}
            className="absolute left-3 right-3 bottom-full mb-2 bg-neutral-900 rounded-lg shadow-xl border border-neutral-800 overflow-hidden z-50 animate-fade-in"
          >
            <div className="px-3 py-2 border-b border-neutral-800 flex items-center gap-2">
              <span className="text-[10px] text-neutral-500 uppercase tracking-wider font-medium">
                Commands
              </span>
            </div>
            <div className="py-1">
              {COMMAND_SUGGESTIONS.map((s, i) => {
                const Icon = s.icon;
                const active = activeIdx === i;
                return (
                  <button
                    key={s.prefix}
                    onClick={() => {
                      setValue(s.prefix + " ");
                      setShowCommands(false);
                      textareaRef.current?.focus();
                    }}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2 text-left transition-colors",
                      active ? "bg-neutral-800/60" : "hover:bg-neutral-800/40"
                    )}
                  >
                    <Icon size={14} className="text-neutral-500" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-neutral-200">{s.label}</div>
                      <div className="text-[11px] text-neutral-500 truncate">
                        {s.description}
                      </div>
                    </div>
                    <span className="text-[10px] text-neutral-600 font-mono">
                      {s.prefix}
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => {
            setValue(e.target.value);
            adjustHeight();
          }}
          onKeyDown={handleKeyDown}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder="Describe the candidate you're looking for..."
          rows={3}
          className="w-full bg-transparent border-none px-5 pt-5 pb-3 text-[15px] text-neutral-100 placeholder:text-neutral-600 resize-none focus:outline-none leading-relaxed"
          style={{ overflow: "hidden" }}
        />

        {/* Toolbar */}
        <div className="flex items-center justify-between gap-2 px-3 py-2.5 border-t border-neutral-800/60">

          {/* Left actions */}
          <div className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[12px] text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/60 transition-colors"
              title="Upload job description"
            >
              <Paperclip size={13} />
              <span>Attach</span>
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".docx,.txt"
              className="hidden"
              onChange={handleFileUpload}
            />

            <button
              type="button"
              data-command-button
              onClick={(e) => {
                e.stopPropagation();
                if (!value.startsWith("/")) {
                  setValue("/");
                  setTimeout(() => textareaRef.current?.focus(), 0);
                }
              }}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-[12px] text-neutral-500 hover:text-neutral-200 hover:bg-neutral-800/60 transition-colors"
            >
              <Command size={13} />
              <span>Commands</span>
            </button>

            <div className="w-px h-4 bg-neutral-800 mx-1" />

            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md">
              <span className="text-[11px] text-neutral-600 uppercase tracking-wider">Limit</span>
              <select
                value={topK}
                onChange={(e) => onTopKChange?.(Number(e.target.value))}
                className="bg-transparent text-[12px] text-neutral-300 focus:outline-none cursor-pointer font-medium"
              >
                <option value={10} className="bg-neutral-900">10</option>
                <option value={20} className="bg-neutral-900">20</option>
                <option value={50} className="bg-neutral-900">50</option>
                <option value={100} className="bg-neutral-900">100</option>
              </select>
            </div>
          </div>

          {/* Send */}
          <button
            type="button"
            onClick={() => value.trim() && !loading && onSearch?.(value, topK)}
            disabled={!value.trim() || loading}
            className={cn(
              "inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-medium transition-all",
              value.trim() && !loading
                ? "bg-neutral-100 text-neutral-900 hover:bg-white"
                : "bg-neutral-800/60 text-neutral-600 cursor-not-allowed"
            )}
          >
            {loading ? (
              <>
                <span className="w-3 h-3 border-2 border-neutral-600 border-t-neutral-900 rounded-full animate-spin" />
                Searching
              </>
            ) : (
              <>
                Search
                <ArrowRight size={12} />
              </>
            )}
          </button>
        </div>
      </div>

      {/* Quick suggestions */}
      <div className="flex flex-wrap items-center justify-center gap-1.5 mt-5">
        {QUICK_ACTIONS.map((action) => (
          <button
            key={action.label}
            onClick={() => handleQuickAction(action.query)}
            className="text-[12px] text-neutral-500 hover:text-neutral-200 px-2.5 py-1 rounded-md hover:bg-neutral-900/60 transition-colors"
          >
            {action.label}
          </button>
        ))}
      </div>

      {/* Footer hints */}
      <div className="flex items-center justify-center gap-4 mt-6 text-[11px] text-neutral-600">
        <span className="flex items-center gap-1.5">
          <kbd className="kbd">↵</kbd>
          to search
        </span>
        <span className="text-neutral-800">·</span>
        <span className="flex items-center gap-1.5">
          <kbd className="kbd">⇧ ↵</kbd>
          new line
        </span>
        <span className="text-neutral-800">·</span>
        <span className="flex items-center gap-1.5">
          <kbd className="kbd">/</kbd>
          commands
        </span>
      </div>
    </div>
  );
}

export default CandidateSearchInput;