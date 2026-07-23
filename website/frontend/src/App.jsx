import React, { useEffect, useState } from "react";
import axios from "axios";
import { GoogleLogin, googleLogout } from "@react-oauth/google";
import {
  FiChevronLeft,
  FiChevronRight,
  FiPlus,
  FiRefreshCw,
  FiSend,
  FiUpload,
  FiVideo,
  FiLogOut,
  FiX,
  FiLock,
} from "react-icons/fi";
import { FcGoogle } from "react-icons/fc";

const STORAGE_KEY = "multimodal_rag_state";
const AUTH_TOKEN_KEY = "multimodal_rag_token";
const AUTH_USER_KEY = "multimodal_rag_user";

const createDefaultSessionTitle = () => {
  const now = new Date();
  return `Session ${now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`;
};

const getSessionDisplayTitle = (session) => {
  if (session && Array.isArray(session.messages)) {
    const firstUserMsg = session.messages.find(
      (m) => m && m.role === "user" && m.content && m.content.trim(),
    );
    if (firstUserMsg) {
      const text = firstUserMsg.content.trim();
      return text.length > 24 ? text.substring(0, 24) + "..." : text;
    }
  }
  return session?.title || session?.name || createDefaultSessionTitle();
};

const api = axios.create({ baseURL: "http://127.0.0.1:8000/api" });

function App() {
  const [user, setUser] = useState(() => {
    const savedUser = window.localStorage.getItem(AUTH_USER_KEY);
    return savedUser ? JSON.parse(savedUser) : null;
  });

  const [token, setToken] = useState(() => {
    return window.localStorage.getItem(AUTH_TOKEN_KEY) || "";
  });

  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(() => {
    const cached = window.localStorage.getItem(STORAGE_KEY);
    if (cached) {
      try {
        return JSON.parse(cached).activeSessionId || "";
      } catch (e) {
        return "";
      }
    }
    return "";
  });

  const [videoFile, setVideoFile] = useState(null);
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [message, setMessage] = useState("");
  const [chat, setChat] = useState([]);
  const [loading, setLoading] = useState(false);
  const [videoUrl, setVideoUrl] = useState("");
  const [videoSourceType, setVideoSourceType] = useState("upload");
  const [sessionName, setSessionName] = useState("");
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  const getSessionVideoUrl = (sessionId) =>
    token
      ? `http://127.0.0.1:8000/api/sessions/${sessionId}/video?token=${encodeURIComponent(
          token,
        )}`
      : `http://127.0.0.1:8000/api/sessions/${sessionId}/video`;

  // State to control Login Modal Popup
  const [showAuthModal, setShowAuthModal] = useState(false);

  // Set Auth Header whenever token changes
  useEffect(() => {
    if (token) {
      api.defaults.headers.common["Authorization"] = `Bearer ${token}`;
      window.localStorage.setItem(AUTH_TOKEN_KEY, token);
    } else {
      delete api.defaults.headers.common["Authorization"];
      window.localStorage.removeItem(AUTH_TOKEN_KEY);
    }
  }, [token]);

  // Load sessions when authenticated user is present
  useEffect(() => {
    if (user && token) {
      loadSessions();
    } else {
      // Clear or show demo state for unauthenticated viewers
      setSessions([]);
      setChat([]);
    }
  }, [user, token]);

  useEffect(() => {
    if (user) {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          activeSessionId,
          chat,
          videoUrl,
          videoSourceType,
          sessionName,
        }),
      );
    }
  }, [activeSessionId, chat, videoUrl, videoSourceType, sessionName, user]);

  const handleGoogleSuccess = async (credentialResponse) => {
    setLoading(true);
    try {
      const response = await axios.post(
        "http://127.0.0.1:8000/api/auth/google",
        {
          google_token: credentialResponse.credential,
        },
      );

      const { access_token, user: loggedInUser } = response.data;

      setToken(access_token);
      setUser(loggedInUser);
      window.localStorage.setItem(AUTH_USER_KEY, JSON.stringify(loggedInUser));
      setShowAuthModal(false); // Close login modal after successful auth
    } catch (error) {
      console.error("Google authentication failed:", error);
      alert("Authentication failed. Please check backend logs.");
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => {
    googleLogout();
    setToken("");
    setUser(null);
    setSessions([]);
    setChat([]);
    setActiveSessionId("");
    setVideoUrl("");
    window.localStorage.removeItem(AUTH_TOKEN_KEY);
    window.localStorage.removeItem(AUTH_USER_KEY);
    window.localStorage.removeItem(STORAGE_KEY);
  };

  const loadSessions = async () => {
    try {
      const response = await api.get("/sessions");
      const fetchedSessions = Array.isArray(response.data)
        ? response.data
        : response.data?.sessions || [];

      setSessions(fetchedSessions);

      if (fetchedSessions.length > 0) {
        const stored = window.localStorage.getItem(STORAGE_KEY);
        const savedId = stored
          ? JSON.parse(stored).activeSessionId
          : activeSessionId;

        const matchedSession = fetchedSessions.find(
          (s) => (s.id || s._id || s.session_id) === savedId,
        );

        if (matchedSession) {
          const targetId =
            matchedSession.id ||
            matchedSession._id ||
            matchedSession.session_id;
          setActiveSessionId(targetId);
          setChat(matchedSession.messages || []);
          setVideoSourceType(matchedSession.source_type || "upload");
          setVideoUrl(
            matchedSession.source_type === "youtube"
              ? matchedSession.source_url || ""
              : matchedSession.video_path
                ? getSessionVideoUrl(targetId)
                : matchedSession.source_url || "",
          );
          setSessionName(getSessionDisplayTitle(matchedSession));
        } else {
          const firstSession = fetchedSessions[0];
          const firstId =
            firstSession.id || firstSession._id || firstSession.session_id;

          setActiveSessionId(firstId);
          setChat(firstSession.messages || []);
          setVideoSourceType(firstSession.source_type || "upload");
          setVideoUrl(
            firstSession.source_type === "youtube"
              ? firstSession.source_url || ""
              : firstSession.video_path
                ? getSessionVideoUrl(firstId)
                : firstSession.source_url || "",
          );
          setSessionName(getSessionDisplayTitle(firstSession));
        }
      }
    } catch (error) {
      console.error("Failed to load sessions:", error);
      if (error.response?.status === 401) {
        handleLogout();
      }
    }
  };

  // Interceptor: Guards actions that require login
  const requireAuth = (actionCallback) => {
    if (!user || !token) {
      setShowAuthModal(true);
      return;
    }
    actionCallback();
  };

  const createNewSession = () => {
    requireAuth(async () => {
      setLoading(true);
      try {
        const formData = new FormData();
        const defaultTitle = createDefaultSessionTitle();
        formData.append("title", defaultTitle);

        const response = await api.post("/sessions", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });

        const newSession = response.data;
        const newId = newSession.id || newSession._id || newSession.session_id;

        setSessions((prev) => [newSession, ...prev]);
        setActiveSessionId(newId);
        setChat([]);
        setVideoFile(null);
        setYoutubeUrl("");
        setVideoUrl("");
        setVideoSourceType("upload");
        setSessionName(defaultTitle);
        setMessage("");
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    });
  };

  const uploadVideo = (event) => {
    event.preventDefault();
    requireAuth(async () => {
      if (!videoFile && !youtubeUrl.trim()) return;

      setLoading(true);
      const formData = new FormData();
      if (videoFile) formData.append("file", videoFile);
      if (youtubeUrl.trim()) formData.append("youtube_url", youtubeUrl.trim());

      try {
        const response = await api.post("/sessions", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        const nextSession = response.data;
        const nextId =
          nextSession.id || nextSession._id || nextSession.session_id;

        setSessions((prev) => [nextSession, ...prev]);
        setActiveSessionId(nextId);
        setChat(nextSession.messages || []);

        if (nextSession.source_type === "youtube") {
          setVideoUrl(nextSession.source_url || "");
          setVideoSourceType("youtube");
        } else if (videoFile) {
          setVideoUrl(getSessionVideoUrl(nextId));
          setVideoSourceType("upload");
        }

        setYoutubeUrl("");
        setSessionName(getSessionDisplayTitle(nextSession));
      } catch (error) {
        console.error(error);
      } finally {
        setLoading(false);
      }
    });
  };

  const sendQuestion = (event) => {
    event.preventDefault();
    requireAuth(async () => {
      if (!activeSessionId || !message.trim()) return;

      const question = message.trim();
      setMessage("");

      const updatedChat = [...chat, { role: "user", content: question }];
      setChat(updatedChat);

      setSessions((prev) =>
        prev.map((s) => {
          const sId = s.id || s._id || s.session_id;
          if (sId === activeSessionId) {
            return { ...s, messages: updatedChat };
          }
          return s;
        }),
      );

      try {
        const response = await api.post(
          `/sessions/${activeSessionId}/messages`,
          { question },
        );

        const fullChat = [
          ...updatedChat,
          {
            role: "assistant",
            content: response.data.answer || response.data.content,
          },
        ];

        setChat(fullChat);

        setSessions((prev) =>
          prev.map((s) => {
            const sId = s.id || s._id || s.session_id;
            if (sId === activeSessionId) {
              return { ...s, messages: fullChat };
            }
            return s;
          }),
        );
      } catch (error) {
        console.error(error);
        setChat((prev) => [
          ...prev,
          {
            role: "assistant",
            content: "The request failed. Please try again.",
          },
        ]);
      }
    });
  };

  return (
    <div className="flex h-screen w-full bg-[#070a11] text-slate-100 font-sans overflow-hidden relative">
      <div
        className="fixed inset-0 pointer-events-none opacity-20"
        style={{
          backgroundImage: `radial-gradient(#34d399 1px, transparent 1px)`,
          backgroundSize: "24px 24px",
        }}
      />

      {/* COLLAPSIBLE SIDEBAR */}
      <aside
        className={`relative z-10 flex flex-col border-r border-slate-800 bg-[#0b0f19]/90 backdrop-blur-md transition-all duration-300 ease-in-out ${
          isSidebarOpen ? "w-72" : "w-16"
        }`}
      >
        <div className="flex items-center justify-between p-4 border-b border-slate-800">
          {isSidebarOpen && (
            <h2 className="text-lg font-bold tracking-tight text-emerald-400">
              Sessions ({sessions.length})
            </h2>
          )}
          <button
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="p-2 text-slate-400 rounded-lg hover:bg-slate-800 hover:text-white transition-colors"
            title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {isSidebarOpen ? (
              <FiChevronLeft size={20} />
            ) : (
              <FiChevronRight size={20} />
            )}
          </button>
        </div>

        <div className="p-3 space-y-2">
          <button
            onClick={createNewSession}
            className="flex items-center justify-center w-full gap-2 px-3 py-2 text-sm font-semibold text-slate-900 bg-emerald-400 hover:bg-emerald-300 rounded-lg shadow-lg shadow-emerald-950/40 transition-all"
          >
            <FiPlus size={18} />
            {isSidebarOpen && <span>New Session</span>}
          </button>

          {isSidebarOpen && user && (
            <button
              onClick={loadSessions}
              className="flex items-center justify-center w-full gap-2 px-3 py-2 text-xs font-medium text-slate-400 border border-slate-800 hover:border-slate-700 hover:text-slate-200 rounded-lg transition-all"
            >
              <FiRefreshCw size={14} />
              <span>Refresh Sessions</span>
            </button>
          )}
        </div>

        {/* Sessions List */}
        <div className="flex-1 overflow-y-auto px-3 py-2 space-y-2">
          {sessions.length === 0
            ? isSidebarOpen && (
                <p className="text-xs text-slate-500 text-center py-4">
                  {user
                    ? "No sessions found."
                    : "Sign in to access your chat history."}
                </p>
              )
            : sessions.map((session, idx) => {
                const sessionId =
                  session.id || session._id || session.session_id || idx;
                const sessionTitle = getSessionDisplayTitle(session);
                const isSelected = sessionId === activeSessionId;

                return (
                  <button
                    key={sessionId}
                    onClick={() => {
                      setActiveSessionId(sessionId);
                      setChat(
                        (session.messages || []).filter(
                          (entry) =>
                            entry && entry.content && entry.content.trim(),
                        ),
                      );
                      setVideoSourceType(session.source_type || "upload");
                      setVideoUrl(
                        session.source_type === "youtube"
                          ? session.source_url || ""
                          : session.video_path
                            ? getSessionVideoUrl(sessionId)
                            : session.source_url || "",
                      );
                      setSessionName(sessionTitle);
                    }}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      isSelected
                        ? "bg-slate-800/80 border-emerald-500/50 text-white shadow-md shadow-emerald-950/20"
                        : "bg-slate-900/40 border-slate-800/60 text-slate-400 hover:bg-slate-800/40 hover:text-slate-200"
                    }`}
                  >
                    {isSidebarOpen ? (
                      <>
                        <div className="font-semibold text-sm truncate text-slate-100">
                          {sessionTitle}
                        </div>
                        {session.video_title && (
                          <div className="text-xs text-slate-500 truncate mt-1">
                            {session.video_title}
                          </div>
                        )}
                      </>
                    ) : (
                      <div className="flex justify-center">
                        <FiVideo
                          size={18}
                          className={
                            isSelected ? "text-emerald-400" : "text-slate-500"
                          }
                        />
                      </div>
                    )}
                  </button>
                );
              })}
        </div>
      </aside>

      {/* MAIN CONTENT AREA */}
      <main className="relative z-10 flex-1 flex flex-col h-full overflow-hidden p-6 gap-6 max-w-7xl mx-auto w-full">
        <header className="flex items-center justify-between">
          <div>
            {/* <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-emerald-500/30 bg-emerald-500/10 text-emerald-400 text-xs font-semibold uppercase tracking-wider mb-2">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Multimodal RAG Live
            </div> */}
            <h1 className="text-3xl font-extrabold tracking-tight text-white sm:text-4xl">
              Video Q&A <span className="text-emerald-400">Center</span>
            </h1>
          </div>

          {/* User Profile or Sign In CTA */}
          {user ? (
            <div className="flex items-center gap-3 bg-slate-900/80 border border-slate-800 px-3 py-1.5 rounded-2xl">
              {user.picture && (
                <img
                  src={user.picture}
                  alt={user.name}
                  className="w-7 h-7 rounded-full border border-emerald-400/50"
                />
              )}
              <span className="text-xs font-medium text-slate-300 hidden sm:inline">
                {user.name}
              </span>
              <button
                onClick={handleLogout}
                className="p-1.5 text-slate-400 hover:text-red-400 hover:bg-slate-800 rounded-lg transition-all"
                title="Sign Out"
              >
                <FiLogOut size={16} />
              </button>
            </div>
          ) : (
            <button
              onClick={() => setShowAuthModal(true)}
              className="flex items-center gap-2 px-4 py-2 text-xs font-semibold text-slate-950 bg-emerald-400 hover:bg-emerald-300 rounded-xl shadow-lg transition-all"
            >
              <FcGoogle size={18} />
              <span>Sign in with Google</span>
            </button>
          )}
        </header>

        {/* Upload Form */}
        <section className="bg-slate-900/60 border border-slate-800 rounded-2xl p-4 backdrop-blur-sm">
          <form
            onSubmit={uploadVideo}
            className="flex flex-wrap items-center gap-3"
          >
            <label
              onClick={(e) => {
                if (!user) {
                  e.preventDefault();
                  setShowAuthModal(true);
                }
              }}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-slate-800 border border-slate-700 hover:border-slate-600 rounded-xl text-xs font-medium cursor-pointer text-slate-300 hover:text-white transition-all"
            >
              <FiUpload size={16} />
              <span className="truncate max-w-[120px]">
                {videoFile ? videoFile.name : "Upload File"}
              </span>
              <input
                type="file"
                accept="video/*"
                className="hidden"
                disabled={!user}
                onChange={(e) => setVideoFile(e.target.files?.[0] || null)}
              />
            </label>

            <input
              type="text"
              placeholder="Paste YouTube link..."
              value={youtubeUrl}
              onClick={() => !user && setShowAuthModal(true)}
              onChange={(e) => setYoutubeUrl(e.target.value)}
              className="flex-1 min-w-[200px] bg-slate-950/60 border border-slate-800 focus:border-emerald-500 focus:outline-none px-3 py-2 rounded-xl text-xs text-slate-200 placeholder-slate-500 transition-all"
            />

            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 bg-emerald-400 hover:bg-emerald-300 text-slate-950 font-semibold text-xs rounded-xl shadow-md transition-all disabled:opacity-50"
            >
              {loading ? "Processing..." : "Load Video"}
            </button>
          </form>
        </section>

        {/* Video & Chat Grid */}
        <section className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-0">
          {/* Video Player */}
          <div className="lg:col-span-6 flex flex-col bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden p-4 backdrop-blur-sm">
            <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-slate-950 flex items-center justify-center border border-slate-800/80 shadow-inner">
              {videoUrl && videoSourceType === "youtube" ? (
                <iframe
                  className="w-full h-full object-cover"
                  src={`https://www.youtube.com/embed/${
                    new URL(videoUrl).searchParams.get("v") ||
                    videoUrl.split("/").pop()
                  }`}
                  title="YouTube video"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              ) : videoUrl ? (
                <video
                  controls
                  src={videoUrl}
                  className="w-full h-full object-contain"
                />
              ) : (
                <div className="flex flex-col items-center gap-3 text-slate-500 p-6 text-center">
                  <FiVideo size={40} className="stroke-1 text-slate-600" />
                  <p className="text-xs max-w-xs">
                    Upload a video file or paste a YouTube link above to
                    initialize the player.
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Chat Panel */}
          <div className="lg:col-span-6 flex flex-col bg-slate-900/60 border border-slate-800 rounded-2xl overflow-hidden backdrop-blur-sm">
            <div className="flex-1 p-4 overflow-y-auto space-y-4">
              {chat.length === 0 ? (
                <div className="h-full flex items-center justify-center text-xs text-slate-500">
                  Ask a question to start the conversation...
                </div>
              ) : (
                chat.map((entry, index) => (
                  <div
                    key={`${entry.role}-${index}`}
                    className={`flex flex-col ${
                      entry.role === "user" ? "items-end" : "items-start"
                    }`}
                  >
                    <span className="text-[10px] text-slate-500 mb-1 px-1">
                      {entry.role === "user" ? "You" : "Assistant"}
                    </span>
                    <div
                      className={`max-w-[80%] rounded-2xl px-4 py-2.5 text-xs leading-relaxed ${
                        entry.role === "user"
                          ? "bg-emerald-400 text-slate-950 font-medium rounded-tr-none shadow-md"
                          : "bg-slate-950/80 text-slate-200 border border-slate-800 rounded-tl-none"
                      }`}
                    >
                      {entry.content}
                    </div>
                  </div>
                ))
              )}
            </div>

            <form
              onSubmit={sendQuestion}
              className="p-3 border-t border-slate-800/80 bg-slate-950/40 flex items-center gap-2"
            >
              <input
                type="text"
                placeholder="Ask a question about the video..."
                value={message}
                onClick={() => !user && setShowAuthModal(true)}
                onChange={(e) => setMessage(e.target.value)}
                className="flex-1 bg-slate-900 border border-slate-800 focus:border-emerald-500 focus:outline-none px-4 py-2.5 rounded-xl text-xs text-slate-200 placeholder-slate-500 transition-all"
              />
              <button
                type="submit"
                className="p-2.5 bg-emerald-400 hover:bg-emerald-300 text-slate-950 rounded-xl transition-all shadow-md"
              >
                <FiSend size={16} />
              </button>
            </form>
          </div>
        </section>
      </main>

      {/* SIGN IN POPUP / MODAL */}
      {showAuthModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-fade-in">
          <div className="relative flex flex-col items-center bg-slate-900 border border-slate-800 p-8 rounded-3xl shadow-2xl max-w-sm w-full text-center">
            <button
              onClick={() => setShowAuthModal(false)}
              className="absolute top-4 right-4 p-2 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
            >
              <FiX size={18} />
            </button>

            <div className="p-3 bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 rounded-2xl mb-4">
              <FiLock size={24} />
            </div>

            <h3 className="text-xl font-bold text-white mb-2">
              Sign In Required
            </h3>
            <p className="text-xs text-slate-400 mb-6">
              Please sign in with Google to upload videos, generate session AI
              contexts, and ask questions.
            </p>

            <GoogleLogin
              onSuccess={handleGoogleSuccess}
              onError={() => alert("Google Login Failed")}
              theme="filled_black"
              shape="pill"
            />
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
