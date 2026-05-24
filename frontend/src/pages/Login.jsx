import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { formatApiErrorDetail } from "@/lib/api";
import { Mail, Lock, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
      toast.success("Selamat datang kembali di Sanctuary");
      navigate("/");
    } catch (err) {
      const detail = err.response?.data?.detail;
      // Email not verified handling
      if (detail && typeof detail === "object" && detail.code === "email_not_verified") {
        toast.error("Email belum diverifikasi. Mengirim ulang link…");
        navigate("/verify-email", { state: { email: detail.email, needsResend: true } });
        return;
      }
      const msg = formatApiErrorDetail(detail) || err.message;
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  return (
    <div className="min-h-screen botanical-bg grid place-items-center px-4 py-10">
      <div className="relative z-10 w-full max-w-md fade-up" data-testid="login-card">
        <div className="bg-white/95 backdrop-blur-xl rounded-[2rem] shadow-[0_24px_60px_rgba(28,48,43,0.18)] p-8 sm:p-10">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-2xl bg-[#2D5F5F] grid place-items-center text-white">
              <span className="font-semibold text-lg">E</span>
            </div>
            <div>
              <div className="font-semibold text-lg text-[#1C302B]">EchoAid</div>
              <div className="text-[11px] uppercase tracking-[0.22em] text-[#7A9690]">Sanctuary</div>
            </div>
          </div>

          <h1 className="text-3xl sm:text-4xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
            Welcome Back
          </h1>
          <p className="text-sm text-[#7A9690] mt-2">Sign in to your sanctuary</p>

          <form onSubmit={submit} className="mt-7 space-y-4">
            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Email</label>
              <div className="mt-1.5 flex items-center gap-3 px-4 py-3 rounded-xl bg-[#F4F7F4] focus-within:ring-2 ring-[#E8F0EA] border border-transparent focus-within:border-[#2D5F5F] transition">
                <Mail size={16} className="text-[#7A9690]" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="nama@email.com"
                  className="flex-1 bg-transparent outline-none text-sm text-[#1C302B] placeholder:text-[#A7BCB6]"
                  data-testid="login-email-input"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between">
                <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Password</label>
                <button type="button" className="text-xs text-[#2D5F5F] hover:underline" data-testid="forgot-password-btn">
                  Lupa password?
                </button>
              </div>
              <div className="mt-1.5 flex items-center gap-3 px-4 py-3 rounded-xl bg-[#F4F7F4] focus-within:ring-2 ring-[#E8F0EA] border border-transparent focus-within:border-[#2D5F5F] transition">
                <Lock size={16} className="text-[#7A9690]" />
                <input
                  type={show ? "text" : "password"}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="flex-1 bg-transparent outline-none text-sm text-[#1C302B] placeholder:text-[#A7BCB6]"
                  data-testid="login-password-input"
                />
                <button
                  type="button"
                  onClick={() => setShow((s) => !s)}
                  className="text-[#7A9690] hover:text-[#2D5F5F]"
                  aria-label="Toggle password"
                  data-testid="toggle-password-visibility"
                >
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="text-sm text-[#C06C5B] bg-[#FCEFEB] px-4 py-2 rounded-xl" data-testid="login-error">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              data-testid="login-submit-button"
              className="w-full mt-2 rounded-full bg-[#2D5F5F] text-white py-3.5 font-medium hover:bg-[#244C4C] active:translate-y-0 hover:-translate-y-0.5 transition disabled:opacity-60"
            >
              {loading ? "Memasuki Sanctuary…" : "Masuk ke Sanctuary"}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-[#7A9690]">
            <div className="flex-1 h-px bg-[#D8E6DD]" />
            atau masuk dengan
            <div className="flex-1 h-px bg-[#D8E6DD]" />
          </div>

          <button
            onClick={onGoogle}
            data-testid="google-signin-button"
            className="w-full rounded-full border border-[#D8E6DD] bg-white py-3 flex items-center justify-center gap-3 hover:bg-[#F4F7F4] transition text-sm font-medium text-[#1C302B]"
          >
            <img alt="Google" src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" className="w-4 h-4" />
            Lanjutkan dengan Google
          </button>

          <p className="text-center text-sm text-[#4A635D] mt-6">
            Belum punya akun?{" "}
            <Link to="/register" className="text-[#2D5F5F] font-semibold hover:underline" data-testid="link-to-register">
              Daftar di sini
            </Link>
          </p>
          <p className="text-center text-xs text-[#7A9690] mt-3">
            Dengan masuk kamu menyetujui Syarat Pengguna & Kebijakan Privasi EchoAid.
          </p>
        </div>
      </div>
    </div>
  );
}
