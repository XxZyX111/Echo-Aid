import React, { useState } from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Switch } from "@/components/ui/switch";
import { Sun, Moon, Bell, ShieldCheck, Lock, Download, Heart, UserPlus, LogOut, PlusCircle, Pencil, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { useNavigate } from "react-router-dom";

export default function ProfilePage() {
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const [adding, setAdding] = useState(false);
  const [newG, setNewG] = useState({ name: "", relation: "", phone: "" });

  if (!user) return null;

  const togglePref = async (key, val) => {
    const prefs = { ...(user.sanctuary_preferences || {}), [key]: val };
    const { data } = await api.patch("/profile", { sanctuary_preferences: prefs });
    setUser(data.user);
  };

  const togglePrivacy = async (key, val) => {
    const privacy = { ...(user.privacy || {}), [key]: val };
    const { data } = await api.patch("/profile", { privacy });
    setUser(data.user);
  };

  const addGuardian = async () => {
    if (!newG.name) return toast.info("Nama guardian wajib diisi");
    const { data } = await api.post("/profile/guardian", newG);
    setUser(data.user);
    setNewG({ name: "", relation: "", phone: "" });
    setAdding(false);
    toast.success("Guardian ditambahkan ke Sanctuary kamu");
  };

  const removeGuardian = async (id) => {
    const { data } = await api.delete(`/profile/guardian/${id}`);
    setUser(data.user);
  };

  const handleSignOut = async () => {
    await logout();
    navigate("/login");
  };

  const prefs = user.sanctuary_preferences || {};
  const privacy = user.privacy || {};
  const routine = user.daily_support_routine || [];
  const guardians = user.guardian_circle || [];

  return (
    <div className="max-w-4xl mx-auto" data-testid="profile-page">
      <div className="bg-white rounded-3xl p-6 sm:p-8 shadow-[0_8px_32px_rgba(45,95,95,0.06)] flex flex-col sm:flex-row items-center gap-6">
        <img src={user.avatar_url} alt="avatar" className="w-24 h-24 rounded-3xl object-cover ring-4 ring-[#E8F0EA]" />
        <div className="text-center sm:text-left">
          <h1 className="text-2xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>{user.name}</h1>
          <div className="text-sm text-[#7A9690]">{user.university || "EchoAid Member"}</div>
          <span className="inline-block mt-2 text-[11px] uppercase tracking-[0.18em] bg-[#E6F4EA] text-[#2D5F5F] px-3 py-1 rounded-full">
            {user.role === "admin" ? "Admin" : "Sanctuary Member"}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 mt-5">
        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]" data-testid="sanctuary-prefs-card">
          <div className="flex items-center gap-2 mb-4 text-[#1C302B] font-medium">
            <Heart size={16} className="text-[#2D5F5F]" /> Sanctuary Preferences
          </div>
          <div className="flex items-center justify-between p-4 rounded-2xl bg-[#F4F7F4]">
            <div className="flex items-center gap-3">
              <Moon size={16} className="text-[#4A635D]" />
              <div>
                <div className="text-sm font-medium text-[#1C302B]">Dark Mode</div>
                <div className="text-xs text-[#7A9690]">Soft theme for healing eyes</div>
              </div>
            </div>
            <Switch checked={!!prefs.dark_mode} onCheckedChange={(v) => togglePref("dark_mode", v)} data-testid="toggle-dark-mode" />
          </div>
          <div className="flex items-center justify-between p-4 rounded-2xl bg-[#F4F7F4] mt-3">
            <div className="flex items-center gap-3">
              <Bell size={16} className="text-[#4A635D]" />
              <div>
                <div className="text-sm font-medium text-[#1C302B]">Daily Reminders</div>
                <div className="text-xs text-[#7A9690]">Subtle nudges for wellness check-ins</div>
              </div>
            </div>
            <Switch checked={!!prefs.daily_reminders} onCheckedChange={(v) => togglePref("daily_reminders", v)} data-testid="toggle-daily-reminders" />
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]" data-testid="daily-routine-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-[#1C302B] font-medium"><Sun size={16} className="text-[#2D5F5F]" /> Daily Support Routine</div>
            <button className="text-xs text-[#2D5F5F] flex items-center gap-1" data-testid="add-routine"><PlusCircle size={14} /> Add New</button>
          </div>
          <div className="space-y-3">
            {routine.map((r) => (
              <div key={r.id} className="flex items-center justify-between p-3 rounded-2xl bg-[#F4F7F4]">
                <div>
                  <div className="text-sm font-medium text-[#1C302B]">{r.title}</div>
                  <div className="text-xs text-[#7A9690]">Scheduled · {r.schedule}</div>
                </div>
                <span className={`text-[11px] uppercase tracking-[0.18em] px-2.5 py-1 rounded-full ${r.status === "active" ? "bg-[#E6F4EA] text-[#2D5F5F]" : "bg-white border border-[#D8E6DD] text-[#4A635D]"}`}>
                  {r.status === "active" ? "Active" : "Upcoming"}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] md:col-span-2" data-testid="privacy-card">
          <div className="flex items-center gap-2 mb-3 text-[#1C302B] font-medium"><ShieldCheck size={16} className="text-[#2D5F5F]" /> Privacy & Security</div>
          <div className="bg-[#E8F0EA] rounded-2xl p-4 text-sm text-[#1C302B] mb-4">
            <div className="font-medium">100% Confidential Environment</div>
            <div className="text-[#4A635D] text-xs mt-1">Your data is encrypted and never shared with universities or third parties. EchoAid prioritizes your mental well-being and privacy.</div>
          </div>
          <div className="space-y-3">
            <div className="flex items-center justify-between p-4 rounded-2xl bg-[#F4F7F4]">
              <div className="flex items-center gap-3">
                <Lock size={16} className="text-[#4A635D]" />
                <div>
                  <div className="text-sm font-medium text-[#1C302B]">Biometric App Lock</div>
                </div>
              </div>
              <Switch checked={!!privacy.biometric_lock} onCheckedChange={(v) => togglePrivacy("biometric_lock", v)} data-testid="toggle-biometric" />
            </div>
            <div className="flex items-center justify-between p-4 rounded-2xl bg-[#F4F7F4]">
              <div className="flex items-center gap-3">
                <ShieldCheck size={16} className="text-[#4A635D]" />
                <div>
                  <div className="text-sm font-medium text-[#1C302B]">Journal Auto-Encryption</div>
                </div>
              </div>
              <Switch checked={!!privacy.journal_encryption} onCheckedChange={(v) => togglePrivacy("journal_encryption", v)} data-testid="toggle-journal-encryption" />
            </div>
            <button className="w-full flex items-center justify-between p-4 rounded-2xl bg-[#F4F7F4] hover:bg-[#E8F0EA] transition text-sm text-[#C06C5B] font-medium" data-testid="download-my-data">
              <span className="flex items-center gap-3"><Download size={16} /> Download My Data</span>
            </button>
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] md:col-span-2" data-testid="guardian-card">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2 text-[#1C302B] font-medium"><Heart size={16} className="text-[#C06C5B]" /> Guardian Circle</div>
            <button onClick={() => setAdding(true)} className="text-xs text-[#2D5F5F] flex items-center gap-1" data-testid="open-add-guardian"><UserPlus size={14} /> Add Emergency Contact</button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {guardians.map((g) => (
              <div key={g.guardian_id} className="flex items-center gap-3 p-3 rounded-2xl bg-[#F4F7F4]">
                <div className="w-10 h-10 rounded-full bg-[#E8F0EA] grid place-items-center text-[#2D5F5F] font-semibold">{g.name?.[0] || "G"}</div>
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium text-[#1C302B] truncate">{g.name}</div>
                  <div className="text-xs text-[#7A9690] truncate">{g.relation} · {g.phone}</div>
                </div>
                <button onClick={() => removeGuardian(g.guardian_id)} className="text-[#C06C5B]" data-testid={`remove-guardian-${g.guardian_id}`}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
            {guardians.length === 0 && <div className="text-sm text-[#7A9690] col-span-full">Belum ada guardian. Tambah orang yang kamu percaya untuk dihubungi saat kondisi darurat.</div>}
          </div>
          {adding && (
            <div className="mt-4 p-4 rounded-2xl border border-dashed border-[#D8E6DD]">
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                <input value={newG.name} onChange={(e) => setNewG((g) => ({ ...g, name: e.target.value }))} placeholder="Nama" className="px-3 py-2 rounded-xl bg-[#F4F7F4] outline-none text-sm" data-testid="guardian-name" />
                <input value={newG.relation} onChange={(e) => setNewG((g) => ({ ...g, relation: e.target.value }))} placeholder="Hubungan" className="px-3 py-2 rounded-xl bg-[#F4F7F4] outline-none text-sm" data-testid="guardian-relation" />
                <input value={newG.phone} onChange={(e) => setNewG((g) => ({ ...g, phone: e.target.value }))} placeholder="No. HP" className="px-3 py-2 rounded-xl bg-[#F4F7F4] outline-none text-sm" data-testid="guardian-phone" />
              </div>
              <div className="flex gap-2 mt-3 justify-end">
                <button onClick={() => setAdding(false)} className="text-xs text-[#4A635D] px-3 py-2" data-testid="cancel-guardian">Batal</button>
                <button onClick={addGuardian} className="rounded-full bg-[#2D5F5F] text-white px-5 py-2 text-xs font-medium" data-testid="save-guardian">Simpan</button>
              </div>
            </div>
          )}
        </div>
      </div>

      <button
        onClick={handleSignOut}
        data-testid="signout-button"
        className="mt-6 w-full rounded-full border-2 border-[#C06C5B] text-[#C06C5B] py-3 font-medium hover:bg-[#FCEFEB] transition flex items-center justify-center gap-2"
      >
        <LogOut size={16} /> Sign Out
      </button>
    </div>
  );
}
