import { useState, useEffect, useCallback } from 'react';
import { api } from '../lib/api';
import { Session, Message } from '../lib/types';

export function useChat() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loadingSessions, setLoadingSessions] = useState<boolean>(false);
  const [loadingMessages, setLoadingMessages] = useState<boolean>(false);
  const [sendingMessage, setSendingMessage] = useState<boolean>(false);
  const [selectedDocumentIds, setSelectedDocumentIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const fetchSessions = useCallback(async () => {
    try {
      setLoadingSessions(true);
      const res = await api.getSessions();
      setSessions(res.sessions);
      if (res.sessions.length > 0 && !activeSessionId) {
        setActiveSessionId(res.sessions[0].id);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to fetch sessions');
    } finally {
      setLoadingSessions(false);
    }
  }, [activeSessionId]);

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

  const createNewSession = useCallback(async (title?: string) => {
    try {
      setError(null);
      const newSession = await api.createSession(title);
      setSessions((prev) => [newSession, ...prev]);
      setActiveSessionId(newSession.id);
      setMessages([]);
      return newSession.id;
    } catch (err: any) {
      setError(err.message || 'Failed to create new session');
      return null;
    }
  }, []);

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

  const submitQuery = useCallback(async (queryText: string) => {
    if (!queryText.trim()) return;

    let sessionId = activeSessionId;
    if (!sessionId) {
      const createdId = await createNewSession(queryText.substring(0, 30));
      if (!createdId) return;
      sessionId = createdId;
    }

    const userMsg: Message = {
      id: Math.random().toString(),
      role: 'user',
      content: queryText,
      created_at: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMsg]);
    setSendingMessage(true);
    setError(null);

    try {
      const res = await api.chat({
        session_id: sessionId,
        query: queryText,
        document_ids: selectedDocumentIds.length > 0 ? selectedDocumentIds : undefined,
      });

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

  useEffect(() => {
    if (activeSessionId) {
      fetchMessages(activeSessionId);
    }
  }, [activeSessionId, fetchMessages]);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  return {
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
  };
}
