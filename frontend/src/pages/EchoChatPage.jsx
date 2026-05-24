import React, { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, BACKEND_URL } from "@/lib/api";
import { Send, Paperclip, CalendarPlus, Sparkles, Wifi, WifiOff } from "lucide-react";
import { toast } from "sonner";

function buildWsUrl(bookingId) {
  // Convert https://... to wss://...
  const httpUrl = BACKEND_URL || window.location.origin;
  const wsUrl = httpUrl.replace(/^http/i, "ws");
  return `${wsUrl}/api/ws/chat/${bookingId}`;
}

export default function EchoChatPage() {
  const navigate = useNavigate();
  const { bookingId } = useParams();
  const [bookings, setBookings] = useState([]);
  const [activeBookingId, setActiveBookingId] = useState(bookingId || null);
  const [messages, setMessages] = useState([]);
  const [booking, setBooking] = useState(null);
  const [input, setInput] = useState("");
  const [streamingMessage, setStreamingMessage] = useState(null); // {message_id, content}
  const [typing, setTyping] = useState(false);
  const [wsStatus, setWsStatus] = useState("disconnected"); // disconnected | connecting | open
  const scrollRef = useRef(null);
  const wsRef = useRef(null);

  // Load bookings list
  useEffect(() => {
    api.get("/bookings").then((r) => {
      const items = r.data.items || [];
      setBookings(items);
      if (!activeBookingId && items.length) setActiveBookingId(items[0].booking_id);
    }).catch(() => {});
    // eslint-disable-next-line
  }, []);

  // Load chat history + open WebSocket when booking changes
  useEffect(() => {
    if (!activeBookingId) return;
    api.get(`/chat/${activeBookingId}`).then((r) => {
      setBooking(r.data.booking);
      setMessages(r.data.messages || []);
    }).catch((e) => {
      if (e.response?.status === 403) toast.error("Booking tidak ditemukan");
    });

    // Close existing WS
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {}
      wsRef.current = null;
    }
    setStreamingMessage(null);
    setTyping(false);
    setWsStatus("connecting");

    const ws = new WebSocket(buildWsUrl(activeBookingId));
    wsRef.current = ws;

    ws.onopen = () => setWsStatus("open");
    ws.onclose = () => setWsStatus("disconnected");
    ws.onerror = () => setWsStatus("disconnected");
    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "ready") {
          // ready to send messages
        } else if (msg.type === "user_message") {
          setMessages((m) => {
            // remove optimistic placeholder
            const filtered = m.filter((x) => !String(x.message_id).startsWith("tmp_"));
            return [...filtered, msg.message];
          });
        } else if (msg.type === "typing") {
          setTyping(true);
        } else if (msg.type === "ai_chunk") {
          setTyping(false);
          setStreamingMessage({ message_id: msg.message_id, content: msg.content_so_far });
        } else if (msg.type === "ai_message") {
          setStreamingMessage(null);
          setTyping(false);
          setMessages((m) => [...m, msg.message]);
        } else if (msg.type === "error") {
          setTyping(false);
          setStreamingMessage(null);
          toast.error(msg.message || "Pesan gagal diproses");
        }
      } catch (e) {
        // ignore
      }
    };

    return () => {
      try { ws.close(); } catch {}
    };
  }, [activeBookingId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, streamingMessage, typing]);

  const send = async (e) => {
    e?.preventDefault?.();
    if (!input.trim() || !activeBookingId) return;
    const msg = input.trim();
    setInput("");

    // If WS open, send via WS. Otherwise fall back to REST.
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      // optimistic local echo
      setMessages((m) => [...m, { message_id: `tmp_${Date.now()}`, role: "user", content: msg, created_at: new Date().toISOString() }]);
      wsRef.current.send(JSON.stringify({ type: "user_message", content: msg }));
    } else {
      // Fallback REST
      setMessages((m) => [...m, { message_id: `tmp_${Date.now()}`, role: "user", content: msg, created_at: new Date().toISOString() }]);
      setTyping(true);
      try {
        const { data } = await api.post("/chat/send", { booking_id: activeBookingId, message: msg });
        setMessages((m) => {
          const filtered = m.filter((x) => !String(x.message_id).startsWith("tmp_"));
          return [...filtered, data.user_message, data.ai_message];
        });
      } catch (err) {
        toast.error("Pesan gagal dikirim. Coba lagi.");
      } finally {
        setTyping(false);
      }
    }
  };

  // Empty state - no bookings
  if (bookings.length === 0) {
    return (
      <div className="max-w-3xl mx-auto" data-testid="echochat-empty">
        <div className="bg-white rounded-3xl p-10 shadow-[0_8px_32px_rgba(45,95,95,0.06)] text-center">
          <div className="w-16 h-16 rounded-full bg-[#E8F0EA] mx-auto grid place-items-center text-[#2D5F5F]"><Sparkles size={28} /></div>
          <h2 className="text-2xl font-medium text-[#1C302B] mt-4" style={{ fontFamily: "Outfit, sans-serif" }}>Belum ada percakapan</h2>
          <p className="text-sm text-[#4A635D] mt-2 max-w-md mx-auto">
            EchoChat aktif setelah kamu booking sesi konsultasi. Pilih dokter di Consultation untuk memulai percakapan privat.
          </p>
          <button
            onClick={() => navigate("/consultation")}
            data-testid="goto-consultation-from-empty"
            className="mt-6 inline-flex items-center gap-2 rounded-full bg-[#2D5F5F] text-white px-6 py-3 text-sm font-medium hover:bg-[#244C4C] transition"
          >
            <CalendarPlus size={16} /> Book Konsultasi
          </button>
        </div>
      </div>
    );
  }

  const renderMessage = (m, isStream = false) => {
    const isUser = m.role === "user";
    return (
      <div key={m.message_id} className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
        <div className={`max-w-[78%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
          isUser ? "bg-[#2D5F5F] text-white rounded-br-md" : "bg-[#E8F0EA] text-[#1C302B] rounded-bl-md"
        }`}>
          <div className="whitespace-pre-wrap leading-relaxed">
            {m.content}
            {isStream && <span className="inline-block w-1.5 h-4 bg-[#2D5F5F] ml-0.5 align-middle animate-pulse" />}
          </div>
          {!isStream && (
            <div className={`text-[10px] mt-1 ${isUser ? "text-white/70" : "text-[#7A9690]"}`}>
              {new Date(m.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="max-w-6xl mx-auto" data-testid="echochat-page">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-5 h-[calc(100vh-200px)] min-h-[520px]">
        <aside className="hidden lg:block bg-white rounded-3xl p-3 shadow-[0_8px_32px_rgba(45,95,95,0.06)] overflow-y-auto">
          <div className="px-3 py-2 text-[11px] uppercase tracking-[0.18em] text-[#7A9690]">Konsultasi</div>
          {bookings.map((b) => (
            <button
              key={b.booking_id}
              onClick={() => setActiveBookingId(b.booking_id)}
              data-testid={`booking-tab-${b.booking_id}`}
              className={`w-full text-left flex items-center gap-3 px-3 py-3 rounded-2xl transition ${
                activeBookingId === b.booking_id ? "bg-[#E8F0EA]" : "hover:bg-[#F4F7F4]"
              }`}
            >
              <img src={b.doctor_image} alt={b.doctor_name} className="w-10 h-10 rounded-xl object-cover" />
              <div className="min-w-0">
                <div className="text-sm font-medium text-[#1C302B] truncate">{b.doctor_name}</div>
                <div className="text-[11px] text-[#7A9690] truncate">{b.date} · {b.time}</div>
              </div>
            </button>
          ))}
        </aside>

        {/* Mobile booking selector */}
        <div className="lg:hidden bg-white rounded-3xl p-2 shadow-[0_8px_32px_rgba(45,95,95,0.06)] overflow-x-auto">
          <div className="flex gap-2">
            {bookings.map((b) => (
              <button
                key={b.booking_id}
                onClick={() => setActiveBookingId(b.booking_id)}
                className={`shrink-0 flex items-center gap-2 px-3 py-2 rounded-2xl transition ${
                  activeBookingId === b.booking_id ? "bg-[#E8F0EA]" : "hover:bg-[#F4F7F4]"
                }`}
              >
                <img src={b.doctor_image} alt={b.doctor_name} className="w-8 h-8 rounded-lg object-cover" />
                <div className="text-xs font-medium text-[#1C302B]">{b.doctor_name}</div>
              </button>
            ))}
          </div>
        </div>

        <section className="lg:col-span-3 bg-white rounded-3xl shadow-[0_8px_32px_rgba(45,95,95,0.06)] flex flex-col overflow-hidden">
          <div className="px-5 py-3 border-b border-[#D8E6DD] flex items-center gap-3">
            {booking && <>
              <img src={booking.doctor_image} alt={booking.doctor_name} className="w-10 h-10 rounded-xl object-cover" />
              <div className="flex-1 min-w-0">
                <div className="font-medium text-[#1C302B] truncate">{booking.doctor_name}</div>
                <div className="text-[11px] text-[#2D5F5F] flex items-center gap-1.5">
                  {wsStatus === "open" ? <><Wifi size={10} /> Live</> : wsStatus === "connecting" ? "Connecting…" : <><WifiOff size={10} /> Offline</>}
                </div>
              </div>
            </>}
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 sm:p-5 space-y-3 bg-[#F8FBF8]" data-testid="chat-messages">
            {messages.length === 0 && !streamingMessage && !typing && (
              <div className="text-center text-sm text-[#7A9690] py-10">Sapa {booking?.doctor_name || "dokter"} kamu untuk memulai percakapan…</div>
            )}
            {messages.map((m) => renderMessage(m))}
            {streamingMessage && renderMessage({
              message_id: streamingMessage.message_id,
              role: "assistant",
              content: streamingMessage.content,
              created_at: new Date().toISOString(),
            }, true)}
            {typing && !streamingMessage && (
              <div className="flex justify-start">
                <div className="bg-[#E8F0EA] rounded-2xl px-4 py-3 text-sm text-[#4A635D]">
                  <span className="inline-flex gap-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2D5F5F] animate-bounce" />
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2D5F5F] animate-bounce" style={{ animationDelay: "0.2s" }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-[#2D5F5F] animate-bounce" style={{ animationDelay: "0.4s" }} />
                  </span>
                </div>
              </div>
            )}
          </div>

          <form onSubmit={send} className="border-t border-[#D8E6DD] p-3 flex items-center gap-2">
            <button type="button" className="hidden sm:grid w-10 h-10 rounded-full bg-[#F4F7F4] place-items-center text-[#4A635D]" aria-label="Attach" data-testid="chat-attach">
              <Paperclip size={16} />
            </button>
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Tulis pesan…"
              className="flex-1 bg-[#F4F7F4] rounded-full px-5 py-3 outline-none text-sm focus:ring-2 ring-[#E8F0EA]"
              data-testid="chat-input"
            />
            <button
              type="submit"
              disabled={!input.trim()}
              className="w-10 h-10 rounded-full bg-[#2D5F5F] text-white grid place-items-center hover:bg-[#244C4C] transition disabled:opacity-60"
              data-testid="chat-send-button"
              aria-label="Send"
            >
              <Send size={16} />
            </button>
          </form>
        </section>
      </div>
    </div>
  );
}
