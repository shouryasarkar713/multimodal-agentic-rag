'use client';

import React from 'react';
import { ChatProvider, useChatContext } from '../context/ChatContext';
import { Sidebar } from './Sidebar';

function AppLayoutContent({ children }: { children: React.ReactNode }) {
  const {
    sessions,
    activeSessionId,
    setActiveSessionId,
    createNewSession,
    deleteSession,
  } = useChatContext();

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100 font-sans antialiased">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        setActiveSessionId={setActiveSessionId}
        createNewSession={() => createNewSession()}
        deleteSession={deleteSession}
      />
      
      <div className="flex-1 pl-60 min-h-screen flex flex-col">
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>
    </div>
  );
}

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <ChatProvider>
      <AppLayoutContent>{children}</AppLayoutContent>
    </ChatProvider>
  );
}
