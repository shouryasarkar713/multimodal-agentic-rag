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
    <div className="w-60 bg-surface border-r border-neutral-border flex flex-col h-screen fixed left-0 top-0 text-slate-100 z-10 shadow-sm font-sans">
      {/* Brand Header */}
      <div className="p-5 border-b border-neutral-border flex flex-col gap-1">
        <h1 className="font-editorial-serif text-lg font-bold text-slate-150 tracking-tight">
          Research Copilot
        </h1>
        <p className="text-[9px] text-slate-500 font-bold font-tech-mono tracking-widest uppercase pl-0.5">
          Academic Workspace
        </p>
      </div>

      {/* Main Navigation Links */}
      <nav className="p-0 flex flex-col scholarly-border-b">
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
              className={`flex items-center gap-3 px-4 py-3 text-xs font-bold font-tech-mono uppercase tracking-wider transition-all duration-150 border-l-2 border-b border-neutral-border/30 -mb-px ${
                isActive
                  ? 'bg-background/60 text-primary border-l-primary'
                  : 'text-slate-400 hover:bg-background/25 hover:text-slate-250 border-l-transparent'
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Divider */}
      <div className="px-4 py-3 flex items-center justify-between mt-2">
        <span className="text-[10px] uppercase font-bold tracking-widest text-slate-500 font-tech-mono pl-1">
          Chat Index
        </span>
        <button
          onClick={async () => {
            await createNewSession();
            if (pathname !== '/chat') {
              router.push('/chat');
            }
          }}
          className="p-1 rounded text-slate-500 hover:bg-background hover:text-primary transition-colors border border-neutral-border/20"
          title="New Chat Session"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Scrollable Sessions List */}
      <div className="flex-1 overflow-y-auto px-2 pb-4 flex flex-col select-none scrollbar-thin">
        {sessions.length === 0 ? (
          <div className="text-center py-6 text-[11px] font-tech-mono text-slate-600 uppercase tracking-wider font-semibold">
            No active index
          </div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.id}
              className={`flex items-center justify-between group px-3 py-2 text-[11px] font-medium font-sans cursor-pointer transition-all duration-150 border border-transparent border-y -my-px ${
                activeSessionId === s.id
                  ? 'bg-background/40 text-primary border-neutral-border/60'
                  : 'text-slate-455 hover:bg-background/10 hover:text-slate-200'
              }`}
              onClick={() => {
                setActiveSessionId(s.id);
                if (pathname !== '/chat') {
                  router.push('/chat');
                }
              }}
            >
              <span className="truncate pr-2 flex-1 leading-snug">{s.title}</span>
              <div className="flex items-center gap-1.5">
                <span className="px-1.5 py-0.5 text-[9px] font-tech-mono text-slate-500 border border-neutral-border/30 bg-background/20 font-bold">
                  {s.message_count || 0}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm('Delete this chat session and history?')) {
                      deleteSession(s.id);
                    }
                  }}
                  className="p-0.5 rounded text-slate-650 hover:text-red-400 hover:bg-background border border-transparent hover:border-red-500/20 opacity-0 group-hover:opacity-100 transition-all duration-150"
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
