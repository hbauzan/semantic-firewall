import React from 'react';

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends React.Component<
  { children: React.ReactNode; label?: string },
  State
> {
  state: State = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[ErrorBoundary${this.props.label ? `: ${this.props.label}` : ''}]`, error, info.componentStack);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: '1rem',
          background: '#1a0000',
          border: '1px solid var(--danger, #f44)',
          borderRadius: '4px',
          fontSize: '0.8rem',
          color: '#f88',
        }}>
          <strong>Component Error{this.props.label ? ` (${this.props.label})` : ''}</strong>
          <div style={{ marginTop: '0.5rem', opacity: 0.7 }}>An unexpected error occurred. Check the browser console for details.</div>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{ marginTop: '0.5rem', fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
          >
            Retry
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
