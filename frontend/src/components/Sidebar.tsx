import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, FileText, MessageSquare, BarChart2, Plus, Trash2 } from 'lucide-react';
import { Session } from '../lib/types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  setActiveSessionId: (id: string) => void;
  createNewSession: () => void;
  deleteSession: (id: string) => void;
}

export function Sidebar({
  sessions,
  activeSessionId,
  setActiveSessionId,
  createNewSession,
  deleteSession,
}: SidebarProps) {
  const pathname = usePathname();

  const navItems = [
    { label: 'Home', href: '/', icon: Home },
    { label: 'Documents', href: '/documents', icon: FileText },
    { label: 'Chat', href: '/chat', icon: MessageSquare },
    { label: 'Compare', href: '/compare', icon: BarChart2 },
  ];

  return (
    <div className="w-60 bg-slate-900 border-r border-slate-800 flex flex-col h-screen fixed left-0 top-0 text-slate-100 z-10">
      <div className="p-5 border-b border-slate-800 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center font-bold text-white shadow-lg shadow-indigo-500/30">
          R
        </div>
        <div>
          <h1 className="font-extrabold text-md tracking-tight bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Research Copilot
          </h1>
          <p className="text-[10px] text-slate-400 font-medium tracking-wide">
            AGENTIC MULTIMODAL RAG
          </p>
        </div>
      </div>

      <nav className="p-4 flex flex-col gap-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 group ${
                isActive
                  ? 'bg-indigo-600/10 text-indigo-400'
                  : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
              }`}
            >
              <Icon
                className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 ${
                  isActive ? 'text-indigo-400' : 'text-slate-400'
                }`}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-4 py-2 flex items-center justify-between border-t border-slate-800/60">
        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500">
          Conversations
        </span>
        <button
          onClick={() => createNewSession()}
          className="p-1 rounded-md text-slate-400 hover:bg-slate-800 hover:text-indigo-400 transition-colors"
          title="New Chat Session"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4 flex flex-col gap-1 select-none scrollbar-thin">
        {sessions.length === 0 ? (
          <div className="text-center py-6 text-xs text-slate-600 font-medium">
            No active chats
          </div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              className={`flex items-center justify-between group px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer transition-all duration-150 ${
                activeSessionId === s.id
                  ? 'bg-slate-800 text-indigo-400 shadow-sm border border-slate-700/50'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-200 border border-transparent'
              }`}
              onClick={() => setActiveSessionId(s.id)}
            >
              <span className="truncate pr-2 flex-1">{s.title}</span>
              <div className="flex items-center gap-2">
                <span className="px-1.5 py-0.5 rounded-full bg-slate-800/80 text-[10px] font-mono text-slate-500 border border-slate-700/20 group-hover:bg-slate-700/60">
                  {s.message_count || 0}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this chat session and history?')) {
                      deleteSession(s.id);
                    }
                  }}
                  className="p-0.5 rounded text-slate-600 hover:text-red-400 hover:bg-slate-700 opacity-0 group-hover:opacity-100 transition-all duration-150"
                  title="Delete chat"
                >
                  <Trash2 className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
