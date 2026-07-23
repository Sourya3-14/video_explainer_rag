// src/components/Login.jsx
import React from "react";
import { GoogleLogin } from "@react-oauth/google";
import api from "../api";

export default function Login({ onLoginSuccess }) {
  const handleGoogleSuccess = async (credentialResponse) => {
    try {
      // 1. Send Google ID Token to backend endpoint
      const response = await api.post("/auth/google", {
        google_token: credentialResponse.credential,
      });

      const { access_token, user } = response.data;

      // 2. Save JWT token & user info in localStorage
      localStorage.setItem("token", access_token);
      localStorage.setItem("user", JSON.stringify(user));

      // 3. Notify parent app state
      onLoginSuccess(user);
    } catch (error) {
      console.error("Google backend authentication failed:", error);
      alert("Authentication failed. Please try again.");
    }
  };

  return (
    <div
      className="login-container"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        marginTop: "100px",
      }}
    >
      <h2>Welcome to Multimodal RAG Video Q&A</h2>
      <p style={{ color: "#666", marginBottom: "20px" }}>
        Sign in to access your video sessions
      </p>

      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={() => console.error("Google Sign-In Failed")}
      />
    </div>
  );
}
