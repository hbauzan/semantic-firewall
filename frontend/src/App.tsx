import { TelemetryHUD } from './components/TelemetryHUD';
import { ControlPanel } from './components/ControlPanel';
import { ChatInterface } from './components/ChatInterface';
import { AuditPanel } from './components/AuditPanel';
import { ErrorBoundary } from './components/ErrorBoundary';

function App() {
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
        <ErrorBoundary label="ChatInterface">
          <ChatInterface />
        </ErrorBoundary>
        <ErrorBoundary label="AuditPanel">
          <AuditPanel />
        </ErrorBoundary>
      </div>
    </div>
  );
}

export default App;
