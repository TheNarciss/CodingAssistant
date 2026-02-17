import React, { type ReactNode } from 'react'
import {
  Cpu, Eye, ChevronRight, Sparkles, FileCode, Search,
  Wrench, AlertTriangle, Zap, RotateCcw, Wifi
} from 'lucide-react'

export type NodeConfig = { icon: ReactNode; label: string; color: string; glow: string }

export const NODE_CONFIG: Record<string, NodeConfig> = {
  planner: { icon: <Eye size={11} />, label: 'PLANNER', color: '#60a5fa', glow: 'rgba(96,165,250,0.15)' },
  dispatcher: { icon: <ChevronRight size={11} />, label: 'DISPATCH', color: '#818cf8', glow: 'rgba(129,140,248,0.15)' },
  generator: { icon: <Sparkles size={11} />, label: 'GENERATOR', color: '#a78bfa', glow: 'rgba(167,139,250,0.15)' },
  coder_agent: { icon: <FileCode size={11} />, label: 'CODER', color: '#34d399', glow: 'rgba(52,211,153,0.15)' },
  research_agent: { icon: <Search size={11} />, label: 'RESEARCH', color: '#c084fc', glow: 'rgba(192,132,252,0.15)' },
  reviewer: { icon: <Eye size={11} />, label: 'REVIEWER', color: '#fbbf24', glow: 'rgba(251,191,36,0.15)' },
  optimizer: { icon: <Zap size={11} />, label: 'OPTIMIZER', color: '#f87171', glow: 'rgba(248,113,113,0.15)' },
  fallback: { icon: <RotateCcw size={11} />, label: 'FALLBACK', color: '#fb923c', glow: 'rgba(251,146,60,0.15)' },
  tools: { icon: <Wrench size={11} />, label: 'TOOLS', color: '#2dd4bf', glow: 'rgba(45,212,191,0.15)' },
  system: { icon: <Wifi size={11} />, label: 'SYSTEM', color: '#71717a', glow: 'rgba(113,113,122,0.15)' },
  error: { icon: <AlertTriangle size={11} />, label: 'ERROR', color: '#ef4444', glow: 'rgba(239,68,68,0.15)' },
}

export function getNodeConfig(node: string): NodeConfig {
  return NODE_CONFIG[node] || { icon: <Cpu size={11} />, label: node.toUpperCase(), color: '#71717a', glow: 'rgba(113,113,122,0.15)' }
}

export default function NodeBadge({ node }: { node: string }) {
  const cfg = getNodeConfig(node)
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 3,
      fontSize: '.55rem', fontWeight: 700, letterSpacing: '.05em',
      padding: '2px 6px', borderRadius: 4,
      background: cfg.glow, color: cfg.color,
      border: `1px solid ${cfg.color}18`,
      fontFamily: "'JetBrains Mono', monospace",
      flexShrink: 0, marginTop: 1, minWidth: 68,
    }}>{cfg.icon}{cfg.label}</span>
  )
}
