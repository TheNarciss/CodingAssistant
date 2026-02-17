import { Bot, User } from 'lucide-react'

type Props = {
  role: 'user' | 'assistant'
  content: string
}

export default function MessageBubble({ role, content }: Props) {
  const isUser = role === 'user'
  return (
    <div className="chat-msg" style={{
      display: 'flex', gap: 12,
      flexDirection: isUser ? 'row-reverse' : 'row',
      alignItems: 'flex-start',
    }}>
      <div style={{
        width: 30, height: 30, borderRadius: 9, flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: isUser
          ? 'linear-gradient(135deg, #3b82f6, #2563eb)'
          : 'linear-gradient(135deg, #a78bfa, #7c3aed)',
        boxShadow: isUser
          ? '0 2px 8px rgba(59,130,246,.2)'
          : '0 2px 8px rgba(167,139,250,.2)',
      }}>
        {isUser ? <User size={13} color="#fff" /> : <Bot size={13} color="#fff" />}
      </div>
      <div style={{
        maxWidth: '80%', padding: '14px 18px',
        borderRadius: isUser ? '18px 4px 18px 18px' : '4px 18px 18px 18px',
        fontSize: '.88rem', lineHeight: 1.65,
        background: isUser
          ? 'linear-gradient(135deg, rgba(59,130,246,.12), rgba(37,99,235,.06))'
          : 'rgba(24,24,27,.5)',
        border: isUser
          ? '1px solid rgba(59,130,246,.12)'
          : '1px solid rgba(39,39,42,.5)',
        color: isUser ? '#bfdbfe' : '#d4d4d8',
      }}>
        <pre style={{
          whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: '.82rem', margin: 0,
        }}>{content}</pre>
      </div>
    </div>
  )
}
