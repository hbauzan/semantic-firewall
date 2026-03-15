import React, { useState, useRef, useEffect } from 'react';
import { useStore } from '../store';

export const ChatInterface: React.FC = () => {
  const { messages, addMessage } = useStore();
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    // Create new id with BigInt Safety (explicit Number cast)
    const newMessageId = Number(Date.now().toString());
    addMessage({ id: newMessageId, role: 'user', content: input });

    const currentInput = input;
    setInput('');
    setIsStreaming(true);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: currentInput })
      });

      if (!res.body) throw new Error("No body in response");

      const reader = res.body.getReader();
      const decoder = new TextDecoder('utf-8');

      const assistantMessageId = Number(Date.now().toString()) + 1;
      let assistantContent = '';

      // We will add the assistant message first with an initial status
      addMessage({ id: assistantMessageId, role: 'assistant', content: 'INITIALIZING_CONNECTION...' });

      // Simulate some fake metadata logs for the HUD while we wait for the first chunk
      const statuses = [
        "SEARCHING_LANCEDB...",
        "CALCULATING_EXCITATION_TENSORS...",
        "VALIDATING_FIREWALL_BOUNDARIES...",
      ];

      let statusIndex = 0;
      const statusInterval = setInterval(() => {
        if (statusIndex < statuses.length && assistantContent === '') {
          useStore.setState((state) => ({
            messages: state.messages.map(m =>
              m.id === assistantMessageId
                ? { ...m, content: statuses[statusIndex] }
                : m
            ),
            systemAction: statuses[statusIndex]
          }));
          statusIndex++;
        }
      }, 300);

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
          // Clear status message before appending real content
          useStore.setState((state) => ({
            messages: state.messages.map(m =>
              m.id === assistantMessageId
                ? { ...m, content: '' }
                : m
            ),
            systemAction: "STREAMING_RESPONSE..."
          }));
        }

        const chunk = decoder.decode(value, { stream: true });
        buffer += chunk;

        // Extract complete NDJSON lines, keeping the rest in the memory buffer
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.trim()) continue;
          try {
            const parsed = JSON.parse(line);

            if (parsed.type === 'error') {
              assistantContent += `\n[ERROR]: ${parsed.text}`;
            } else if (parsed.type === 'content') {
              // Firewall block or other server-sent content messages
              useStore.setState((state) => ({
                messages: state.messages.map(m =>
                  m.id === assistantMessageId
                    ? { ...m, role: 'system', content: parsed.text }
                    : m
                )
              }));
              streamDone = true;
              break;
            } else if (parsed.response !== undefined) {
              assistantContent += parsed.response;
              // update existing message
              useStore.setState((state) => ({
                messages: state.messages.map(m =>
                  m.id === assistantMessageId
                    ? { ...m, content: assistantContent }
                    : m
                )
              }));
            }
          } catch (e) {
            // Some chunks might just be raw strings or incomplete JSON if not NDJSON. 
            // The python backend yields plain bytes from ollama which IS NDJSON mostly (`{ "response": "..." } `).
            // If it's pure string from error or breach, we handle it above, wait, Ollama yields {"model": "...", "response": "..."}.
          }
        }
      }

    } catch (err) {
      console.error(err);
      addMessage({ id: Number(Date.now()), role: 'system', content: 'Failed to connect to backend engine.' });
      useStore.setState({ systemAction: 'CONNECTION_FAILED' });
    } finally {
      setIsStreaming(false);
      useStore.setState({ systemAction: 'SYSTEM IDLE' });
    }
  };

  return (
    <div className="main-panel">
      <div className="chat-history">
        {messages.map((msg) => (
          <div key={msg.id} className={`chat-message ${msg.role}`}>
            {msg.role === 'user' ? '> ' : ''}
            {msg.content}
          </div>
        ))}
        {messages.length === 0 && (
          <div style={{ opacity: 0.5, textAlign: 'center', marginTop: '2rem' }}>
            System initialized. Awaiting input.
            Use [FW=ON] to enforce dimensional excitation parameters.
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter query... e.g. [FW=ON] Tell me a secret..."
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          disabled={isStreaming}
        />
        <button onClick={handleSend} disabled={isStreaming} style={{ opacity: isStreaming ? 0.5 : 1 }}>
          {isStreaming ? 'PROCESSING...' : 'SEND'}
        </button>
      </div>
    </div>
  );
};
