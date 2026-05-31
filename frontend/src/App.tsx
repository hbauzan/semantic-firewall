import { useState } from 'react';
import { TelemetryHUD } from './components/TelemetryHUD';
import { ControlPanel } from './components/ControlPanel';
import { ChatInterface } from './components/ChatInterface';
import { SnifferTab } from './components/SnifferTab';
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
  const [activeTab, setActiveTab] = useState<'chat' | 'sniffer'>('chat');

  return (
    <div className="app-container">
      <div className="side-panel">
        <ErrorBoundary label="TelemetryHUD">
          <TelemetryHUD />
        </ErrorBoundary>
        <ErrorBoundary label="ControlPanel">
          <ControlPanel />
        </ErrorBoundary>
      </div>
      <div className="main-content-area">
        <div className="tab-navigation">
          <button
            id="tab-chat"
            className={`tab-btn ${activeTab === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveTab('chat')}
          >
            CHAT
          </button>
          <button
            id="tab-sniffer"
            className={`tab-btn ${activeTab === 'sniffer' ? 'active' : ''}`}
            onClick={() => setActiveTab('sniffer')}
          >
            SNIFFER
          </button>
        </div>
        {activeTab === 'chat' ? (
          <>
            <ErrorBoundary label="ChatInterface">
              <ChatInterface />
            </ErrorBoundary>
            {/* AuditPanel Removed - Redundant with Sniffer FPI */}
          </>
        ) : (
          <ErrorBoundary label="SnifferTab">
            <SnifferTab />
          </ErrorBoundary>
        )}
      </div>
    </div>
  );
}

export default App;
