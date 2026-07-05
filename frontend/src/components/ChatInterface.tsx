import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useStore } from '../store';
import { API_BASE_URL } from '../config';
import { VerdictCard } from './VerdictCard';
import { DEMO_QUERIES } from '../demoQueries';

const LOADING_STATUSES = [
  'Checking your query against the corpus…',
  'Searching semantic memory…',
  'Running firewall filters…',
];

export const ChatInterface: React.FC = () => {
  const { messages, addMessage } = useStore();
  const [input, setInput] = useState('');
  const [inputHistory, setInputHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendPrompt = useCallback(async (prompt: string) => {
    if (!prompt.trim() || isStreaming) return;

    const newMessageId = crypto.randomUUID();
    addMessage({ id: newMessageId, role: 'user', content: prompt });

    setInput('');
    setInputHistory(prev => [...prev, prompt]);
    setHistoryIdx(-1);
    setIsStreaming(true);
    let connectionFailed = false;

    try {
      const res = await fetch(`${API_BASE_URL}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt }),
      });

      if (!res.ok) {
        const errBody = await res.text();
        throw new Error(`Server error ${res.status}: ${errBody}`);
      }

      if (!res.body) throw new Error('No body in response');

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');

      const assistantMessageId = crypto.randomUUID();
      let assistantContent = '';

      addMessage({ id: assistantMessageId, role: 'assistant', content: LOADING_STATUSES[0] });

      let statusIndex = 0;
      const statusInterval = setInterval(() => {
        statusIndex = Math.min(statusIndex + 1, LOADING_STATUSES.length - 1);
        if (assistantContent === '') {
          useStore.setState((state) => ({
            messages: state.messages.map(m =>
              m.id === assistantMessageId ? { ...m, content: LOADING_STATUSES[statusIndex] } : m
            ),
            systemAction: LOADING_STATUSES[statusIndex],
          }));
        }
      }, 400);

      let streamDone = false;
      let firstChunkReceived = false;
      let buffer = '';
      while (!streamDone) {
        const { value, done } = await reader.read();
        if (done) {
          streamDone = true;
          break;
        }

        if (!firstChunkReceived) {
          firstChunkReceived = true;
          clearInterval(statusInterval);
          useStore.setState((state) => ({
            messages: state.messages.map(m =>
              m.id === assistantMessageId ? { ...m, content: '' } : m
            ),
            systemAction: 'Streaming response…',
          }));
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const parsed = JSON.parse(line);

            if (parsed.type === 'error') {
              assistantContent += `\n[ERROR]: ${parsed.text}`;
            } else if (parsed.type === 'content') {
              useStore.setState((state) => ({
                messages: state.messages.map(m =>
                  m.id === assistantMessageId
                    ? { ...m, role: 'system', content: parsed.text }
                    : m
                ),
              }));
              streamDone = true;
              break;
            } else if (parsed.response !== undefined) {
              assistantContent += parsed.response;
              useStore.setState((state) => ({
                messages: state.messages.map(m =>
                  m.id === assistantMessageId ? { ...m, content: assistantContent } : m
                ),
              }));
            }
          } catch {
            console.warn('[NDJSON parse] Skipping malformed line:', line);
          }
        }
      }
    } catch (err) {
      connectionFailed = true;
      console.error(err);
      addMessage({ id: crypto.randomUUID(), role: 'system', content: 'Failed to connect to backend engine.' });
      useStore.setState({ systemAction: 'CONNECTION_FAILED' });
    } finally {
      setIsStreaming(false);
      if (!connectionFailed) {
        useStore.setState({ systemAction: 'SYSTEM IDLE' });
      }
    }
  }, [addMessage, isStreaming]);

  const handleSend = () => sendPrompt(input);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      const newIdx = Math.min(historyIdx + 1, inputHistory.length - 1);
      if (newIdx >= 0) {
        setHistoryIdx(newIdx);
        setInput(inputHistory[inputHistory.length - 1 - newIdx]);
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      const newIdx = Math.max(historyIdx - 1, -1);
      setHistoryIdx(newIdx);
      setInput(newIdx === -1 ? '' : inputHistory[inputHistory.length - 1 - newIdx]);
    } else if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="main-panel">
      <div className="chat-history">
        {messages.map((msg) => (
          <VerdictCard key={msg.id} content={msg.content} role={msg.role} />
        ))}
        {messages.length === 0 && (
          <div className="chat-empty-state">
            <h3>Try the semantic firewall</h3>
            <ol className="onboarding-steps">
              <li>Upload a PDF corpus in the Control Panel.</li>
              <li>Keep all three filters ON in positive (allowlist) mode.</li>
              <li>Send a demo query below — or type your own.</li>
            </ol>
            <div className="demo-query-row">
              {DEMO_QUERIES.map((q) => (
                <button
                  key={q.id}
                  type="button"
                  className="demo-query-chip"
                  disabled={isStreaming}
                  onClick={() => sendPrompt(q.prompt)}
                >
                  {q.label}
                </button>
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about your loaded corpus…"
          onKeyDown={handleKeyDown}
          disabled={isStreaming}
        />
        <button type="button" onClick={handleSend} disabled={isStreaming} className={isStreaming ? 'btn-disabled' : ''}>
          {isStreaming ? 'Processing…' : 'Send'}
        </button>
      </div>
    </div>
  );
};
