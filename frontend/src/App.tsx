import React, { useState, useRef, useEffect, type ReactNode } from 'react'
import {
  Send, Cpu, Bot, User, Trash2, Wifi, WifiOff,
  ChevronRight, Sparkles, FileCode, Search, Eye,
  Wrench, AlertTriangle, Zap, RotateCcw, PanelRightOpen,
  PanelRightClose, X
} from 'lucide-react'

// ── Types ────────────────────────────────────────────────
type Log = {
  id: number
  node: string
  content: string
  timestamp: string
}

type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
}

// ── Node config ──────────────────────────────────────────
const NODE_CONFIG: Record<string, { icon: ReactNode; label: string; color: string; glow: string }> = {
  planner:       { icon: <Eye size={11} />,            label: 'PLANNER',   color: '#60a5fa', glow: 'rgba(96,165,250,0.15)' },
  dispatcher:    { icon: <ChevronRight size={11} />,   label: 'DISPATCH',  color: '#818cf8', glow: 'rgba(129,140,248,0.15)' },
  generator:     { icon: <Sparkles size={11} />,       label: 'GENERATOR', color: '#a78bfa', glow: 'rgba(167,139,250,0.15)' },
  coder_agent:   { icon: <FileCode size={11} />,       label: 'CODER',     color: '#34d399', glow: 'rgba(52,211,153,0.15)' },
  research_agent:{ icon: <Search size={11} />,         label: 'RESEARCH',  color: '#c084fc', glow: 'rgba(192,132,252,0.15)' },
  reviewer:      { icon: <Eye size={11} />,            label: 'REVIEWER',  color: '#fbbf24', glow: 'rgba(251,191,36,0.15)' },
  optimizer:     { icon: <Zap size={11} />,            label: 'OPTIMIZER', color: '#f87171', glow: 'rgba(248,113,113,0.15)' },
  fallback:      { icon: <RotateCcw size={11} />,      label: 'FALLBACK',  color: '#fb923c', glow: 'rgba(251,146,60,0.15)' },
  tools:         { icon: <Wrench size={11} />,         label: 'TOOLS',     color: '#2dd4bf', glow: 'rgba(45,212,191,0.15)' },
  system:        { icon: <Wifi size={11} />,           label: 'SYSTEM',    color: '#71717a', glow: 'rgba(113,113,122,0.15)' },
  error:         { icon: <AlertTriangle size={11} />,  label: 'ERROR',     color: '#ef4444', glow: 'rgba(239,68,68,0.15)' },
}

function getNodeConfig(node: string) {
  return NODE_CONFIG[node] || { icon: <Cpu size={11} />, label: node.toUpperCase(), color: '#71717a', glow: 'rgba(113,113,122,0.15)' }
}

// ── Typing dots ──────────────────────────────────────────
function TypingIndicator() {
  return (
    <div style={{ display: 'flex', gap: 4, alignItems: 'center', padding: '4px 0' }}>
      {[0, 1, 2].map(i => (
        <span key={i} style={{
          width: 6, height: 6, borderRadius: '50%', background: '#a78bfa',
          animation: `typingDot 1.4s ease-in-out ${i * 0.16}s infinite`,
        }} />
      ))}
    </div>
  )
}

// ── Inline activity ticker (visible when panel is closed) ──
function ActivityTicker({ logs, onClick }: { logs: Log[]; onClick: () => void }) {
  const last = logs[logs.length - 1]
  if (!last) return null
  const cfg = getNodeConfig(last.node)

  return (
    <button onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 10,
      width: '100%', padding: '10px 16px',
      background: 'rgba(167,139,250,0.03)',
      border: '1px solid rgba(167,139,250,0.08)',
      borderRadius: 12, cursor: 'pointer',
      transition: 'all 0.2s ease',
      fontFamily: "'DM Sans', sans-serif",
    }}
    onMouseEnter={e => {
      e.currentTarget.style.background = 'rgba(167,139,250,0.07)'
      e.currentTarget.style.borderColor = 'rgba(167,139,250,0.18)'
    }}
    onMouseLeave={e => {
      e.currentTarget.style.background = 'rgba(167,139,250,0.03)'
      e.currentTarget.style.borderColor = 'rgba(167,139,250,0.08)'
    }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, flex: 1, minWidth: 0 }}>
        <span style={{
          display: 'inline-flex', alignItems: 'center', gap: 4,
          fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.05em',
          padding: '2px 7px', borderRadius: 5,
          background: cfg.glow, color: cfg.color,
          border: `1px solid ${cfg.color}20`,
          fontFamily: "'JetBrains Mono', monospace", flexShrink: 0,
        }}>
          {cfg.icon} {cfg.label}
        </span>
        <span style={{
          fontSize: '0.75rem', color: '#52525b',
          fontFamily: "'JetBrains Mono', monospace",
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {last.content}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.65rem', color: '#3f3f46', flexShrink: 0 }}>
        <span style={{
          background: 'rgba(167,139,250,0.15)', color: '#a78bfa',
          padding: '1px 6px', borderRadius: 4, fontWeight: 600,
          fontFamily: "'JetBrains Mono', monospace",
        }}>{logs.length}</span>
        <PanelRightOpen size={13} color="#52525b" />
      </div>
    </button>
  )
}

// ── Main ─────────────────────────────────────────────────
class ErrorBoundary extends React.Component<{ children: ReactNode }, { hasError: boolean }> {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh',
          background: '#09090b', color: '#a1a1aa', fontFamily: 'monospace',
        }}>
          <p>Something went wrong. Please refresh the page.</p>
        </div>
      )
    }
    return this.props.children
  }
}

function App() {
  const [input, setInput] = useState('')
  const [logs, setLogs] = useState<Log[]>([])
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  const [panelOpen, setPanelOpen] = useState(false)
  const [userClosedPanel, setUserClosedPanel] = useState(false)

  const ws = useRef<WebSocket | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => { logsEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [logs])
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [chat])

  // Auto-open panel when processing starts (unless user closed it manually)
  useEffect(() => {
    if (isProcessing && !userClosedPanel) setPanelOpen(true)
  }, [isProcessing, userClosedPanel])

  // ── WebSocket ──────────────────────────────────────────
  const connectWebSocket = () => {
    ws.current = new WebSocket('ws://localhost:8000/ws')
    ws.current.onopen = () => {
      setIsConnected(true)
      setLogs(prev => [...prev, {
        id: Date.now(), node: 'system',
        content: 'Connection established.',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }])
    }
    ws.current.onclose = () => {
      setIsConnected(false)
      setTimeout(connectWebSocket, 3000)
    }
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'done') { setIsProcessing(false); return }
      if (data.type === 'answer') {
        setChat(prev => [...prev, { role: 'assistant', content: data.content }])
      } else {
        setLogs(prev => [...prev, {
          id: Date.now() + Math.random(), node: data.node,
          content: data.content,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
        }])
      }
    }
  }

  useEffect(() => { connectWebSocket(); return () => ws.current?.close() }, [])

  const sendMessage = () => {
    if (!input.trim() || isProcessing || !isConnected) return
    setChat(prev => [...prev, { role: 'user', content: input }])
    setLogs([])
    setIsProcessing(true)
    setUserClosedPanel(false) // reset preference on new message
    ws.current?.send(JSON.stringify({ message: input }))
    setInput('')
    inputRef.current?.focus()
  }

  const closePanel = () => { setPanelOpen(false); setUserClosedPanel(true) }

  return (
    <>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap');
        *, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'DM Sans', -apple-system, sans-serif; background: #0a0a0b; overflow: hidden; }
        ::selection { background: rgba(167,139,250,0.3); color: #fff; }
        @keyframes typingDot { 0%,60%,100% { opacity:.3; transform:translateY(0); } 30% { opacity:1; transform:translateY(-4px); } }
        @keyframes fadeIn { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:translateY(0); } }
        @keyframes slideIn { from { opacity:0; transform:translateX(-8px); } to { opacity:1; transform:translateX(0); } }
        @keyframes pulse { 0%,100% { opacity:1; } 50% { opacity:.5; } }
        .log-entry { animation: slideIn .25s ease; }
        .chat-msg { animation: fadeIn .35s ease; }
        .input-glow:focus { box-shadow: 0 0 0 2px rgba(167,139,250,.25), 0 0 24px rgba(167,139,250,.08); border-color: rgba(167,139,250,.3) !important; }
        .scrollbar-thin::-webkit-scrollbar { width: 4px; }
        .scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
        .scrollbar-thin::-webkit-scrollbar-thumb { background: rgba(63,63,70,.3); border-radius: 4px; }
        .scrollbar-thin::-webkit-scrollbar-thumb:hover { background: rgba(63,63,70,.6); }
        .send-btn { transition: all .2s ease; }
        .send-btn:hover:not(:disabled) { background: #8b5cf6; box-shadow: 0 4px 16px rgba(167,139,250,.3); transform: translateY(-1px); }
        .send-btn:disabled { opacity: .3; cursor: not-allowed; }
        .hover-btn { transition: all .15s ease; }
        .hover-btn:hover { background: rgba(167,139,250,.1); color: #a78bfa; }
        .clear-hover:hover { background: rgba(239,68,68,.1); color: #f87171; }
      `}</style>

      <div style={{
        display: 'flex', height: '100vh', width: '100vw',
        background: '#0a0a0b', color: '#e4e4e7',
        fontFamily: "'DM Sans', -apple-system, sans-serif",
      }}>

        {/* ═══ MAIN — CHAT ═══ */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          background: 'linear-gradient(180deg, #0a0a0b 0%, #0c0c0f 100%)',
          minWidth: 0,
        }}>

          {/* Header */}
          <div style={{
            padding: '12px 24px', borderBottom: '1px solid rgba(39,39,42,.5)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'rgba(15,15,18,.8)', backdropFilter: 'blur(12px)', flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{
                width: 34, height: 34, borderRadius: 10,
                background: 'linear-gradient(135deg, #a78bfa, #6d28d9)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                boxShadow: '0 4px 12px rgba(167,139,250,.2)',
              }}>
                <Bot size={16} color="#fff" />
              </div>
              <div>
                <div style={{ fontWeight: 600, fontSize: '.92rem', letterSpacing: '-.01em', color: '#fafafa' }}>
                  Magnificent 8
                </div>
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 6,
                  fontSize: '.68rem', fontWeight: 500, marginTop: 1,
                  color: isConnected ? '#34d399' : '#f87171',
                }}>
                  <span style={{
                    width: 5, height: 5, borderRadius: '50%',
                    background: isConnected ? '#34d399' : '#f87171',
                    animation: isConnected ? 'pulse 2s ease infinite' : 'none',
                    boxShadow: isConnected ? '0 0 6px rgba(52,211,153,.4)' : 'none',
                  }} />
                  {isConnected ? 'Connected' : 'Reconnecting...'}
                </div>
              </div>
            </div>

            <button className="hover-btn" onClick={() => panelOpen ? closePanel() : setPanelOpen(true)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '6px 12px', borderRadius: 8,
                background: 'none', border: '1px solid rgba(39,39,42,.5)',
                color: '#52525b', cursor: 'pointer', fontSize: '.72rem',
                fontWeight: 500, fontFamily: "'JetBrains Mono', monospace",
              }}>
              {panelOpen ? <PanelRightClose size={14} /> : <PanelRightOpen size={14} />}
              {!panelOpen && logs.length > 0 && (
                <span style={{
                  background: 'rgba(167,139,250,.15)', color: '#a78bfa',
                  padding: '1px 6px', borderRadius: 4, fontWeight: 600, fontSize: '.62rem',
                }}>{logs.length}</span>
              )}
            </button>
          </div>

          {/* Messages */}
          <div className="scrollbar-thin" style={{ flex: 1, overflowY: 'auto', padding: '24px' }}>
            {chat.length === 0 && !isProcessing && (
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                justifyContent: 'center', height: '100%', gap: 16, opacity: .4,
              }}>
                <div style={{
                  width: 64, height: 64, borderRadius: 16,
                  background: 'rgba(167,139,250,.08)', border: '1px solid rgba(167,139,250,.12)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}>
                  <Sparkles size={28} color="#a78bfa" />
                </div>
                <div style={{ textAlign: 'center' }}>
                  <p style={{ fontSize: '.95rem', fontWeight: 500, color: '#a1a1aa' }}>What should I build?</p>
                  <p style={{ fontSize: '.78rem', color: '#52525b', marginTop: 6 }}>Describe a task — I'll plan, code, and review it.</p>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 760, margin: '0 auto' }}>
              {chat.map((msg, i) => (
                <div key={i} className="chat-msg" style={{
                  display: 'flex', gap: 12,
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row',
                  alignItems: 'flex-start',
                }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 9, flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: msg.role === 'user'
                      ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
                      : 'linear-gradient(135deg, #a78bfa, #7c3aed)',
                    boxShadow: msg.role === 'user'
                      ? '0 2px 8px rgba(59,130,246,.2)'
                      : '0 2px 8px rgba(167,139,250,.2)',
                  }}>
                    {msg.role === 'user' ? <User size={13} color="#fff" /> : <Bot size={13} color="#fff" />}
                  </div>
                  <div style={{
                    maxWidth: '80%', padding: '14px 18px',
                    borderRadius: msg.role === 'user' ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
                    fontSize: '.88rem', lineHeight: 1.65,
                    background: msg.role === 'user'
                      ? 'linear-gradient(135deg, rgba(59,130,246,.12), rgba(37,99,235,.06))'
                      : 'rgba(24,24,27,.5)',
                    border: msg.role === 'user'
                      ? '1px solid rgba(59,130,246,.12)'
                      : '1px solid rgba(39,39,42,.5)',
                    color: msg.role === 'user' ? '#bfdbfe' : '#d4d4d8',
                  }}>
                    <pre style={{
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                      fontFamily: "'JetBrains Mono', monospace",
                      fontSize: '.82rem', margin: 0,
                    }}>{msg.content}</pre>
                  </div>
                </div>
              ))}

              {/* Inline ticker when panel closed & agent working */}
              {isProcessing && !panelOpen && logs.length > 0 && (
                <div className="chat-msg">
                  <ActivityTicker logs={logs} onClick={() => setPanelOpen(true)} />
                </div>
              )}

              {isProcessing && (
                <div className="chat-msg" style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                  <div style={{
                    width: 30, height: 30, borderRadius: 9, flexShrink: 0,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: 'linear-gradient(135deg, #a78bfa, #7c3aed)',
                    boxShadow: '0 2px 8px rgba(167,139,250,.2)',
                  }}>
                    <Bot size={13} color="#fff" />
                  </div>
                  <div style={{
                    padding: '14px 18px', borderRadius: '4px 18px 18px 18px',
                    background: 'rgba(24,24,27,.5)', border: '1px solid rgba(39,39,42,.5)',
                  }}>
                    <TypingIndicator />
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>
          </div>

          {/* Input */}
          <div style={{
            padding: '16px 24px', borderTop: '1px solid rgba(39,39,42,.5)',
            background: 'rgba(15,15,18,.5)', backdropFilter: 'blur(12px)', flexShrink: 0,
          }}>
            <div style={{ maxWidth: 760, margin: '0 auto' }}>
              <div style={{ position: 'relative' }}>
                <input ref={inputRef} className="input-glow"
                  value={input} onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && sendMessage()}
                  placeholder={isConnected ? "Describe what you want to build..." : "Waiting for connection..."}
                  disabled={isProcessing || !isConnected}
                  style={{
                    width: '100%', padding: '14px 52px 14px 18px',
                    background: 'rgba(24,24,27,.4)', border: '1px solid rgba(39,39,42,.5)',
                    borderRadius: 12, outline: 'none', color: '#e4e4e7',
                    fontSize: '.88rem', fontFamily: "'JetBrains Mono', monospace",
                    transition: 'all .2s ease',
                  }}
                />
                <button className="send-btn" onClick={sendMessage}
                  disabled={isProcessing || !isConnected || !input.trim()}
                  style={{
                    position: 'absolute', right: 6, top: '50%', transform: 'translateY(-50%)',
                    width: 36, height: 36, borderRadius: 9,
                    background: '#a78bfa', border: 'none', cursor: 'pointer',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#0a0a0b',
                  }}>
                  <Send size={15} />
                </button>
              </div>
              <div style={{ display: 'flex', gap: 8, marginTop: 10, flexWrap: 'wrap' }}>
                {['Create a snake game', 'Build a REST API', 'Fix bugs in main.py'].map(s => (
                  <button key={s} onClick={() => { setInput(s); inputRef.current?.focus() }}
                    style={{
                      fontSize: '.7rem', color: '#3f3f46', background: 'none',
                      border: '1px solid rgba(39,39,42,.35)', borderRadius: 8,
                      padding: '5px 10px', cursor: 'pointer',
                      fontFamily: "'DM Sans', sans-serif", transition: 'all .15s ease',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(167,139,250,.25)'; e.currentTarget.style.color = '#71717a' }}
                    onMouseLeave={e => { e.currentTarget.style.borderColor = 'rgba(39,39,42,.35)'; e.currentTarget.style.color = '#3f3f46' }}
                  >{s}</button>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* ═══ SLIDING PANEL — THOUGHT PROCESS ═══ */}
        <div style={{
          width: panelOpen ? 420 : 0,
          minWidth: panelOpen ? 420 : 0,
          opacity: panelOpen ? 1 : 0,
          overflow: 'hidden',
          display: 'flex', flexDirection: 'column',
          background: 'linear-gradient(180deg, #08080a 0%, #0a0a0d 100%)',
          borderLeft: panelOpen ? '1px solid rgba(39,39,42,.4)' : 'none',
          transition: 'width .35s cubic-bezier(.4,0,.2,1), min-width .35s cubic-bezier(.4,0,.2,1), opacity .25s ease',
          flexShrink: 0,
        }}>

          {/* Panel Header */}
          <div style={{
            padding: '12px 20px', borderBottom: '1px solid rgba(39,39,42,.35)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'rgba(12,12,15,.8)', flexShrink: 0,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Cpu size={14} color="#3f3f46" />
              <span style={{
                fontSize: '.68rem', fontWeight: 600, letterSpacing: '.12em',
                textTransform: 'uppercase', color: '#3f3f46',
                fontFamily: "'JetBrains Mono', monospace",
              }}>Reasoning</span>
              {logs.length > 0 && (
                <span style={{
                  fontSize: '.6rem', fontWeight: 600, color: '#52525b',
                  background: 'rgba(39,39,42,.3)', padding: '2px 7px',
                  borderRadius: 5, fontFamily: "'JetBrains Mono', monospace",
                }}>{logs.length}</span>
              )}
            </div>
            <div style={{ display: 'flex', gap: 2 }}>
              <button className="clear-hover hover-btn" onClick={() => setLogs([])}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: '#27272a', padding: 5, borderRadius: 6,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}><Trash2 size={13} /></button>
              <button className="hover-btn" onClick={closePanel}
                style={{
                  background: 'none', border: 'none', cursor: 'pointer',
                  color: '#27272a', padding: 5, borderRadius: 6,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                }}><X size={13} /></button>
            </div>
          </div>

          {/* Logs */}
          <div className="scrollbar-thin" style={{ flex: 1, overflowY: 'auto', padding: '12px 16px' }}>
            {logs.length === 0 && (
              <div style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                height: '100%', color: '#1c1c1e', fontSize: '.75rem',
                fontFamily: "'JetBrains Mono', monospace",
              }}>Waiting for activity...</div>
            )}

            <div style={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {logs.map((log) => {
                const cfg = getNodeConfig(log.node)
                return (
                  <div key={log.id} className="log-entry" style={{
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    padding: '7px 10px', borderRadius: 6,
                    transition: 'background .15s ease', cursor: 'default',
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(24,24,27,.35)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <span style={{
                      fontSize: '.58rem', color: '#1c1c1e',
                      fontFamily: "'JetBrains Mono', monospace",
                      flexShrink: 0, marginTop: 3, fontVariantNumeric: 'tabular-nums', minWidth: 48,
                    }}>{log.timestamp}</span>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 3,
                      fontSize: '.55rem', fontWeight: 700, letterSpacing: '.05em',
                      padding: '2px 6px', borderRadius: 4,
                      background: cfg.glow, color: cfg.color,
                      border: `1px solid ${cfg.color}18`,
                      fontFamily: "'JetBrains Mono', monospace",
                      flexShrink: 0, marginTop: 1, minWidth: 68,
                    }}>{cfg.icon}{cfg.label}</span>
                    <span style={{
                      fontSize: '.73rem', color: '#52525b',
                      fontFamily: "'JetBrains Mono', monospace",
                      lineHeight: 1.5, wordBreak: 'break-word',
                    }}>{log.content}</span>
                  </div>
                )
              })}
              <div ref={logsEndRef} />
            </div>
          </div>

          {/* Status */}
          <div style={{
            padding: '8px 20px', borderTop: '1px solid rgba(39,39,42,.25)',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            background: 'rgba(12,12,15,.4)', flexShrink: 0,
          }}>
            <div style={{
              display: 'flex', alignItems: 'center', gap: 6,
              fontSize: '.62rem', color: '#1c1c1e',
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              {isConnected ? <Wifi size={10} /> : <WifiOff size={10} />}
              ws://localhost:8000
            </div>
            {isProcessing && (
              <div style={{
                fontSize: '.62rem', color: '#a78bfa',
                fontFamily: "'JetBrains Mono', monospace",
                display: 'flex', alignItems: 'center', gap: 5,
              }}>
                <span style={{
                  width: 5, height: 5, borderRadius: '50%',
                  background: '#a78bfa', animation: 'pulse 1s ease infinite',
                }} />
                Processing
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  )
}

export default function WrappedApp() {
  return (
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  )
}