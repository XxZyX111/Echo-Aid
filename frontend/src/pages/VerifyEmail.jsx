import React, { useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { api, formatApiErrorDetail } from "@/lib/api";
import { Mail, CheckCircle2, AlertTriangle, ExternalLink, RefreshCw } from "lucide-react";
import { toast } from "sonner";

export default function VerifyEmail() {
  const navigate = useNavigate();
  const location = useLocation();
  const [search] = useSearchParams();
  const tokenInUrl = search.get("token");

  const stateEmail = location.state?.email || "";
  const stateDevUrl = location.state?.devUrl || "";
  const stateDevNote = location.state?.devNote || "";
  const needsResend = location.state?.needsResend || false;

  const [status, setStatus] = useState(tokenInUrl ? "verifying" : "info");
  // info | verifying | success | error
  const [errorMsg, setErrorMsg] = useState("");
  const [email, setEmail] = useState(stateEmail);
  const [resending, setResending] = useState(false);
  const [devUrl, setDevUrl] = useState(stateDevUrl);
  const verifiedOnceRef = useRef(false);

  // Auto-verify if token in URL
  useEffect(() => {
    if (!tokenInUrl || verifiedOnceRef.current) return;
    verifiedOnceRef.current = true;
    (async () => {
      try {
        const { data } = await api.post("/auth/verify-email", { token: tokenInUrl });
        setStatus("success");
        setEmail(data.email || "");
        toast.success("Email berhasil diverifikasi! Silakan login.");
      } catch (err) {
        setStatus("error");
        setErrorMsg(formatApiErrorDetail(err.response?.data?.detail) || err.message);
      }
    })();
  }, [tokenInUrl]);

  // Auto-resend if coming from login with unverified email
  useEffect(() => {
    if (needsResend && email && !devUrl) {
      handleResend();
    }
    // eslint-disable-next-line
  }, [needsResend]);

  const handleResend = async () => {
    if (!email) {
      toast.info("Masukkan email kamu");
      return;
    }
    setResending(true);
    try {
      const { data } = await api.post("/auth/resend-verification", { email });
      toast.success("Link verifikasi sudah dikirim ulang. Cek inbox kamu.");
      if (data.dev_verification_url) setDevUrl(data.dev_verification_url);
    } catch (err) {
      toast.error(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setResending(false);
    }
  };

  return (
    <div className="min-h-screen botanical-bg grid place-items-center px-4 py-10">
      <div className="relative z-10 w-full max-w-md fade-up" data-testid="verify-email-page">
        <div className="bg-white/95 backdrop-blur-xl rounded-[2rem] shadow-[0_24px_60px_rgba(28,48,43,0.18)] p-8 sm:p-10">
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-2xl bg-[#2D5F5F] grid place-items-center text-white">
              <span className="font-semibold text-lg">E</span>
            </div>
            <div>
              <div className="font-semibold text-lg text-[#1C302B]">EchoAid</div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-[#7A9690]">Sanctuary</div>
            </div>
          </div>

          {status === "verifying" && (
            <div className="text-center py-6" data-testid="verify-status-loading">
              <div className="w-14 h-14 mx-auto rounded-full bg-[#E8F0EA] grid place-items-center text-[#2D5F5F] animate-spin">
                <RefreshCw size={22} />
              </div>
              <h2 className="mt-5 text-2xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
                Memverifikasi email…
              </h2>
              <p className="text-sm text-[#4A635D] mt-2">Tunggu sebentar ya.</p>
            </div>
          )}

          {status === "success" && (
            <div className="text-center py-4" data-testid="verify-status-success">
              <div className="w-14 h-14 mx-auto rounded-full bg-[#E6F4EA] grid place-items-center text-[#2D5F5F]">
                <CheckCircle2 size={26} />
              </div>
              <h2 className="mt-5 text-2xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
                Email terverifikasi!
              </h2>
              <p className="text-sm text-[#4A635D] mt-2">Akun {email} siap digunakan. Yuk masuk ke Sanctuary kamu.</p>
              <button
                onClick={() => navigate("/login")}
                data-testid="goto-login-after-verify"
                className="mt-6 w-full rounded-full bg-[#2D5F5F] text-white py-3 font-medium hover:bg-[#244C4C] transition"
              >
                Masuk ke Sanctuary
              </button>
            </div>
          )}

          {status === "error" && (
            <div className="text-center py-4" data-testid="verify-status-error">
              <div className="w-14 h-14 mx-auto rounded-full bg-[#FCEFEB] grid place-items-center text-[#C06C5B]">
                <AlertTriangle size={26} />
              </div>
              <h2 className="mt-5 text-2xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
                Verifikasi gagal
              </h2>
              <p className="text-sm text-[#C06C5B] mt-2">{errorMsg}</p>
              <p className="text-sm text-[#4A635D] mt-3">Minta link verifikasi baru di bawah.</p>
              <div className="mt-5">
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="email@kamu.com"
                  className="w-full px-4 py-3 rounded-xl bg-[#F4F7F4] outline-none border border-transparent focus:border-[#2D5F5F] text-sm"
                  data-testid="resend-email-input"
                />
                <button
                  onClick={handleResend}
                  disabled={resending}
                  data-testid="resend-link-button"
                  className="mt-3 w-full rounded-full bg-[#2D5F5F] text-white py-3 font-medium hover:bg-[#244C4C] transition disabled:opacity-60"
                >
                  {resending ? "Mengirim…" : "Kirim Ulang Link"}
                </button>
              </div>
            </div>
          )}

          {status === "info" && (
            <div data-testid="verify-status-info">
              <div className="w-14 h-14 rounded-full bg-[#E8F0EA] grid place-items-center text-[#2D5F5F]">
                <Mail size={22} />
              </div>
              <h2 className="mt-5 text-2xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
                Cek inbox kamu
              </h2>
              <p className="text-sm text-[#4A635D] mt-2 leading-relaxed">
                Kami sudah mengirim link verifikasi ke <strong className="text-[#1C302B]">{email}</strong>.
                Klik link di email untuk mengaktifkan akun kamu. Link berlaku 24 jam.
              </p>

              {(stateDevNote || devUrl) && (
                <div className="mt-4 rounded-2xl border border-dashed border-[#D8E6DD] bg-[#FBFDFB] p-4 text-xs text-[#4A635D]" data-testid="dev-mode-banner">
                  <div className="font-semibold text-[#2D5F5F] uppercase tracking-[0.18em] text-[10px] mb-1">Demo / Testing Mode</div>
                  {stateDevNote && <p className="leading-relaxed">{stateDevNote}</p>}
                  {devUrl && (
                    <a
                      href={devUrl}
                      target="_self"
                      data-testid="dev-verification-link"
                      className="mt-2 inline-flex items-center gap-2 text-[#2D5F5F] font-medium hover:underline break-all"
                    >
                      <ExternalLink size={14} /> Klik untuk verifikasi langsung
                    </a>
                  )}
                </div>
              )}

              <div className="mt-5">
                <button
                  onClick={handleResend}
                  disabled={resending}
                  data-testid="resend-from-info-button"
                  className="w-full rounded-full border border-[#D8E6DD] py-3 text-sm font-medium text-[#1C302B] hover:bg-[#F4F7F4] transition disabled:opacity-60"
                >
                  {resending ? "Mengirim ulang…" : "Kirim ulang link verifikasi"}
                </button>
              </div>

              <p className="text-center text-sm text-[#4A635D] mt-6">
                Sudah verifikasi?{" "}
                <Link to="/login" className="text-[#2D5F5F] font-semibold hover:underline" data-testid="info-goto-login">
                  Masuk di sini
                </Link>
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
