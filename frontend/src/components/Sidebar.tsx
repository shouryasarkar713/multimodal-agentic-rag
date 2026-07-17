import React from 'react';
import Link from 'next/link';
import { useRouter, usePathname } from 'next/navigation';
import { Home, FileText, MessageSquare, BarChart2, Plus, Trash2 } from 'lucide-react';
import { Session } from '../lib/types';

interface SidebarProps {
  sessions: Session[];
  activeSessionId: string | null;
  setActiveSessionId: (id: string) => void;
  createNewSession: (title?: string) => Promise<string | null>;
  deleteSession: (id: string) => void;
  setSelectedDocumentIds: React.Dispatch<React.SetStateAction<string[]>>;
}

export function Sidebar({
  sessions,
  activeSessionId,
  setActiveSessionId,
  createNewSession,
  deleteSession,
  setSelectedDocumentIds,
}: SidebarProps) {
  const router = useRouter();
  const pathname = usePathname();

  const navItems = [
    { label: 'Home', href: '/', icon: Home },
    { label: 'Documents', href: '/documents', icon: FileText },
    { label: 'Chat', href: '/chat', icon: MessageSquare },
    { label: 'Compare', href: '/compare', icon: BarChart2 },
  ];

  return (
    <div className="w-60 bg-slate-950/70 backdrop-blur-xl border-r border-slate-800/60 flex flex-col h-screen fixed left-0 top-0 text-slate-100 z-10 shadow-2xl">
      {/* Brand Header */}
      <div className="p-5 border-b border-slate-800/65 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-indigo-600 border border-indigo-400/35 flex items-center justify-center font-bold text-white shadow-lg neon-glow">
          R
        </div>
        <div>
          <h1 className="font-extrabold text-md tracking-tight bg-gradient-to-r from-indigo-400 to-violet-400 bg-clip-text text-transparent">
            Research Copilot
          </h1>
          <p className="text-[10px] text-slate-500 font-bold tracking-wider">
            AGENTIC MULTIMODAL RAG
          </p>
        </div>
      </div>

      {/* Main Navigation Links */}
      <nav className="p-4 flex flex-col gap-1.5">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          const handleClick = async (e: React.MouseEvent) => {
            if (item.label === 'Chat') {
              e.preventDefault();
              setSelectedDocumentIds([]); // Clear document scope selection
              await createNewSession(); // Start a new conversation
              if (pathname !== '/chat') {
                router.push('/chat');
              }
            }
          };

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={handleClick}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 group relative overflow-hidden ${
                isActive
                  ? 'bg-indigo-600/10 text-indigo-400 border-l-4 border-indigo-500 pl-2 rounded-l-none'
                  : 'text-slate-400 hover:bg-slate-800/40 hover:text-slate-250'
              }`}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <Icon
                className={`w-4 h-4 transition-transform duration-200 group-hover:scale-110 relative z-10 ${
                  isActive ? 'text-indigo-400' : 'text-slate-400'
                }`}
              />
              <span className="relative z-10">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Divider */}
      <div className="px-4 py-2 flex items-center justify-between border-t border-slate-800/40 mt-2">
        <span className="text-[10px] uppercase font-bold tracking-wider text-slate-500 pl-1">
          Conversations
        </span>
        <button
          onClick={async () => {
            await createNewSession();
            if (pathname !== '/chat') {
              router.push('/chat');
            }
          }}
          className="p-1 rounded-md text-slate-400 hover:bg-slate-800 hover:text-indigo-400 transition-colors"
          title="New Chat Session"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Scrollable Sessions List */}
      <div className="flex-1 overflow-y-auto px-4 pb-4 flex flex-col gap-1.5 select-none scrollbar-thin">
        {sessions.length === 0 ? (
          <div className="text-center py-6 text-xs text-slate-655 font-medium">
            No active chats
          </div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              className={`flex items-center justify-between group px-3 py-2 rounded-lg text-xs font-semibold cursor-pointer transition-all duration-150 border ${
                activeSessionId === s.id
                  ? 'bg-slate-800/50 text-indigo-400 shadow-sm border-slate-700/40'
                  : 'text-slate-450 hover:bg-slate-800/20 hover:text-slate-200 border-transparent'
              }`}
              onClick={() => {
                setActiveSessionId(s.id);
                if (pathname !== '/chat') {
                  router.push('/chat');
                }
              }}
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
