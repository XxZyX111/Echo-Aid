import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import { Search, Star, ShieldCheck, ChevronLeft, ChevronRight } from "lucide-react";
import { toast } from "sonner";

const CATEGORIES = [
  { id: "anxiety", label: "Anxiety" },
  { id: "academic_stress", label: "Academic Stress" },
  { id: "depression", label: "Depression" },
  { id: "relationships", label: "Relationships" },
  { id: "trauma", label: "Trauma" },
];

const TIME_SLOTS = ["09:00 AM", "10:30 AM", "11:00 AM", "01:00 PM", "02:30 PM", "04:30 PM"];

function weekDates(offset = 0) {
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - today.getDay() + 1 + offset * 7);
  return Array.from({ length: 7 }).map((_, i) => {
    const d = new Date(start);
    d.setDate(start.getDate() + i);
    return d;
  });
}

export default function ConsultationPage() {
  const navigate = useNavigate();
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("anxiety");
  const [doctors, setDoctors] = useState([]);
  const [selectedDoctor, setSelectedDoctor] = useState(null);
  const [weekOffset, setWeekOffset] = useState(0);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedTime, setSelectedTime] = useState(null);
  const [booking, setBooking] = useState(false);

  const week = useMemo(() => weekDates(weekOffset), [weekOffset]);

  const load = async () => {
    const params = {};
    if (category) params.category = category;
    if (q.trim()) params.q = q.trim();
    const r = await api.get("/doctors", { params });
    setDoctors(r.data.items || []);
    if (!selectedDoctor && r.data.items?.length) setSelectedDoctor(r.data.items[0]);
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [category]);

  const onSearch = (e) => {
    e.preventDefault();
    load();
  };

  const confirmBooking = async () => {
    if (!selectedDoctor) return toast.info("Pilih dokter dulu");
    if (!selectedDate) return toast.info("Pilih tanggal dulu");
    if (!selectedTime) return toast.info("Pilih jam dulu");
    setBooking(true);
    try {
      const dateStr = selectedDate.toISOString().slice(0, 10);
      const { data } = await api.post("/bookings", {
        doctor_id: selectedDoctor.doctor_id,
        date: dateStr,
        time: selectedTime,
        category,
      });
      toast.success("Booking dikonfirmasi! Buka EchoChat untuk memulai percakapan.");
      navigate(`/echochat/${data.booking_id}`);
    } catch (e) {
      toast.error("Gagal booking. Coba lagi.");
    } finally {
      setBooking(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto" data-testid="consultation-page">
      <div className="mb-6">
        <h1 className="text-2xl sm:text-3xl font-medium text-[#1C302B]" style={{ fontFamily: "Outfit, sans-serif" }}>Consultation</h1>
        <p className="text-[#7A9690] text-sm mt-1 max-w-2xl">
          Connect with our network of specialized psychologists in a private, secure environment designed for your peace of mind.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-5">
        <aside className="lg:col-span-2 space-y-4">
          <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)]" data-testid="find-support-card">
            <div className="font-medium text-[#1C302B] mb-3">Find Support</div>
            <form onSubmit={onSearch} className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-[#F4F7F4] border border-transparent focus-within:border-[#2D5F5F]">
              <Search size={16} className="text-[#7A9690]" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search speciality…"
                className="flex-1 bg-transparent outline-none text-sm"
                data-testid="doctor-search-input"
              />
            </form>
            <div className="mt-4 text-xs uppercase tracking-[0.18em] text-[#7A9690]">Categories</div>
            <div className="flex flex-wrap gap-2 mt-2">
              {CATEGORIES.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setCategory(c.id)}
                  data-testid={`category-${c.id}`}
                  className={`text-xs px-3 py-1.5 rounded-full transition ${
                    category === c.id ? "bg-[#B8DDD4] text-[#1C302B] font-semibold" : "bg-[#F4F7F4] text-[#4A635D] hover:bg-[#E8F0EA]"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>
          <div className="bg-[#E8F0EA] rounded-3xl p-5 flex items-start gap-3" data-testid="confidential-badge">
            <div className="w-10 h-10 rounded-2xl bg-white grid place-items-center text-[#2D5F5F]"><ShieldCheck size={18} /></div>
            <div>
              <div className="font-medium text-[#1C302B] text-sm">100% Confidential</div>
              <div className="text-xs text-[#4A635D]">Your sessions are end-to-end encrypted. We prioritize your anonymity and safety.</div>
            </div>
          </div>
        </aside>

        <div className="lg:col-span-3 space-y-4">
          {doctors.map((d) => (
            <div
              key={d.doctor_id}
              data-testid={`doctor-card-${d.doctor_id}`}
              className={`bg-white rounded-3xl p-5 shadow-[0_8px_32px_rgba(45,95,95,0.06)] flex gap-4 items-center transition cursor-pointer ${
                selectedDoctor?.doctor_id === d.doctor_id ? "ring-2 ring-[#2D5F5F]" : ""
              }`}
              onClick={() => setSelectedDoctor(d)}
            >
              <img src={d.image} alt={d.name} className="w-20 h-20 rounded-2xl object-cover" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-[#1C302B]">{d.name}</div>
                  <div className="flex items-center gap-1 text-xs text-[#1C302B]"><Star size={12} className="fill-[#E0B25A] stroke-[#E0B25A]" /> {d.rating}</div>
                </div>
                <div className="text-xs text-[#7A9690]">{d.title}</div>
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {d.specialties?.map((s) => (
                    <span key={s} className="text-[11px] bg-[#F4F7F4] text-[#4A635D] px-2 py-1 rounded-full">{s}</span>
                  ))}
                </div>
                <div className="flex items-center justify-between mt-3">
                  <div className="text-xs text-[#7A9690]">Next available: {d.next_available}</div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setSelectedDoctor(d); }}
                    data-testid={`book-now-${d.doctor_id}`}
                    className="rounded-full bg-[#2D5F5F] text-white px-4 py-1.5 text-xs font-medium hover:bg-[#244C4C] transition"
                  >
                    Book Now
                  </button>
                </div>
              </div>
            </div>
          ))}

          {selectedDoctor && (
            <div className="bg-white rounded-3xl p-6 shadow-[0_8px_32px_rgba(45,95,95,0.06)] fade-up" data-testid="booking-card">
              <div className="flex items-center justify-between">
                <h3 className="font-medium text-[#1C302B]">Select Date & Time</h3>
                <div className="flex gap-2">
                  <button onClick={() => setWeekOffset((w) => w - 1)} className="w-8 h-8 rounded-full bg-[#F4F7F4] grid place-items-center" data-testid="prev-week"><ChevronLeft size={16} /></button>
                  <button onClick={() => setWeekOffset((w) => w + 1)} className="w-8 h-8 rounded-full bg-[#F4F7F4] grid place-items-center" data-testid="next-week"><ChevronRight size={16} /></button>
                </div>
              </div>
              <div className="grid grid-cols-7 gap-2 mt-4 text-center text-[11px] uppercase tracking-[0.15em] text-[#7A9690]">
                {["Mon","Tue","Wed","Thu","Fri","Sat","Sun"].map((d) => <div key={d}>{d}</div>)}
              </div>
              <div className="grid grid-cols-7 gap-2 mt-1">
                {week.map((d) => {
                  const isSel = selectedDate?.toDateString() === d.toDateString();
                  return (
                    <button
                      key={d.toISOString()}
                      onClick={() => setSelectedDate(d)}
                      data-testid={`date-${d.toISOString().slice(0, 10)}`}
                      className={`aspect-square rounded-2xl text-sm font-medium transition ${
                        isSel ? "bg-[#2D5F5F] text-white" : "bg-[#F4F7F4] text-[#1C302B] hover:bg-[#E8F0EA]"
                      }`}
                    >
                      {d.getDate()}
                    </button>
                  );
                })}
              </div>

              <div className="mt-5 text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">Available Time Slots</div>
              <div className="flex flex-wrap gap-2 mt-2">
                {TIME_SLOTS.map((t) => (
                  <button
                    key={t}
                    onClick={() => setSelectedTime(t)}
                    data-testid={`time-${t.replace(/\s/g, "")}`}
                    className={`text-xs px-4 py-2 rounded-full border transition ${
                      selectedTime === t ? "bg-[#E8F0EA] border-[#2D5F5F] text-[#1C302B] font-semibold" : "border-[#D8E6DD] text-[#4A635D] hover:bg-[#F4F7F4]"
                    }`}
                  >
                    {t}
                  </button>
                ))}
              </div>

              <button
                onClick={confirmBooking}
                disabled={booking}
                data-testid="confirm-booking-button"
                className="mt-6 w-full rounded-full bg-[#2D5F5F] text-white py-3 font-medium hover:bg-[#244C4C] hover:-translate-y-0.5 transition disabled:opacity-60"
              >
                {booking ? "Memproses…" : "Konfirmasi Booking"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
