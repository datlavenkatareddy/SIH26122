import React from 'react';
import { ErrorState } from '@/components/ui/error-state';

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** Short name of the area that failed, shown in the fallback (e.g. "Evidence panel"). */
  label?: string;
  /** Changing this value clears a caught error (e.g. pass the current pathname or event id). */
  resetKey?: unknown;
}

interface ErrorBoundaryState {
  error: Error | null;
}

/**
 * Contains render-time crashes to the subtree it wraps. Without one, a single
 * uncaught exception in any component unmounts the whole React tree and the
 * user sees a blank page.
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error(`[ErrorBoundary${this.props.label ? `: ${this.props.label}` : ''}]`, error, info.componentStack);
  }

  componentDidUpdate(prev: ErrorBoundaryProps) {
    if (this.state.error && prev.resetKey !== this.props.resetKey) {
      this.setState({ error: null });
    }
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <ErrorState
        variant="card"
        title={this.props.label ? `${this.props.label} failed to render` : 'Something went wrong'}
        message={this.state.error.message || 'An unexpected error occurred.'}
        onRetry={() => this.setState({ error: null })}
        className="my-6"
      />
    );
  }
}
