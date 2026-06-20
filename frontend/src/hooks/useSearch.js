import { useState, useCallback } from "react";
import { v4 as uuidv4 } from "uuid";
import {
  searchCandidates,
  rankByJDText,
  uploadJD,
} from "../api/client";

export function useSearch() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [jdRequirements, setJdRequirements] = useState(null);

  const reset = useCallback(() => {
    setResults(null);
    setError(null);
    setJdRequirements(null);
  }, []);

  const runSearch = useCallback(async (query, topK, filters) => {
    setLoading(true);
    setError(null);
    try {
      const { data } = await searchCandidates(query, topK, filters);
      setResults(data.candidates);
      setJdRequirements(data.jd_requirements);
      return data;
    } catch (e) {
      const msg = e.response?.data?.detail || e.message;
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const runRanking = useCallback(async (jdText, topK, filters) => {
    const sid = uuidv4();
    setSessionId(sid);
    setLoading(true);
    setError(null);
    try {
      const { data } = await rankByJDText(jdText, topK, filters, sid);
      setResults(data.candidates);
      setJdRequirements(data.jd_requirements);
      return data;
    } catch (e) {
      const msg = e.response?.data?.detail || e.message;
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const runUpload = useCallback(async (file, topK) => {
    const sid = uuidv4();
    setSessionId(sid);
    setLoading(true);
    setError(null);
    try {
      const { data } = await uploadJD(file, topK, sid);
      setResults(data.candidates);
      setJdRequirements(data.jd_requirements);
      return data;
    } catch (e) {
      const msg = e.response?.data?.detail || e.message;
      setError(msg);
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    results,
    loading,
    error,
    sessionId,
    jdRequirements,
    runSearch,
    runRanking,
    runUpload,
    reset,
  };
}