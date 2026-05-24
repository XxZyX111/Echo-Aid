import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { ArrowRight, Sparkles, MapPin, Stethoscope, RefreshCw, Lightbulb } from "lucide-react";
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { toast } from "sonner";

const MOODS = [
  { id: "grateful", label: "Grateful", emoji: "😊", bg: "bg-[#E6F4EA]" },
  { id: "calm", label: "Calm", emoji: "😌", bg: "bg-[#E8F0F7]" },
  { id: "neutral", label: "Neutral", emoji: "😐", bg: "bg-[#FBEFD8]" },
  { id: "low", label: "Low", emoji: "😔", bg: "bg-[#F4DDE4]" },
  { id: "anxious", label: "Anxious", emoji: "😟", bg: "bg-[#E6E0F2]" },
];

const QUOTES = [
  "Tidak apa-apa merasa lelah hari ini. Kamu tidak sendirian, ingatlah bahwa setiap langkah kecil adalah kemajuan.",
  "Healing is not linear. Bernapaslah, kamu sudah jauh dari tempat kamu mulai.",
  "Beristirahat juga produktif. Take a moment for yourself.",
  "Your feelings are valid. Beri ruang untuk merasakan tanpa menghakimi.",
];

export default function Home() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [moods, setMoods] = useState([]);
  const [note, setNote] = useState("");
  const [selectedMood, setSelectedMood] = useState(null);
  const [saving, setSaving] = useState(false);

  // Weekly Insight
  const [insight, setInsight] = useState(null);
  const [insightStats, setInsightStats] = useState(null);
  const [insightStale, setInsightStale] = useState(true);
  const [insightLoading, setInsightLoading] = useState(false);

  const quote = useMemo(() => QUOTES[new Date().getDate() % QUOTES.length], []);

  useEffect(() => {
    api.get("/mood").then((r) => setMoods(r.data.items || [])).catch(() => {});
    api.get("/insights/weekly").then((r) => {
      setInsight(r.data.insight);
      setInsightStats(r.data.stats);
      setInsightStale(r.data.is_stale);
    }).catch(() => {});
  }, []);

  const generateInsight = async () => {
    setInsightLoading(true);
    try {
      const { data } = await api.post("/insights/weekly");
      setInsight(data.insight);
      setInsightStats(data.stats);
      setInsightStale(false);
      if (data.throttled) {
        toast.info("Insight sudah dibuat dalam 1 jam terakhir. Tampilkan yang ada.");
      } else {
        toast.success("Weekly insight baru sudah siap 🌿");
      }
    } catch (err) {
      const msg = err.response?.data?.detail || "Gagal generate insight";
      toast.error(typeof msg === "string" ? msg : "Gagal generate insight");
    } finally {
      setInsightLoading(false);
    }
  };

  const submitMood = async () => {
    if (!selectedMood) {
      toast.info("Pilih mood kamu dulu");
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.post("/mood", { mood: selectedMood, note });
      const moodEntry = data.entry || data;
      setMoods((m) => [moodEntry, ...m]);
      setSelectedMood(null);
      setNote("");
      if (data.journal_entry) {
        if (data.journal_entry.ai_response_status === "pending") {
          toast.success("Mood + curhatan tersimpan. Echo Companion sedang menulis respons…");
        } else {
          toast.success("Mood + curhatan tersimpan ke Journal 🌿");
        }
      } else {
        toast.success("Mood tersimpan di sanctuary 🌿");
      }
    } catch (e) {
      toast.error("Gagal menyimpan mood");
    } finally {
      setSaving(false);
    }
  };

  // Build chart data: last 7 days mood, stress (inverse), cortisol (simulated body indicator)
  // All on a 1-5 wellness scale.
  const chartData = useMemo(() => {
    const moodScore = { grateful: 5, calm: 4, neutral: 3, low: 2, anxious: 1 };
    const stressScore = { grateful: 1, calm: 2, neutral: 3, low: 4, anxious: 5 };
    // Cortisol is a simulated body indicator (lower = calmer body)
    const cortisolScore = { grateful: 1.5, calm: 2, neutral: 2.8, low: 4, anxious: 4.5 };
    const days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
    const today = new Date();
    return days.map((d, i) => {
      const day = new Date(today);
      day.setDate(today.getDate() - (6 - i));
      const dayStr = day.toISOString().slice(0, 10);
      const m = moods.find((x) => (x.created_at || "").slice(0, 10) === dayStr);
      return {
        day: d,
        mood: m ? moodScore[m.mood] : 3 + ((i * 7) % 3) - 1,
        stress: m ? stressScore[m.mood] : 2 + ((i * 5) % 3),
        cortisol: m ? cortisolScore[m.mood] : 2.5 + ((i * 3) % 3) * 0.5,
      };
    });
  }, [moods]);

  return (
    <div className="max-w-6xl mx-auto" data-testid="home-dashboard">
      <div className="mb-6">
        <h1 className="text-3xl sm:text-4xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
          Welcome back, {user?.nickname || user?.name?.split(" ")[0] || "friend"}.
        </h1>
        <p className="text-[#4A635D] mt-1">How are you feeling today?</p>
      </div>

      <div className="bg-[#E8F0EA] text-[#1C302B] rounded-2xl px-5 py-4 text-sm italic mb-6 fade-up" data-testid="daily-quote">
        “{quote}”
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] fade-up" data-testid="mood-checkin-card">
          <div className="flex items-center justify-between mb-5">
            <div>
              <h3 className="text-lg font-semibold text-[#1C302B]">Quick Mood Check-in</h3>
              <p className="text-xs text-[#7A9690] mt-0.5">Daily entry · {new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</p>
            </div>
          </div>
          <div className="grid grid-cols-5 gap-2 sm:gap-3">
            {MOODS.map((m) => (
              <button
                key={m.id}
                onClick={() => setSelectedMood(m.id)}
                data-testid={`mood-button-${m.id}`}
                className={`group flex flex-col items-center gap-1 sm:gap-2 py-2 sm:py-3 rounded-2xl border transition-all ${
                  selectedMood === m.id ? "border-[#2D5F5F] bg-[#E8F0EA] -translate-y-0.5" : "border-transparent hover:bg-[#F4F7F4]"
                }`}
              >
                <div className={`w-10 h-10 sm:w-12 sm:h-12 rounded-2xl grid place-items-center text-xl sm:text-2xl ${m.bg}`}>{m.emoji}</div>
                <div className="text-[10px] sm:text-xs text-[#4A635D]">{m.label}</div>
              </button>
            ))}
          </div>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Want to add more context? (Optional)"
            className="mt-5 w-full rounded-xl bg-[#F4F7F4] focus:bg-white focus:ring-2 ring-[#E8F0EA] outline-none border border-transparent focus:border-[#2D5F5F] px-4 py-3 text-sm resize-none"
            rows={3}
            data-testid="mood-note-input"
          />
          <div className="mt-4 flex justify-end">
            <button
              onClick={submitMood}
              disabled={saving}
              data-testid="mood-submit-button"
              className="rounded-full bg-[#2D5F5F] text-white px-6 py-2.5 text-sm font-medium hover:bg-[#244C4C] hover:-translate-y-0.5 transition disabled:opacity-60"
            >
              {saving ? "Menyimpan…" : "Simpan Mood"}
            </button>
          </div>
        </div>

        <div className="bg-[#2D5F5F] text-white rounded-3xl p-6 shadow-[0_16px_48px_rgba(45,95,95,0.20)] flex flex-col fade-up" data-testid="consultation-cta">
          <div className="flex items-center gap-2 text-[#B8DDD4] text-[11px] uppercase tracking-[0.18em]">
            <Stethoscope size={14} strokeWidth={1.6} /> Consultation
          </div>
          <h3 className="text-2xl font-medium mt-3" style={{ fontFamily: "Outfit, sans-serif" }}>
            Saatnya untuk konsultasi
          </h3>
          <p className="text-sm text-[#C5DBD6] mt-2 flex-1">
            Mari ngobrol dan konsultasi bersama para psikolog tersertifikasi kami.
          </p>
          <button
            onClick={() => navigate("/consultation")}
            data-testid="goto-consultation-button"
            className="mt-5 rounded-full bg-[#E8F0EA] text-[#1C302B] px-5 py-2.5 text-sm font-medium flex items-center justify-center gap-2 hover:bg-white transition"
          >
            Konsultasi <ArrowRight size={16} />
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 mt-5">
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] fade-up" data-testid="health-correlation-card">
          <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
            <div>
              <h3 className="text-lg font-semibold text-[#1C302B]">Health Correlation</h3>
              <p className="text-xs text-[#7A9690] mt-0.5">7-day wellness biomarker trend (scale 1–5)</p>
            </div>
            <div className="flex items-center gap-3 text-xs text-[#4A635D] flex-wrap">
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#2D5F5F]" /> Mood</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#C06C5B]" /> Stress</span>
              <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[#B98A3D]" /> Cortisol</span>
            </div>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData} margin={{ top: 10, right: 12, left: 4, bottom: 4 }}>
                <CartesianGrid strokeDasharray="3 6" stroke="#E8F0EA" />
                <XAxis dataKey="day" stroke="#7A9690" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis
                  stroke="#7A9690"
                  tickLine={false}
                  axisLine={false}
                  fontSize={11}
                  domain={[0, 5]}
                  ticks={[1, 2, 3, 4, 5]}
                  width={28}
                  label={{
                    value: "Level",
                    angle: -90,
                    position: "insideLeft",
                    style: { fill: "#7A9690", fontSize: 11, textAnchor: "middle" },
                  }}
                />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: "1px solid #D8E6DD", fontSize: 12 }}
                  formatter={(value, name) => [Number(value).toFixed(1), name.charAt(0).toUpperCase() + name.slice(1)]}
                />
                <Line type="monotone" dataKey="mood" name="mood" stroke="#2D5F5F" strokeWidth={2.4} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="stress" name="stress" stroke="#C06C5B" strokeWidth={2.4} dot={{ r: 3 }} />
                <Line type="monotone" dataKey="cortisol" name="cortisol" stroke="#B98A3D" strokeWidth={2.2} strokeDasharray="6 4" dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="mt-3 grid grid-cols-3 gap-2 text-[11px] text-[#7A9690]">
            <div className="bg-[#F4F7F4] rounded-xl p-2.5"><div className="text-[#2D5F5F] font-semibold">Mood</div>Subjective wellness 1-5</div>
            <div className="bg-[#F4F7F4] rounded-xl p-2.5"><div className="text-[#C06C5B] font-semibold">Stress</div>Inverse mood signal</div>
            <div className="bg-[#F4F7F4] rounded-xl p-2.5"><div className="text-[#B98A3D] font-semibold">Cortisol</div>Simulated body load</div>
          </div>
        </div>

        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] flex flex-col fade-up" data-testid="healing-map-preview-card">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-[#1C302B]">Healing Map</h3>
            <button onClick={() => navigate("/healing-map")} className="text-[#2D5F5F]" data-testid="goto-healing-map">
              <ArrowRight size={18} />
            </button>
          </div>
          <div className="mt-4 rounded-2xl overflow-hidden h-40 relative">
            <img alt="park" src="https://images.unsplash.com/photo-1613370625437-f2956da172ef?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjY2NjV8MHwxfHNlYXJjaHwyfHxwZWFjZWZ1bCUyMHVyYmFuJTIwcGFyayUyMG5hdHVyZXxlbnwwfHx8fDE3Nzk2MTc4NTV8MA&ixlib=rb-4.1.0&q=85" className="w-full h-full object-cover" />
            <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent grid place-items-center text-white text-sm font-medium">
              <MapPin size={28} strokeWidth={1.6} />
            </div>
          </div>
          <div className="flex items-center justify-between mt-3 text-xs text-[#4A635D]">
            <span><MapPin size={12} className="inline mr-1" /> 2 Rest spots nearby</span>
            <span className="text-[#7A9690]">Jakarta</span>
          </div>
          <button
            onClick={() => navigate("/meditation")}
            data-testid="goto-meditation-button"
            className="mt-4 rounded-full bg-[#E8F0EA] text-[#1C302B] py-2.5 text-sm font-medium flex items-center justify-center gap-2 hover:bg-[#D8E6DD] transition"
          >
            <Sparkles size={14} /> Try a 4-7-8 Breathing
          </button>
        </div>
      </div>

      {/* Weekly AI Insight */}
      <div className="mt-5 bg-gradient-to-br from-[#E8F0EA] to-[#F4F7F4] rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] fade-up" data-testid="weekly-insight-card">
        <div className="flex flex-wrap items-start justify-between gap-3 mb-4">
          <div className="flex items-start gap-3">
            <div className="w-11 h-11 rounded-2xl bg-[#2D5F5F] grid place-items-center text-white shrink-0">
              <Lightbulb size={20} strokeWidth={1.6} />
            </div>
            <div>
              <div className="text-[11px] uppercase tracking-[0.18em] text-[#4A635D]">Weekly Insight</div>
              <h3 className="text-xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
                Refleksi 7 hari terakhir
              </h3>
              {insightStats && (
                <div className="mt-1 text-xs text-[#7A9690] flex flex-wrap gap-x-3 gap-y-1" data-testid="insight-stats">
                  <span>{insightStats.mood_entries} mood entries</span>
                  <span>{insightStats.journal_entries} jurnal</span>
                  {insightStats.dominant_mood && (
                    <span>Dominan: <span className="text-[#2D5F5F] font-medium capitalize">{insightStats.dominant_mood}</span></span>
                  )}
                  {insightStats.avg_mood_score != null && (
                    <span>Avg score: {insightStats.avg_mood_score}/5</span>
                  )}
                </div>
              )}
            </div>
          </div>
          <button
            onClick={generateInsight}
            disabled={insightLoading}
            data-testid="generate-insight-button"
            className="rounded-full bg-[#2D5F5F] text-white px-5 py-2 text-sm font-medium hover:bg-[#244C4C] hover:-translate-y-0.5 transition disabled:opacity-60 flex items-center gap-2"
          >
            <RefreshCw size={14} className={insightLoading ? "animate-spin" : ""} />
            {insightLoading ? "Menganalisis…" : insight ? "Generate Ulang" : "Generate Insight"}
          </button>
        </div>

        {insight ? (
          <div className="bg-white rounded-2xl p-5 text-sm text-[#1C302B] leading-relaxed whitespace-pre-wrap" data-testid="insight-content">
            {insight.content}
            <div className="mt-3 pt-3 border-t border-[#E8F0EA] text-[11px] text-[#7A9690] flex items-center justify-between">
              <span>Diperbarui {new Date(insight.created_at).toLocaleString("en-GB", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })}</span>
              {insightStale && <span className="text-[#C06C5B] font-medium">Sudah lebih dari 24 jam — refresh untuk insight terbaru</span>}
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-2xl p-5 text-sm text-[#4A635D]" data-testid="insight-empty">
            Belum ada insight minggu ini. Klik <span className="font-medium text-[#1C302B]">Generate Insight</span> untuk refleksi mingguan dari AI berbasis pola mood & jurnal kamu. Powered by Claude Sonnet 4.5 + WHO LIVE LIFE framework.
          </div>
        )}
      </div>
    </div>
  );
}
