import axios from "axios";

// Read API URL from environment variable or default to local backend
const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api";

const api = axios.create({
  baseURL: API_BASE_URL,
});

// Sets or clears the global Authorization header on the Axios instance.
export const setAuthToken = (token) => {
  if (token) {
    api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
  } else {
    delete api.defaults.headers.common["Authorization"];
  }
};

// Builds the media streaming URL for a session video.
export const getSessionVideoUrl = (sessionId, token) => {
  const queryParam = token ? `?token=${encodeURIComponent(token)}` : "";
  return `${API_BASE_URL}/sessions/${sessionId}/video${queryParam}`;
};

// Google OAuth login endpoint.
export const loginWithGoogle = async (googleToken) => {
  const response = await axios.post(`${API_BASE_URL}/auth/google`, {
    google_token: googleToken,
  });
  return response.data; // Expected { access_token, user }
};

// Fetch all sessions for the logged-in user.
export const fetchSessions = async () => {
  const response = await api.get("/sessions");
  return Array.isArray(response.data)
    ? response.data
    : response.data?.sessions || [];
};

// Create a new session (with or without video/YouTube URL).
export const createSession = async ({ title, file, youtubeUrl }) => {
  const formData = new FormData();
  if (title) formData.append("title", title);
  if (file) formData.append("file", file);
  if (youtubeUrl) formData.append("youtube_url", youtubeUrl);

  const response = await api.post("/sessions", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
};

//  Send a question message to an active session.
export const sendMessage = async (sessionId, question) => {
  const response = await api.post(`/sessions/${sessionId}/messages`, {
    question,
  });
  return response.data;
};

export default api;
