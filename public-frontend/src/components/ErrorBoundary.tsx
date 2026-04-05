import { Component, type ReactNode, type ErrorInfo } from 'react';

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
}

interface State {
  hasError: boolean;
  isChunkError: boolean;
}

/**
 * Error Boundary that catches chunk loading failures from React.lazy().
 * On chunk error: auto-reloads the page once to fetch fresh chunks.
 * On other errors: shows a retry button.
 */
export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, isChunkError: false };
  }

  static getDerivedStateFromError(error: Error): State {
    const isChunkError =
      error.name === 'ChunkLoadError' ||
      error.message.includes('Failed to fetch dynamically imported module') ||
      error.message.includes('Loading chunk') ||
      error.message.includes('Loading CSS chunk') ||
      error.message.includes('Importing a module script failed');

    return { hasError: true, isChunkError };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary]', error.message, errorInfo.componentStack);

    if (this.state.isChunkError) {
      // Prevent infinite reload loop: only auto-reload once per session
      const reloadKey = 'chunk-error-reload';
      const lastReload = sessionStorage.getItem(reloadKey);
      const now = Date.now();

      if (!lastReload || now - parseInt(lastReload) > 10000) {
        sessionStorage.setItem(reloadKey, String(now));
        window.location.reload();
      }
    }
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '400px',
          gap: '1rem',
          color: '#8b949e',
        }}>
          <div style={{ fontSize: '1.1rem', color: '#e6edf3' }}>
            {this.state.isChunkError
              ? 'A new version is available.'
              : 'Something went wrong.'}
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '8px 24px',
              background: '#21262d',
              border: '1px solid #30363d',
              borderRadius: '6px',
              color: '#e6edf3',
              cursor: 'pointer',
              fontSize: '0.9rem',
            }}
          >
            Reload Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
