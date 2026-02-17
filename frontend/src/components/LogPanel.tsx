import { useEffect, useRef } from 'react'
import { Cpu, Trash2, X, Wifi, WifiOff } from 'lucide-react'
import { getNodeConfig } from './NodeBadge'

type Log = {
  id: number
  node: string
  content: string
  timestamp: string
}

type Props = {
  logs: Log[]
  panelOpen: boolean
  closePanel: () => void
  clearLogs: () => void
  clearSandbox: () => void
  isConnected: boolean
  isProcessing: boolean
}

function extractDiff(content: string) {
  const beforeMatch = content.match(/\[DIFF_BEFORE\]([\s\S]*?)\[\/DIFF_BEFORE\]/)
  const afterMatch = content.match(/\[DIFF_AFTER\]([\s\S]*?)\[\/DIFF_AFTER\]/)
  const cleaned = content
    .replace(/\[DIFF_BEFORE\][\s\S]*?\[\/DIFF_BEFORE\]/g, '')
    .replace(/\[DIFF_AFTER\][\s\S]*?\[\/DIFF_AFTER\]/g, '')
    .trim()

  return {
    cleaned,
    before: beforeMatch?.[1] ?? '',
    after: afterMatch?.[1] ?? '',
  }
}

export default function LogPanel({
  logs,
  panelOpen,
  closePanel,
  clearLogs,
  clearSandbox,
  isConnected,
  isProcessing,
}: Props) {
  const logsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const handleCleanup = () => {
    clearSandbox()
    clearLogs()
  }

  return (
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
          <button className="clear-hover hover-btn" onClick={handleCleanup}
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
            const diff = extractDiff(log.content)
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
                <div style={{
                  fontSize: '.73rem', color: '#52525b',
                  fontFamily: "'JetBrains Mono', monospace",
                  lineHeight: 1.5, wordBreak: 'break-word',
                  display: 'flex', flexDirection: 'column', gap: 6,
                }}>
                  {diff.cleaned && <span>{diff.cleaned}</span>}
                  {diff.before && (
                    <pre style={{
                      margin: 0, padding: '8px 10px',
                      background: 'rgba(239,68,68,.08)',
                      border: '1px solid rgba(239,68,68,.2)',
                      borderRadius: 6, color: '#f87171',
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                    }}>{diff.before}</pre>
                  )}
                  {diff.after && (
                    <pre style={{
                      margin: 0, padding: '8px 10px',
                      background: 'rgba(34,197,94,.08)',
                      border: '1px solid rgba(34,197,94,.2)',
                      borderRadius: 6, color: '#4ade80',
                      whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                    }}>{diff.after}</pre>
                  )}
                </div>
              </div>
            )
          })}
          <div ref={logsEndRef} />
        </div>
      </div>

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
  )
}
