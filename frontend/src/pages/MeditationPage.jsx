import React, { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Sparkles, Play, Pause, X } from "lucide-react";

function BreathingPlayer({ meditation, onClose }) {
  const [phase, setPhase] = useState("Inhale");
  const [count, setCount] = useState(4);
  const [cycle, setCycle] = useState(0);

  useEffect(() => {
    const seq = [
      { p: "Inhale", n: 4 },
      { p: "Hold", n: 7 },
      { p: "Exhale", n: 8 },
    ];
    let idx = 0;
    let secondsLeft = seq[0].n;
    setPhase(seq[0].p);
    setCount(seq[0].n);
    const id = setInterval(() => {
      secondsLeft -= 1;
      if (secondsLeft <= 0) {
        idx = (idx + 1) % seq.length;
        if (idx === 0) setCycle((c) => c + 1);
        secondsLeft = seq[idx].n;
        setPhase(seq[idx].p);
      }
      setCount(secondsLeft);
    }, 1000);
    return () => clearInterval(id);
  }, []);

  const scale = phase === "Inhale" ? "scale-100" : phase === "Hold" ? "scale-100" : "scale-75";
  return (
    <div className="fixed inset-0 z-50 bg-[#0F2926]/90 grid place-items-center p-4" data-testid="breathing-player">
      <button onClick={onClose} className="absolute top-5 right-5 text-white/80 hover:text-white" data-testid="close-breathing">
        <X size={24} />
      </button>
      <div className="text-center">
        <div className={`mx-auto w-56 h-56 rounded-full bg-[#2D5F5F]/40 grid place-items-center transition-transform duration-[3000ms] ${scale}`}>
          <div className="w-40 h-40 rounded-full bg-[#2D5F5F] grid place-items-center text-white">
            <div className="text-center">
              <div className="text-xs uppercase tracking-[0.18em] text-[#B8DDD4]">{phase}</div>
              <div className="text-5xl font-light mt-1" style={{ fontFamily: "Outfit, sans-serif" }}>{count}</div>
            </div>
          </div>
        </div>
        <div className="mt-6 text-white text-sm">Cycle {cycle + 1} · {meditation.title}</div>
      </div>
    </div>
  );
}

export default function MeditationPage() {
  const [items, setItems] = useState([]);
  const [active, setActive] = useState(null);
  const [playing, setPlaying] = useState(null);

  useEffect(() => {
    api.get("/meditations").then((r) => {
      setItems(r.data.items || []);
      if (r.data.items?.length) setActive(r.data.items[0]);
    }).catch(() => {});
  }, []);

  if (!active) return <div className="text-[#7A9690]">Loading…</div>;

  return (
    <div className="max-w-6xl mx-auto" data-testid="meditation-page">
      <div className="bg-[#E8F0EA] rounded-3xl p-8 sm:p-12 text-center fade-up" data-testid="featured-meditation">
        <span className="inline-flex items-center gap-2 bg-white/80 backdrop-blur text-[#2D5F5F] text-xs uppercase tracking-[0.18em] px-3 py-1.5 rounded-full">
          <Sparkles size={12} /> Featured Daily Guide
        </span>
        <h1 className="mt-5 text-3xl sm:text-5xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>
          {active.title}
        </h1>
        <p className="mt-3 text-sm sm:text-base text-[#4A635D] max-w-2xl mx-auto leading-relaxed">{active.subtitle}</p>
        <button
          onClick={() => setPlaying(active)}
          data-testid="begin-exercise-button"
          className="mt-7 rounded-full bg-[#2D5F5F] text-white px-7 py-3 text-sm font-medium hover:bg-[#244C4C] hover:-translate-y-0.5 transition inline-flex items-center gap-2"
        >
          <Play size={16} /> Begin Exercise
        </button>
        <div className="mt-8 rounded-2xl overflow-hidden">
          <img src={active.image} alt={active.title} className="w-full h-72 object-cover" />
        </div>
      </div>

      <div className="mt-8">
        <h3 className="text-xl font-medium text-[#1C302B] mb-3" style={{ fontFamily: "Outfit, sans-serif" }}>Meditation Library</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
          {items.map((m) => (
            <button
              key={m.meditation_id}
              onClick={() => setActive(m)}
              data-testid={`meditation-card-${m.meditation_id}`}
              className="bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)] text-left hover:-translate-y-1 transition group"
            >
              <div className="rounded-2xl overflow-hidden h-36">
                <img src={m.image} alt={m.title} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
              </div>
              <div className="mt-4 text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">{m.category} · {m.duration_min} min</div>
              <div className="font-medium text-[#1C302B] mt-1">{m.title}</div>
              <div className="text-sm text-[#4A635D] mt-1 line-clamp-2">{m.subtitle}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="mt-8 bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]">
        <h4 className="font-medium text-[#1C302B]">Steps in this exercise</h4>
        <ol className="list-decimal list-inside text-sm text-[#4A635D] mt-2 space-y-1">
          {active.steps?.map((s, i) => <li key={i}>{s}</li>)}
        </ol>
      </div>

      {playing && <BreathingPlayer meditation={playing} onClose={() => setPlaying(null)} />}
    </div>
  );
}
