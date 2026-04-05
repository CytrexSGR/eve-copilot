import { Component, type ReactNode, type ErrorInfo } from 'react';

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[ErrorBoundary] Uncaught error:', error, errorInfo);
  }

  handleReset = (): void => {
    this.setState({ hasError: false, error: null });
  };

  render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback;
      }

      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          minHeight: '300px',
          padding: '2rem',
          color: '#e6edf3',
        }}>
          <div style={{
            background: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.08)',
            borderLeft: '3px solid #f85149',
            borderRadius: '8px',
            padding: '2rem',
            maxWidth: '500px',
            width: '100%',
            textAlign: 'center',
          }}>
            <h2 style={{ margin: '0 0 0.5rem', fontSize: '1.25rem', color: '#f85149' }}>
              Something went wrong
            </h2>
            <p style={{ margin: '0 0 1rem', fontSize: '0.875rem', color: '#8b949e' }}>
              {this.state.error?.message || 'An unexpected error occurred.'}
            </p>
            <button
              onClick={this.handleReset}
              style={{
                background: 'rgba(88, 166, 255, 0.15)',
                border: '1px solid rgba(88, 166, 255, 0.3)',
                color: '#58a6ff',
                padding: '0.5rem 1.5rem',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.875rem',
              }}
            >
              Try Again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
