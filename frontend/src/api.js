import axios from "axios";

export const api = axios.create({
  baseURL: "/api",
});

export async function fetchReview(period, limit = 20) {
  const { data } = await api.get("/review", { params: { period, limit } });
  return data;
}

export async function fetchEntries() {
  const { data } = await api.get("/entries", { params: { limit: 200 } });
  return data;
}

export async function createEntry(payload) {
  const { data } = await api.post("/entries", payload);
  return data;
}

export async function fetchStats() {
  const { data } = await api.get("/stats/overview");
  return data;
}

export async function exportData() {
  const { data } = await api.get("/io/export");
  return data;
}

export async function importData(file) {
  const formData = new FormData();
  formData.append("file", file);
  const { data } = await api.post("/io/import", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function getWordAudioUrl(word) {
  const { data } = await api.get(`/audio/word/${encodeURIComponent(word)}`);
  return data.url;
}

export async function getSentenceAudioBlob(text, entryId = null) {
  const response = await api.post(
    "/audio/sentence",
    { text, entry_id: entryId },
    { responseType: "blob" }
  );
  return response.data;
}
