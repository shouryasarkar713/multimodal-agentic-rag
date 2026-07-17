'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import { Session, Message } from '../lib/types';

interface ChatContextType {
  sessions: Session[];
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  messages: Message[];
  loadingSessions: boolean;
  loadingMessages: boolean;
  sendingMessage: boolean;
  selectedDocumentIds: string[];
  setSelectedDocumentIds: React.Dispatch<React.SetStateAction<string[]>>;
  error: string | null;
  setError: (err: string | null) => void;
  createNewSession: (title?: string, initialDocIds?: string[]) => Promise<string | null>;
  deleteSession: (id: string) => Promise<void>;
  submitQuery: (queryText: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(false);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [sendingMessage, setSendingMessage] = useState<boolean>(false);
  const [selectedDocumentIds, setSelectedDocumentIdsState] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const setSelectedDocumentIds = useCallback((update: string[] | ((prev: string[]) => string[]) | React.SetStateAction<string[]>) => {
    setSelectedDocumentIdsState((prev) => {
      const next = typeof update === 'function' ? (update as Function)(prev) : update;
      if (typeof window !== 'undefined' && activeSessionId) {
        localStorage.setItem(`session_docs_${activeSessionId}`, JSON.stringify(next));
      }
      return next;
    });
  }, [activeSessionId]);

  // Fetch all chat sessions
  const fetchSessions = useCallback(async () => {
    try {
      setLoadingSessions(true);
      const res = await api.getSessions();
      setSessions(res.sessions);
      
      // Auto-select latest session if none is selected and sessions exist
      if (res.sessions.length > 0 && !activeSessionId) {
        setActiveSessionId(res.sessions[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch sessions');
    } finally {
      setLoadingSessions(false);
    }
  }, [activeSessionId]);

  // Load message history for active session
  const fetchMessages = useCallback(async (sessionId: string) => {
    try {
      setLoadingMessages(true);
      const res = await api.getMessages(sessionId);
      setMessages(res.messages);
      setError(null);
    } catch (err: any) {
      setError(err.message || 'Failed to fetch messages');
    } finally {
      setLoadingMessages(false);
    }
  }, []);

  // Create a new session
  const createNewSession = useCallback(async (title?: string, initialDocIds?: string[]) => {
    try {
      setError(null);
      const newSession = await api.createSession(title);
      setSessions((prev) => [newSession, ...prev]);
      
      // Save initial document scope to localStorage for this new session ID
      if (initialDocIds && initialDocIds.length > 0) {
        localStorage.setItem(`session_docs_${newSession.id}`, JSON.stringify(initialDocIds));
        setSelectedDocumentIdsState(initialDocIds);
      } else {
        localStorage.removeItem(`session_docs_${newSession.id}`);
        setSelectedDocumentIdsState([]);
      }
      
      setActiveSessionId(newSession.id);
      setMessages([]);
      return newSession.id;
    } catch (err: any) {
      setError(err.message || 'Failed to create new session');
      return null;
    }
  }, []);

  // Delete a session
  const deleteSession = useCallback(async (id: string) => {
    try {
      setError(null);
      await api.deleteSession(id);
      setSessions((prev) => prev.filter((s) => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to delete session');
    }
  }, [activeSessionId]);

  // Submit chat query
  const submitQuery = useCallback(async (queryText: string) => {
    if (!queryText.trim()) return;

    let sessionId = activeSessionId;
    
    // Auto-create session if none active
    if (!sessionId) {
      const createdId = await createNewSession(queryText.substring(0, 30));
      if (!createdId) return;
      sessionId = createdId;
    }

    // 1. Optimistic User Message update
    const userMsg: Message = {
      id: Math.random().toString(), // temp ID
      role: 'user',
      content: queryText,
      created_at: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMsg]);
    setSendingMessage(true);
    setError(null);

    try {
      // 2. Call API
      const res = await api.chat({
        session_id: sessionId,
        query: queryText,
        document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
      });

      // 3. Append Assistant Message response
      const assistantMsg: Message = {
        id: res.message_id,
        role: 'assistant',
        content: res.content,
        citations: res.citations,
        figure_refs: res.figure_refs,
        confidence: res.confidence,
        trace_id: res.trace_id,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
      
      // Update session list to increment message counts / update ordering
      fetchSessions();
      
    } catch (err: any) {
      setError(err.message || 'Error executing chat completion');
      const errorMsg: Message = {
        id: Math.random().toString(),
        role: 'assistant',
        content: `⚠️ Failed to execute query: ${err.message || 'Unknown error. Check backend connection.'}`,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setSendingMessage(false);
    }
  }, [activeSessionId, selectedDocumentIds, createNewSession, fetchSessions]);

  // Fetch session messages when activeSessionId changes
  useEffect(() => {
    if (activeSessionId) {
      fetchMessages(activeSessionId);
    }
  }, [activeSessionId, fetchMessages]);

  // Load stored document selection scope when activeSessionId changes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      console.log('[DEBUG] activeSessionId changed to:', activeSessionId);
      if (activeSessionId) {
        const stored = localStorage.getItem(`session_docs_${activeSessionId}`);
        console.log('[DEBUG] stored value from localStorage:', stored);
        if (stored) {
          try {
            const parsed = JSON.parse(stored);
            console.log('[DEBUG] successfully parsed scope:', parsed);
            setSelectedDocumentIdsState(parsed);
          } catch (e) {
            console.error('[DEBUG] error parsing stored scope:', e);
            setSelectedDocumentIdsState([]);
          }
        } else {
          console.log('[DEBUG] no stored scope found, setting to []');
          setSelectedDocumentIdsState([]);
        }
      } else {
        console.log('[DEBUG] activeSessionId is null/undefined, setting to []');
        setSelectedDocumentIdsState([]);
      }
    }
  }, [activeSessionId]);

  // Initial load
  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return (
    <ChatContext.Provider
      value={{
        sessions,
        activeSessionId,
        setActiveSessionId,
        messages,
        loadingSessions,
        loadingMessages,
        sendingMessage,
        selectedDocumentIds,
        setSelectedDocumentIds,
        error,
        setError,
        createNewSession,
        deleteSession,
        submitQuery,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChatContext() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChatContext must be used within a ChatProvider');
  }
  return context;
}
