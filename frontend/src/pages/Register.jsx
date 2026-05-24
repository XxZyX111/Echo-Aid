import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { api, formatApiErrorDetail } from "@/lib/api";
import { Mail, Lock, User, GraduationCap, Eye, EyeOff } from "lucide-react";
import { toast } from "sonner";

export default function Register() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState({
    name: "",
    nickname: "",
    email: "",
    university: "",
    password: "",
    confirm: "",
    agree: false,
  });
  const [show, setShow] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const onChange = (k) => (e) =>
    setForm((f) => ({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value }));

  const submit = async (e) => {
    e.preventDefault();
    setError("");
    if (form.password.length < 6) return setError("Password minimal 6 karakter");
    if (form.password !== form.confirm) return setError("Konfirmasi password tidak cocok");
    if (!form.agree) return setError("Mohon setujui Syarat Pengguna & Kebijakan Privasi");
    setLoading(true);
    try {
      const { data } = await api.post("/auth/register", {
        name: form.name,
        nickname: form.nickname,
        email: form.email,
        password: form.password,
        university: form.university,
      });
      toast.success("Sanctuary kamu sudah siap. Cek email untuk verifikasi.");
      // Pass dev link if testing mode
      navigate("/verify-email", { state: { email: data.email, devUrl: data.dev_verification_url, devNote: data.dev_mode_note } });
    } catch (err) {
      setError(formatApiErrorDetail(err.response?.data?.detail) || err.message);
    } finally {
      setLoading(false);
    }
  };

  const onGoogle = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + "/";
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  const FieldIcon = ({ Icon, children }) => (
    <div className="mt-1.5 flex items-center gap-3 px-4 py-3 rounded-xl bg-[#F4F7F4] focus-within:ring-2 ring-[#E8F0EA] border border-transparent focus-within:border-[#2D5F5F] transition">
      <Icon size={16} className="text-[#7A9690]" />
      {children}
    </div>
  );

  return (
    <div className="min-h-screen botanical-bg grid place-items-center px-4 py-10">
      <div className="relative z-10 w-full max-w-lg fade-up" data-testid="register-card">
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

          <h1 className="text-3xl sm:text-4xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
            Buat akun sanctuary
          </h1>
          <p className="text-sm text-[#7A9690] mt-2">Mulai perjalanan kesehatan mental kamu bersama kami</p>

          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Nama Depan</label>
                <FieldIcon Icon={User}>
                  <input
                    required
                    value={form.name}
                    onChange={onChange("name")}
                    placeholder="Nama Depan"
                    className="flex-1 bg-transparent outline-none text-sm placeholder:text-[#A7BCB6]"
                    data-testid="register-name-input"
                  />
                </FieldIcon>
              </div>
              <div>
                <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Nama Belakang / Panggilan</label>
                <FieldIcon Icon={User}>
                  <input
                    value={form.nickname}
                    onChange={onChange("nickname")}
                    placeholder="Nama Belakang"
                    className="flex-1 bg-transparent outline-none text-sm placeholder:text-[#A7BCB6]"
                    data-testid="register-nickname-input"
                  />
                </FieldIcon>
              </div>
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Email</label>
              <FieldIcon Icon={Mail}>
                <input
                  type="email"
                  required
                  value={form.email}
                  onChange={onChange("email")}
                  placeholder="nama@email.com"
                  className="flex-1 bg-transparent outline-none text-sm placeholder:text-[#A7BCB6]"
                  data-testid="register-email-input"
                />
              </FieldIcon>
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Universitas / Pekerjaan</label>
              <FieldIcon Icon={GraduationCap}>
                <input
                  value={form.university}
                  onChange={onChange("university")}
                  placeholder="Universitas / Profesi"
                  className="flex-1 bg-transparent outline-none text-sm placeholder:text-[#A7BCB6]"
                  data-testid="register-university-input"
                />
              </FieldIcon>
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Password</label>
              <FieldIcon Icon={Lock}>
                <input
                  type={show ? "text" : "password"}
                  required
                  value={form.password}
                  onChange={onChange("password")}
                  placeholder="Min. 6 karakter"
                  className="flex-1 bg-transparent outline-none text-sm placeholder:text-[#A7BCB6]"
                  data-testid="register-password-input"
                />
                <button type="button" onClick={() => setShow((s) => !s)} className="text-[#7A9690]" data-testid="toggle-register-password">
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </FieldIcon>
            </div>

            <div>
              <label className="text-xs uppercase tracking-[0.18em] text-[#4A635D]">Konfirmasi Password</label>
              <FieldIcon Icon={Lock}>
                <input
                  type={show ? "text" : "password"}
                  required
                  value={form.confirm}
                  onChange={onChange("confirm")}
                  placeholder="Ulangi password"
                  className="flex-1 bg-transparent outline-none text-sm placeholder:text-[#A7BCB6]"
                  data-testid="register-confirm-input"
                />
              </FieldIcon>
            </div>

            <label className="flex items-start gap-3 text-xs text-[#4A635D] cursor-pointer">
              <input
                type="checkbox"
                checked={form.agree}
                onChange={onChange("agree")}
                className="mt-0.5 accent-[#2D5F5F]"
                data-testid="register-agree-checkbox"
              />
              Saya setuju dengan Syarat Pengguna dan Kebijakan Privasi EchoAid.
            </label>

            {error && (
              <div className="text-sm text-[#C06C5B] bg-[#FCEFEB] px-4 py-2 rounded-xl" data-testid="register-error">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              data-testid="register-submit-button"
              className="w-full mt-2 rounded-full bg-[#2D5F5F] text-white py-3.5 font-medium hover:bg-[#244C4C] hover:-translate-y-0.5 transition disabled:opacity-60"
            >
              {loading ? "Menyiapkan sanctuary…" : "Buat Sanctuary Saya"}
            </button>
          </form>

          <div className="my-6 flex items-center gap-3 text-xs text-[#7A9690]">
            <div className="flex-1 h-px bg-[#D8E6DD]" />
            atau daftar dengan
            <div className="flex-1 h-px bg-[#D8E6DD]" />
          </div>

          <button
            onClick={onGoogle}
            data-testid="google-signup-button"
            className="w-full rounded-full border border-[#D8E6DD] bg-white py-3 flex items-center justify-center gap-3 hover:bg-[#F4F7F4] transition text-sm font-medium text-[#1C302B]"
          >
            <img alt="Google" src="https://www.gstatic.com/firebasejs/ui/2.0.0/images/auth/google.svg" className="w-4 h-4" />
            Daftar dengan Google
          </button>

          <p className="text-center text-sm text-[#4A635D] mt-6">
            Sudah punya akun?{" "}
            <Link to="/login" className="text-[#2D5F5F] font-semibold hover:underline" data-testid="link-to-login">
              Masuk di sini
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
