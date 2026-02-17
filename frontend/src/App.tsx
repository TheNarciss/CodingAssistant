import React, { useState, useRef, useEffect, type ReactNode } from 'react'
import { Bot, PanelRightOpen, PanelRightClose } from 'lucide-react'
import ChatPanel from './components/ChatPanel.tsx'
import InputBar from './components/InputBar.tsx'
import LogPanel from './components/LogPanel.tsx'

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
  const inputRef = useRef<HTMLInputElement>(null)

  // Auto-open panel when processing starts (unless user closed it manually)
  useEffect(() => {
    if (isProcessing && !userClosedPanel) setPanelOpen(true)
  }, [isProcessing, userClosedPanel])

  // ── WebSocket ──────────────────────────────────────────
  const connectWebSocket = () => {
    if (
      ws.current?.readyState === WebSocket.OPEN ||
      ws.current?.readyState === WebSocket.CONNECTING
    ) {
      return
    }
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
      ws.current = null
      setTimeout(connectWebSocket, 5000)
    }
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'ping') { ws.current?.send(JSON.stringify({ type: 'pong' })); return }
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

  const clearSandbox = async () => {
    try {
      await fetch('http://localhost:8000/api/cleanup', { method: 'POST' })
      setLogs([])
    } catch {
      setLogs(prev => [...prev, {
        id: Date.now(), node: 'error',
        content: 'Cleanup failed. Is the backend running?',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
      }])
    }
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

          <ChatPanel
            chat={chat}
            logs={logs}
            isProcessing={isProcessing}
            panelOpen={panelOpen}
            onOpenPanel={() => setPanelOpen(true)}
          />

          <InputBar
            input={input}
            setInput={setInput}
            sendMessage={sendMessage}
            isProcessing={isProcessing}
            isConnected={isConnected}
            inputRef={inputRef}
          />
        </div>
        <LogPanel
          logs={logs}
          panelOpen={panelOpen}
          closePanel={closePanel}
          clearLogs={() => setLogs([])}
          clearSandbox={clearSandbox}
          isConnected={isConnected}
          isProcessing={isProcessing}
        />
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