import React from 'react';
import { TelemetryHUD } from './components/TelemetryHUD';
import { ControlPanel } from './components/ControlPanel';
import { ChatInterface } from './components/ChatInterface';

function App() {
  return (
    <div className="app-container">
      <div className="side-panel">
        <TelemetryHUD />
        <ControlPanel />
      </div>
      <ChatInterface />
    </div>
  );
}

export default App;
