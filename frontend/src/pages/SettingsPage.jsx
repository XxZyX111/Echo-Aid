import React from "react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import { Switch } from "@/components/ui/switch";
import { Bell, FileText, CalendarCheck, Users, AlarmClock, Sparkles, Type, Download, Trash2, KeyRound } from "lucide-react";
import { toast } from "sonner";

function Row({ icon: Icon, title, desc, value, onChange, testid }) {
  return (
    <div className="flex items-start justify-between gap-4 py-4 border-b border-[#E8F0EA] last:border-0">
      <div className="flex items-start gap-3">
        <div className="mt-0.5 text-[#4A635D]"><Icon size={16} /></div>
        <div>
          <div className="text-sm font-medium text-[#1C302B]">{title}</div>
          <div className="text-xs text-[#7A9690] mt-0.5 max-w-md">{desc}</div>
        </div>
      </div>
      <Switch checked={!!value} onCheckedChange={onChange} data-testid={testid} />
    </div>
  );
}

export default function SettingsPage() {
  const { user, setUser } = useAuth();
  if (!user) return null;
  const s = user.settings || {};

  const set = async (key, val) => {
    const { data } = await api.patch("/settings", { [key]: val });
    setUser(data.user);
  };

  return (
    <div className="max-w-3xl mx-auto" data-testid="settings-page">
      <h1 className="text-2xl sm:text-3xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>Settings</h1>
      <p className="text-[#7A9690] text-sm mt-1">Manage your EchoAid sanctuary for you.</p>

      <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] mt-6">
        <Row icon={Bell} title="Notifications" desc="Choose when EchoAid reaches out to you." value={s.notifications} onChange={(v) => set("notifications", v)} testid="set-notifications" />
        <Row icon={FileText} title="Weekly Wellness Report" desc="A summary of your mood trends and activity each Sunday." value={s.weekly_wellness_report} onChange={(v) => set("weekly_wellness_report", v)} testid="set-weekly-report" />
        <Row icon={CalendarCheck} title="Consultation Reminders" desc="Alerts before your scheduled counsellor sessions." value={s.consultation_reminders} onChange={(v) => set("consultation_reminders", v)} testid="set-consultation-reminders" />
        <Row icon={Users} title="Community Updates" desc="News from peer support groups and campus wellness events." value={s.community_updates} onChange={(v) => set("community_updates", v)} testid="set-community-updates" />
        <Row icon={AlarmClock} title="Mood Check-in Alert" desc="Evening reminder to log how you're feeling." value={s.mood_check_in_alert} onChange={(v) => set("mood_check_in_alert", v)} testid="set-mood-alert" />
      </div>

      <div className="mt-5 bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
        <div className="font-medium text-[#1C302B]">Appearance & Accessibility</div>
        <div className="text-xs text-[#7A9690] mb-2">Adjust the app to suit your needs.</div>
        <Row icon={Sparkles} title="Reduce Motion" desc="Minimise animations for a calmer experience." value={s.reduce_motion} onChange={(v) => set("reduce_motion", v)} testid="set-reduce-motion" />
        <Row icon={Type} title="Larger Text" desc="Increase the base font size across the app." value={s.larger_text} onChange={(v) => set("larger_text", v)} testid="set-larger-text" />
      </div>

      <div className="mt-5 bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
        <div className="font-medium text-[#1C302B]">Account</div>
        <div className="text-xs text-[#7A9690] mb-4">Manage your account and data.</div>
        <div className="flex flex-wrap gap-3">
          <button onClick={() => toast.info("Fitur ubah password segera hadir")} className="rounded-full border border-[#D8E6DD] px-5 py-2.5 text-sm text-[#1C302B] hover:bg-[#F4F7F4] flex items-center gap-2" data-testid="change-password-btn">
            <KeyRound size={14} /> Change Password
          </button>
          <button onClick={() => toast.success("Permintaan unduh data terkirim ke email kamu")} className="rounded-full border border-[#D8E6DD] px-5 py-2.5 text-sm text-[#1C302B] hover:bg-[#F4F7F4] flex items-center gap-2" data-testid="download-data-btn">
            <Download size={14} /> Download My Data
          </button>
          <button onClick={() => toast.error("Hubungi support@echoaid.com untuk menghapus akun")} className="rounded-full bg-[#FCEFEB] text-[#C06C5B] px-5 py-2.5 text-sm font-medium hover:bg-[#F6DAD2] flex items-center gap-2" data-testid="delete-account-btn">
            <Trash2 size={14} /> Delete Account
          </button>
        </div>
      </div>
    </div>
  );
}
