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
    setSelectedDocumentIds,
    selectedDocumentIds,
  } = useChatContext();

  return (
    <div className="min-h-screen flex bg-slate-950 text-slate-100 font-sans antialiased">
      {/* Fixed Sidebar */}
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        setActiveSessionId={setActiveSessionId}
        createNewSession={createNewSession}
        deleteSession={deleteSession}
        setSelectedDocumentIds={setSelectedDocumentIds}
      />
      
      {/* Main Panel Content Area */}
      <div className="flex-1 pl-60 min-h-screen flex flex-col">
        <main className="flex-1 overflow-y-auto">
          {children}
        </main>
      </div>

      {/* Visual Debug Panel */}
      <div id="debug-panel" className="fixed bottom-4 right-4 bg-slate-900/90 border border-slate-800 p-4 rounded-xl max-w-sm z-50 text-[10px] font-mono text-slate-300 backdrop-blur-sm shadow-xl">
        <div>Active Session: {activeSessionId || 'null'}</div>
        <div>Selected Doc IDs: {JSON.stringify(selectedDocumentIds)}</div>
        <div>localStorage keys: {JSON.stringify(typeof window !== 'undefined' ? Object.keys(localStorage).filter(k => k.startsWith('session_docs_')) : [])}</div>
        <div>localStorage values: {JSON.stringify(typeof window !== 'undefined' ? Object.keys(localStorage).filter(k => k.startsWith('session_docs_')).map(k => `${k}=${localStorage.getItem(k)}`) : [])}</div>
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
