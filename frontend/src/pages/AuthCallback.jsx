import React, { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { toast } from "sonner";

export default function AuthCallback() {
  const navigate = useNavigate();
  const { setUser } = useAuth();
  const processedRef = useRef(false);

  useEffect(() => {
    if (processedRef.current) return;
    processedRef.current = true;

    const hash = window.location.hash || "";
    const params = new URLSearchParams(hash.replace(/^#/, ""));
    const sessionId = params.get("session_id");

    if (!sessionId) {
      navigate("/login", { replace: true });
      return;
    }

    (async () => {
      try {
        const { data } = await api.post("/auth/google-session", { session_id: sessionId });
        setUser(data.user);
        toast.success("Selamat datang di Sanctuary");
        // Clear hash and go home
        window.history.replaceState(null, "", window.location.pathname);
        navigate("/", { replace: true });
      } catch (e) {
        toast.error("Login Google gagal. Silakan coba lagi.");
        navigate("/login", { replace: true });
      }
    })();
  }, [navigate, setUser]);

  return (
    <div className="min-h-screen botanical-bg grid place-items-center text-white">
      <div className="relative z-10 text-center" data-testid="auth-callback-loading">
        <div className="w-12 h-12 rounded-2xl bg-white/20 backdrop-blur mx-auto mb-4 grid place-items-center font-semibold">E</div>
        <div className="font-medium tracking-wide">Menyelaraskan sanctuary kamu…</div>
      </div>
    </div>
  );
}
