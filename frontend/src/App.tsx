import { useState, useRef, useEffect } from 'react'
import { Send, Terminal, Cpu, Bot, User, Trash2 } from 'lucide-react'

// Imports Shadcn
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Badge } from "@/components/ui/badge"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Separator } from "@/components/ui/separator"

// Types
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

function App() {
  const [input, setInput] = useState('')
  const [logs, setLogs] = useState<Log[]>([])
  const [chat, setChat] = useState<ChatMessage[]>([])
  const [isProcessing, setIsProcessing] = useState(false)
  const [isConnected, setIsConnected] = useState(false)
  
  const ws = useRef<WebSocket | null>(null)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll Logs
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [logs])

  // Auto-scroll Chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [chat])

  const connectWebSocket = () => {
    ws.current = new WebSocket('ws://localhost:8000/ws')

    ws.current.onopen = () => {
      console.log('Connecté au backend')
      setIsConnected(true)
      setLogs(prev => [...prev, { id: Date.now(), node: 'system', content: '🔌 Connexion établie avec l\'agent.', timestamp: new Date().toLocaleTimeString() }])
    }

    ws.current.onclose = () => {
      setIsConnected(false)
      setTimeout(connectWebSocket, 3000) // Reconnexion auto
    }

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'done') {
        setIsProcessing(false)
        return
      }

      // Si c'est une réponse finale pour le chat
      if (data.type === 'answer') {
        setChat(prev => [...prev, { role: 'assistant', content: data.content }])
      } 
      // Sinon, c'est un log technique (pensée de l'IA)
      else {
        setLogs(prev => [...prev, {
          id: Date.now(),
          node: data.node,
          content: data.content,
          timestamp: new Date().toLocaleTimeString()
        }])
      }
    }
  }

  useEffect(() => {
    connectWebSocket()
    return () => ws.current?.close()
  }, [])

  const sendMessage = () => {
    if (!input.trim() || isProcessing || !isConnected) return

    // 1. Affiche le message de l'user tout de suite
    setChat(prev => [...prev, { role: 'user', content: input }])
    
    // 2. Nettoie les logs précédents pour plus de clarté
    setLogs([]) 
    setIsProcessing(true)
    
    // 3. Envoie au backend
    ws.current?.send(JSON.stringify({ message: input }))
    setInput('')
  }

  // Couleurs pour les logs techniques
  const getNodeColor = (node: string) => {
    switch (node) {
      case 'planner': return 'border-blue-500/50 bg-blue-500/10 text-blue-400'
      case 'generator': return 'border-purple-500/50 bg-purple-500/10 text-purple-400'
      case 'reviewer': return 'border-yellow-500/50 bg-yellow-500/10 text-yellow-400'
      case 'optimizer': return 'border-red-500/50 bg-red-500/10 text-red-400'
      case 'tools': return 'border-green-500/50 bg-green-500/10 text-green-400'
      default: return 'border-gray-500/50 bg-gray-500/10 text-gray-400'
    }
  }

  return (
    <div className="flex h-screen bg-zinc-950 text-zinc-50 font-sans overflow-hidden">
      
      {/* --- GAUCHE : CHAT (HUMAN vs AI) --- */}
      <div className="w-1/2 flex flex-col border-r border-zinc-800 bg-zinc-950">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/50">
          <div className="flex items-center gap-2">
            <Bot className="w-6 h-6 text-indigo-400" />
            <div>
              <h1 className="font-bold text-lg leading-none">AI Developer</h1>
              <span className={`text-xs ${isConnected ? 'text-green-500' : 'text-red-500'}`}>
                {isConnected ? '● Online' : '● Offline'}
              </span>
            </div>
          </div>
          <Badge variant="secondary" className="bg-zinc-800">Llama 3.2</Badge>
        </div>
        
        <ScrollArea className="flex-1 p-4">
          <div className="space-y-6">
            {chat.length === 0 && (
              <div className="text-center text-zinc-500 mt-20">
                <Terminal className="w-12 h-12 mx-auto mb-4 opacity-20" />
                <p>Prêt à coder. Que dois-je faire ?</p>
              </div>
            )}
            
            {chat.map((msg, i) => (
              <div key={i} className={`flex gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                <Avatar className="w-8 h-8">
                  <AvatarFallback className={msg.role === 'user' ? 'bg-blue-600' : 'bg-indigo-600'}>
                    {msg.role === 'user' ? <User size={14}/> : <Bot size={14}/>}
                  </AvatarFallback>
                </Avatar>
                
                <div className={`p-4 rounded-2xl max-w-[80%] text-sm leading-relaxed shadow-sm ${
                  msg.role === 'user' 
                    ? 'bg-blue-600/20 text-blue-100 rounded-tr-sm' 
                    : 'bg-zinc-800/50 text-zinc-100 border border-zinc-700 rounded-tl-sm'
                }`}>
                  <div className="whitespace-pre-wrap font-mono text-xs md:text-sm">
                    {msg.content}
                  </div>
                </div>
              </div>
            ))}
            
            {isProcessing && (
              <div className="flex gap-3">
                <Avatar className="w-8 h-8"><AvatarFallback className="bg-indigo-600"><Bot size={14}/></AvatarFallback></Avatar>
                <div className="flex items-center gap-2 text-zinc-400 text-sm italic">
                  <Cpu className="w-4 h-4 animate-spin" />
                  L'agent réfléchit...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>
        </ScrollArea>

        <div className="p-4 bg-zinc-900 border-t border-zinc-800">
          <div className="flex gap-2 relative">
            <Input 
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Ex: Crée un fichier snake.py..."
              disabled={isProcessing || !isConnected}
              className="bg-zinc-950 border-zinc-700 text-zinc-100 pr-12 focus-visible:ring-indigo-500 font-mono"
            />
            <Button 
              size="icon"
              onClick={sendMessage} 
              disabled={isProcessing || !isConnected}
              className="absolute right-1 top-1 h-8 w-8 bg-indigo-600 hover:bg-indigo-700"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>

      {/* --- DROITE : CERVEAU (LOGS TECHNIQUES) --- */}
      <div className="w-1/2 flex flex-col bg-zinc-950/50">
        <div className="p-4 border-b border-zinc-800 flex items-center justify-between bg-zinc-900/30">
          <div className="flex items-center gap-2 text-zinc-400">
            <Cpu className="w-5 h-5" />
            <h2 className="font-semibold text-sm tracking-wider">THOUGHT PROCESS</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={() => setLogs([])} className="h-8 w-8 hover:bg-zinc-800 hover:text-red-400 transition-colors">
            <Trash2 className="w-4 h-4" />
          </Button>
        </div>

        <ScrollArea className="flex-1 p-4">
          <div className="space-y-3 font-mono text-xs">
            {logs.map((log) => (
              <Card key={log.id} className={`p-3 border-l-4 border-y-0 border-r-0 rounded-r-md bg-opacity-10 ${getNodeColor(log.node)}`}>
                <div className="flex items-center justify-between mb-2 opacity-70">
                  <Badge variant="outline" className="text-[10px] h-5 border-current px-1 uppercase tracking-widest">{log.node}</Badge>
                  <span className="text-zinc-500 text-[10px]">{log.timestamp}</span>
                </div>
                <div className="whitespace-pre-wrap opacity-90 leading-relaxed break-words text-zinc-300">
                  {log.content}
                </div>
              </Card>
            ))}
            <div ref={logsEndRef} />
          </div>
        </ScrollArea>
      </div>

    </div>
  )
}

export default App