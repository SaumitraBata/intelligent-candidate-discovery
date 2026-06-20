import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  timeout: 120000, // 2 min for full ranking
});

export const searchCandidates = (query, topK = 20, filters = {}) =>
  api.post("/search", { query, top_k: topK, filters });

export const rankByJDText = (jdText, topK = 100, filters = {}, sessionId = null) =>
  api.post("/rank", {
    jd_text: jdText,
    top_k: topK,
    filters,
    session_id: sessionId,
  });

export const uploadJD = (file, topK = 100, sessionId = null) => {
  const form = new FormData();
  form.append("file", file);
  form.append("top_k", topK);
  if (sessionId) form.append("session_id", sessionId);
  return api.post("/upload-jd", form, {
    headers: { "Content-Type": "multipart/form-data" },
  });
};

export const exportResults = (candidates) =>
  api.post("/export", candidates, { responseType: "blob" });

export const getCandidateDetail = (id) => api.get(`/candidate/${id}`);

export const getStats = () => api.get("/stats");

export const healthCheck = () => api.get("/health");

export default api;