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

            // We will add the assistant message first and update it
            addMessage({ id: assistantMessageId, role: 'assistant', content: '' });

            let streamDone = false;
            while (!streamDone) {
                const { value, done } = await reader.read();
                if (done) {
                    streamDone = true;
                    break;
                }

                const chunk = decoder.decode(value, { stream: true });

                // chunk can have multiple NDJSON lines
                const lines = chunk.split('\\n').filter(line => line.trim() !== '');

                for (const line of lines) {
                    try {
                        const parsed = JSON.parse(line);

                        if (parsed.type === 'error') {
                            assistantContent += \`\\n[ERROR]: \${parsed.text}\`;
            } else if (parsed.type === 'content') {
              // SECURITY BREACH case
              if (parsed.text === 'SECURITY BREACH') {
                useStore.setState((state) => ({
                  messages: state.messages.map(m => 
                    m.id === assistantMessageId 
                      ? { ...m, role: 'system', content: 'SECURITY BREACH DETECTED. CONNECTION TERMINATED.' } 
                      : m
                  )
                }));
                streamDone = true;
                break;
              }
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
    } finally {
      setIsStreaming(false);
    }
  };

  return (
    <div className="main-panel">
      <div className="chat-history">
        {messages.map((msg) => (
          <div key={msg.id} className={\`chat-message \${msg.role}\`}>
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
        <button onClick={handleSend} disabled={isStreaming}>
          {isStreaming ? '...' : 'SEND'}
        </button>
      </div>
    </div>
  );
};
