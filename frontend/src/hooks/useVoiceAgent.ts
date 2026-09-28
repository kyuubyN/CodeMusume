import { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../services/api';
import { ToolCall, VoiceAgent, VoiceStatus } from '../services/voiceAgent';

export interface TranscriptItem {
  id: number;
  role: 'user' | 'agnes' | 'event';
  text: string;
  interrupted?: boolean;
}

let nextId = 1;

export function useVoiceAgent(onToolCall: (call: ToolCall) => Promise<unknown>) {
  const agentRef = useRef<VoiceAgent | null>(null);
  const toolRef = useRef(onToolCall);
  toolRef.current = onToolCall;

  const [status, setStatus] = useState<VoiceStatus>('idle');
  const [partial, setPartial] = useState('');
  const [log, setLog] = useState<TranscriptItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [muted, setMutedState] = useState(false);

  const push = useCallback((role: TranscriptItem['role'], text: string, interrupted = false) => {
    if (!text.trim()) return;
    setLog((prev) => [...prev.slice(-80), { id: nextId++, role, text, interrupted }]);
  }, []);

  const start = useCallback(async () => {
    if (agentRef.current) return;
    setError(null);
    const agent = new VoiceAgent(
      { getToken: api.getVoiceToken, getSession: api.getVoiceSession },
      {
        onStatus: setStatus,
        onUserPartial: setPartial,
        onUserFinal: (t) => push('user', t),
        onAgentText: (t, interrupted) => push('agnes', t, interrupted),
        onToolCall: (call) => toolRef.current(call),
        onError: setError,
        onEnded: () => {
          agentRef.current = null;
          setPartial('');
        },
      }
    );
    agentRef.current = agent;
    await agent.start();
  }, [push]);

  const stop = useCallback(() => {
    agentRef.current?.stop();
    agentRef.current = null;
  }, []);

  const setMuted = useCallback((m: boolean) => {
    agentRef.current?.setMuted(m);
    setMutedState(m);
  }, []);

  const sendText = useCallback(
    (text: string) => {
      push('user', text);
      agentRef.current?.sendText(text);
    },
    [push]
  );

  const notify = useCallback((event: string) => {
    if (agentRef.current?.isLive) agentRef.current.notify(event);
  }, []);

  const refreshPrompt = useCallback(async () => {
    const agent = agentRef.current;
    if (!agent?.isLive) return;
    try {
      agent.updateSystemPrompt(await api.getVoicePrompt());
    } catch {
      /* stale prompt is fine; tool results carry fresh numbers anyway */
    }
  }, []);

  useEffect(() => () => agentRef.current?.stop(), []);

  const live = status !== 'idle' && status !== 'connecting' && status !== 'error';

  return {
    status,
    live,
    partial,
    log,
    error,
    muted,
    start,
    stop,
    setMuted,
    sendText,
    notify,
    push,
    refreshPrompt,
    agentRef,
    clearError: () => setError(null),
  };
}

export type VoiceController = ReturnType<typeof useVoiceAgent>;
