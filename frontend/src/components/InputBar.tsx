import { type RefObject } from 'react'
import { Send } from 'lucide-react'

type Props = {
  input: string
  setInput: (value: string) => void
  sendMessage: () => void
  isProcessing: boolean
  isConnected: boolean
  inputRef: RefObject<HTMLInputElement | null>
}

export default function InputBar({
  input,
  setInput,
  sendMessage,
  isProcessing,
  isConnected,
  inputRef,
}: Props) {
  return (
    <div style={{
      padding: '16px 24px', borderTop: '1px solid rgba(39,39,42,.5)',
      background: 'rgba(15,15,18,.5)', backdropFilter: 'blur(12px)', flexShrink: 0,
    }}>
      <div style={{ maxWidth: 760, margin: '0 auto' }}>
        <div style={{ position: 'relative' }}>
          <input ref={inputRef} className="input-glow"
            value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && sendMessage()}
            placeholder={isConnected ? 'Describe what you want to build...' : 'Waiting for connection...'}
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
  )
}
