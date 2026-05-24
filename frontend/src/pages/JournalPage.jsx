import React, { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import { Mic, Square, Sparkles, HeartHandshake, Loader2 } from "lucide-react";
import { toast } from "sonner";

const MOOD_EMOJI = {
  grateful: "😊",
  calm: "😌",
  neutral: "😐",
  low: "😔",
  anxious: "😟",
};
const MOOD_LABEL_BG = {
  grateful: "bg-[#E6F4EA] text-[#2D5F5F]",
  calm: "bg-[#E8F0F7] text-[#2D5F5F]",
  neutral: "bg-[#FBEFD8] text-[#7A6020]",
  low: "bg-[#F4DDE4] text-[#9C3A53]",
  anxious: "bg-[#E6E0F2] text-[#5E4791]",
};

function EntryItem({ entry, onUpdate }) {
  const [generating, setGenerating] = useState(false);
  const isMood = entry.mode === "mood" || entry.source === "mood_checkin";
  const badge = isMood ? "Mood" : entry.mode === "voice" ? "Voice" : "Text";
  const moodEmoji = entry.mood ? MOOD_EMOJI[entry.mood] : null;
  const moodChipClass = entry.mood ? MOOD_LABEL_BG[entry.mood] || "" : "";
  const isPending = entry.ai_response_status === "pending" && !entry.ai_response;
  const isFailed = entry.ai_response_status === "failed" && !entry.ai_response;

  // Poll for AI response when pending
  useEffect(() => {
    if (!isPending) return;
    let cancelled = false;
    const poll = async () => {
      for (let i = 0; i < 12 && !cancelled; i++) {
        await new Promise((r) => setTimeout(r, 2000));
        if (cancelled) return;
        try {
          const r = await api.get("/journal");
          const fresh = (r.data.items || []).find((x) => x.entry_id === entry.entry_id);
          if (fresh && (fresh.ai_response || fresh.ai_response_status !== "pending")) {
            onUpdate?.(fresh);
            return;
          }
        } catch {}
      }
    };
    poll();
    return () => { cancelled = true; };
  }, [isPending, entry.entry_id]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleAi = async () => {
    setGenerating(true);
    try {
      const { data } = await api.post(`/journal/${entry.entry_id}/ai-response`);
      onUpdate?.(data);
      toast.success("Respons supportif sudah siap 🌿");
    } catch (e) {
      toast.error("Gagal generate respons");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-3 rounded-2xl hover:bg-[#F4F7F4] transition" data-testid={`entry-${entry.entry_id}`}>
      <div className="flex items-start gap-3">
        <div className="flex flex-col items-center gap-1.5">
          <div className={`text-[11px] uppercase tracking-[0.16em] px-2 py-1 rounded-full bg-[#E6F4EA] text-[#2D5F5F]`}>
            {badge}
          </div>
          {moodEmoji && (
            <div className={`text-base rounded-full w-8 h-8 grid place-items-center ${moodChipClass}`} title={entry.mood}>
              {moodEmoji}
            </div>
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-sm text-[#1C302B] whitespace-pre-wrap">{entry.content}</div>
          <div className="text-[11px] text-[#7A9690] mt-1">{new Date(entry.created_at).toLocaleString()}</div>
          {entry.ai_response ? (
            <div className="mt-3 bg-[#E8F0EA] border-l-4 border-[#2D5F5F] rounded-xl p-3 fade-up" data-testid={`ai-response-${entry.entry_id}`}>
              <div className="text-[10px] uppercase tracking-[0.18em] text-[#2D5F5F] font-semibold flex items-center gap-1.5">
                <HeartHandshake size={12} /> Echo Companion
              </div>
              <p className="text-sm text-[#1C302B] mt-1.5 leading-relaxed whitespace-pre-wrap">{entry.ai_response}</p>
            </div>
          ) : isPending ? (
            <div className="mt-3 bg-[#F4F7F4] border-l-4 border-[#7A9690] rounded-xl p-3 flex items-center gap-2 text-xs text-[#4A635D]" data-testid={`ai-pending-${entry.entry_id}`}>
              <Loader2 size={14} className="animate-spin text-[#2D5F5F]" />
              Echo Companion sedang menulis respons supportif…
            </div>
          ) : isFailed ? (
            <button
              onClick={handleAi}
              disabled={generating}
              data-testid={`ai-retry-${entry.entry_id}`}
              className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-[#C06C5B] hover:underline"
            >
              <HeartHandshake size={12} /> Gagal generate. Coba lagi.
            </button>
          ) : (
            (entry.content && entry.content.length > 12) && (
              <button
                onClick={handleAi}
                disabled={generating}
                data-testid={`ai-respond-btn-${entry.entry_id}`}
                className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-[#2D5F5F] hover:underline disabled:opacity-60"
              >
                {generating ? <Loader2 size={12} className="animate-spin" /> : <HeartHandshake size={12} />}
                {generating ? "Menulis respons…" : "Minta respons supportif AI"}
              </button>
            )
          )}
        </div>
      </div>
    </div>
  );
}

function Waveform({ active }) {
  return (
    <div className={`flex items-end justify-center h-20 ${active ? "" : "opacity-50"}`} data-testid="voice-waveform">
      {Array.from({ length: 11 }).map((_, i) => (
        <span key={i} className="waveform-bar" style={{ animationPlayState: active ? "running" : "paused", height: 14 }} />
      ))}
    </div>
  );
}

export default function JournalPage() {
  const [mode, setMode] = useState("voice");
  const [text, setText] = useState("");
  const [entries, setEntries] = useState([]);
  const [saving, setSaving] = useState(false);

  // Voice
  const [recording, setRecording] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);

  const load = async () => {
    try {
      const r = await api.get("/journal");
      setEntries(r.data.items || []);
    } catch {}
  };
  useEffect(() => { load(); }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "" });
      audioChunksRef.current = [];
      mr.ondataavailable = (e) => { if (e.data.size > 0) audioChunksRef.current.push(e.data); };
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        const blob = new Blob(audioChunksRef.current, { type: "audio/webm" });
        await transcribeAndSave(blob);
      };
      mr.start();
      mediaRecorderRef.current = mr;
      setRecording(true);
    } catch (e) {
      toast.error("Akses microphone ditolak. Cek izin browser kamu.");
    }
  };

  const stopRecording = () => {
    const mr = mediaRecorderRef.current;
    if (mr && mr.state !== "inactive") mr.stop();
    setRecording(false);
  };

  const transcribeAndSave = async (blob) => {
    setTranscribing(true);
    try {
      const fd = new FormData();
      fd.append("audio", blob, "voice.webm");
      const r = await api.post("/journal/transcribe", fd, { headers: { "Content-Type": "multipart/form-data" } });
      const transcribed = r.data?.text || "";
      if (!transcribed.trim()) {
        toast.error("Tidak ada suara terdeteksi. Coba lagi ya.");
        return;
      }
      const saveRes = await api.post("/journal", { mode: "voice", content: transcribed });
      setEntries((e) => [saveRes.data, ...e]);
      toast.success("Suara kamu tersimpan sebagai jurnal 🌿");
    } catch (e) {
      toast.error("Gagal mentranskrip suara.");
    } finally {
      setTranscribing(false);
    }
  };

  const saveText = async () => {
    if (!text.trim()) {
      toast.info("Tulis sesuatu dulu ya.");
      return;
    }
    setSaving(true);
    try {
      const { data } = await api.post("/journal", { mode: "text", content: text });
      setEntries((e) => [data, ...e]);
      setText("");
      toast.success("Jurnal tersimpan 🌿");
    } catch {
      toast.error("Gagal menyimpan jurnal.");
    } finally {
      setSaving(false);
    }
  };

  const days = ["M", "T", "W", "T", "F", "S", "S"];

  return (
    <div className="max-w-6xl mx-auto" data-testid="journal-page">
      <div className="flex items-center justify-between mb-5">
        <div>
          <h1 className="text-2xl sm:text-3xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>Journal Sanctuary</h1>
          <div className="text-[#7A9690] text-sm mt-1">{new Date().toLocaleDateString("en-GB", { weekday: "long", day: "numeric", month: "short" })}</div>
        </div>
        <span className="text-[11px] uppercase tracking-[0.18em] bg-[#E6F4EA] text-[#2D5F5F] px-3 py-1.5 rounded-full">Encrypted & Private</span>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2 bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] fade-up">
          <div className="flex items-center justify-between mb-4">
            <div className="text-sm text-[#4A635D] flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#2D5F5F]" /> {mode === "voice" ? "Voice Reflection" : "Text Reflection"}
            </div>
          </div>

          {mode === "voice" ? (
            <div className="grid place-items-center py-6">
              <Waveform active={recording || transcribing} />
              <button
                onClick={recording ? stopRecording : startRecording}
                disabled={transcribing}
                data-testid={recording ? "stop-recording-button" : "start-recording-button"}
                className={`mt-6 w-24 h-24 rounded-full grid place-items-center text-white transition-all shadow-[0_16px_40px_rgba(45,95,95,0.25)] ${
                  recording ? "bg-[#C06C5B] hover:bg-[#A65A4B]" : "bg-[#2D5F5F] hover:bg-[#244C4C]"
                }`}
              >
                {recording ? <Square size={28} /> : <Mic size={28} />}
              </button>
              <div className="mt-4 text-sm text-[#4A635D]">
                {transcribing ? "Mentranskrip suara kamu…" : recording ? "Berbicaralah, kami mendengar." : "Tap to start speaking your mind…"}
              </div>
              <button
                onClick={() => setMode("text")}
                data-testid="switch-to-text-button"
                className="mt-5 rounded-full border border-[#D8E6DD] px-5 py-2 text-sm text-[#1C302B] hover:bg-[#F4F7F4] transition"
              >
                Switch to Text
              </button>
            </div>
          ) : (
            <div>
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                placeholder="Want to add more context? (Optional)"
                rows={10}
                data-testid="journal-text-input"
                className="w-full bg-[#F4F7F4] rounded-2xl px-4 py-3 outline-none focus:bg-white focus:ring-2 ring-[#E8F0EA] border border-transparent focus:border-[#2D5F5F] text-sm resize-none"
              />
              <div className="mt-4 flex items-center justify-between">
                <button
                  onClick={() => setMode("voice")}
                  data-testid="switch-to-voice-button"
                  className="rounded-full border border-[#D8E6DD] px-5 py-2 text-sm text-[#1C302B] hover:bg-[#F4F7F4] transition"
                >
                  Switch to Voice
                </button>
                <button
                  onClick={saveText}
                  disabled={saving}
                  data-testid="save-text-journal-button"
                  className="rounded-full bg-[#2D5F5F] text-white px-6 py-2.5 text-sm font-medium hover:bg-[#244C4C] hover:-translate-y-0.5 transition disabled:opacity-60"
                >
                  {saving ? "Menyimpan…" : "Simpan Jurnal"}
                </button>
              </div>
            </div>
          )}
        </div>

        <div className="space-y-5">
          <div className="bg-[#E8F0EA] rounded-3xl p-6 fade-up" data-testid="weekly-growth-card">
            <div className="flex items-center gap-2 text-[#1C302B] mb-2">
              <Sparkles size={14} /> <span className="text-sm font-medium">Weekly Growth</span>
            </div>
            <p className="text-sm text-[#1C302B] italic leading-relaxed">
              "You've shared {entries.length} entries this week. There's a beautiful shift from 'overwhelmed' to 'balanced' today. Your resilience is showing."
            </p>
          </div>
          <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] fade-up">
            <div className="text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">Focus Suggestion</div>
            <p className="text-sm text-[#1C302B] mt-2 leading-relaxed">
              Try a 5-minute breathing exercise before your next journal entry.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 mt-5">
        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]" data-testid="emotional-landscape-card">
          <div className="flex items-center justify-between mb-4">
            <div className="font-medium text-[#1C302B]">Emotional Landscape</div>
            <div className="text-xs text-[#7A9690]">{new Date().toLocaleString("en-GB", { month: "long", year: "numeric" })}</div>
          </div>
          <div className="grid grid-cols-7 gap-2 text-center text-xs text-[#7A9690] mb-2">
            {days.map((d, i) => <div key={i}>{d}</div>)}
          </div>
          <div className="grid grid-cols-7 gap-2">
            {Array.from({ length: 28 }).map((_, i) => {
              const intensity = (i * 11) % 5;
              const colors = ["bg-[#F4F7F4]", "bg-[#D8E6DD]", "bg-[#B5D5C2]", "bg-[#7DB69A]", "bg-[#2D5F5F]"];
              return <div key={i} className={`aspect-square rounded-md ${colors[intensity]}`} />;
            })}
          </div>
        </div>
        <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]" data-testid="recent-echoes-card">
          <div className="flex items-center justify-between mb-3">
            <div className="font-medium text-[#1C302B]">Recent Echoes</div>
            <div className="text-xs text-[#2D5F5F] cursor-pointer">View All</div>
          </div>
          <div className="space-y-3">
            {entries.length === 0 && <div className="text-sm text-[#7A9690]">Belum ada entri. Mulai dengan suara atau teks di atas.</div>}
            {entries.slice(0, 5).map((e) => (
              <EntryItem key={e.entry_id} entry={e} onUpdate={(u) => setEntries((all) => all.map((x) => x.entry_id === u.entry_id ? u : x))} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
