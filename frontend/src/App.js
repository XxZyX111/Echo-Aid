import React from "react";
import { BrowserRouter, Routes, Route, Navigate, useLocation } from "react-router-dom";
import { AuthProvider, useAuth } from "@/lib/auth";
import { Toaster } from "@/components/ui/sonner";
import "@/App.css";
import "leaflet/dist/leaflet.css";

import Login from "@/pages/Login";
import Register from "@/pages/Register";
import VerifyEmail from "@/pages/VerifyEmail";
import AuthCallback from "@/pages/AuthCallback";
import Layout from "@/components/Layout";
import Home from "@/pages/Home";
import JournalPage from "@/pages/JournalPage";
import HealingMapPage from "@/pages/HealingMapPage";
import MeditationPage from "@/pages/MeditationPage";
import ConsultationPage from "@/pages/ConsultationPage";
import EchoChatPage from "@/pages/EchoChatPage";
import ProfilePage from "@/pages/ProfilePage";
import SettingsPage from "@/pages/SettingsPage";
import SupportPage from "@/pages/SupportPage";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F4F7F4]">
        <div className="text-[#2D5F5F] font-medium tracking-wide">Memuat sanctuary…</div>
      </div>
    );
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AppRouter() {
  const location = useLocation();
  // Handle OAuth callback first (URL fragment)
  if (location.hash?.includes("session_id=")) {
    return <AuthCallback />;
  }
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/verify-email" element={<VerifyEmail />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Home />} />
        <Route path="journal" element={<JournalPage />} />
        <Route path="healing-map" element={<HealingMapPage />} />
        <Route path="meditation" element={<MeditationPage />} />
        <Route path="consultation" element={<ConsultationPage />} />
        <Route path="echochat" element={<EchoChatPage />} />
        <Route path="echochat/:bookingId" element={<EchoChatPage />} />
        <Route path="profile" element={<ProfilePage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="support" element={<SupportPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRouter />
          <Toaster richColors position="top-right" />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}
