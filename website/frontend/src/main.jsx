// import React from "react";
// import ReactDOM from "react-dom/client";
// import App from "./App";

// ReactDOM.createRoot(document.getElementById("root")).render(
  //   <React.StrictMode>
  //     <App />
  //   </React.StrictMode>,
  // );
  
  // src/main.jsx or src/index.js
  import React from 'react';
  import ReactDOM from 'react-dom/client';
  import { GoogleOAuthProvider } from '@react-oauth/google';
  import App from './App';
  import "./styles.css";

// Replace with your Google OAuth Client ID
// ✅ Correct: Load dynamically from your .env file
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

// Log it to verify it loads correctly
console.log("Client ID:", GOOGLE_CLIENT_ID);

// If the log above prints 'undefined' or a string with quotes/spaces around it, Google fails.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <App />
    </GoogleOAuthProvider>
  </React.StrictMode>
);