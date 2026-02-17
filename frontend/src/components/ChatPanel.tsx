import { useEffect, useRef } from 'react'
import { Bot, PanelRightOpen, Sparkles } from 'lucide-react'
import MessageBubble from './MessageBubble'
import { getNodeConfig } from './NodeBadge'

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

type Props = {
  chat: ChatMessage[]
  logs: Log[]
  isProcessing: boolean
  panelOpen: boolean
  onOpenPanel: () => void
}

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

export default function ChatPanel({ chat, logs, isProcessing, panelOpen, onOpenPanel }: Props) {
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chat, isProcessing, logs])

  return (
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
            <p style={{ fontSize: '.78rem', color: '#52525b', marginTop: 6 }}>Describe a task - I'll plan, code, and review it.</p>
          </div>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: 20, maxWidth: 760, margin: '0 auto' }}>
        {chat.map((msg, i) => (
          <MessageBubble key={i} role={msg.role} content={msg.content} />
        ))}

        {isProcessing && !panelOpen && logs.length > 0 && (
          <div className="chat-msg">
            <ActivityTicker logs={logs} onClick={onOpenPanel} />
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
  )
}
