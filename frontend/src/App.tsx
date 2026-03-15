import { TelemetryHUD } from './components/TelemetryHUD';
import { ControlPanel } from './components/ControlPanel';
import { ChatInterface } from './components/ChatInterface';
import { AuditPanel } from './components/AuditPanel';

function App() {
  return (
    <div className="app-container">
      <div className="side-panel">
        <TelemetryHUD />
        <ControlPanel />
      </div>
      <div className="main-content-area">
        <ChatInterface />
        <AuditPanel />
      </div>
    </div>
  );
}

export default App;
