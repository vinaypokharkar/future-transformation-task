import { Component } from 'react'
import Button from './Button'

/**
 * Router-level boundary: keeps one bad render from blanking the whole app.
 * Class component because React has no hook equivalent for componentDidCatch.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('Unhandled render error:', error, info)
  }

  handleReset = () => {
    this.setState({ error: null })
  }

  render() {
    const { error } = this.state

    if (!error) return this.props.children

    return (
      <div className="flex min-h-full items-center justify-center p-6">
        <div className="w-full max-w-md rounded-lg border border-slate-200 bg-white p-6 text-center shadow-sm">
          <h1 className="text-base font-semibold text-slate-900">This page hit an error</h1>
          <p className="mt-2 text-sm text-slate-500">
            The rest of the app is still running. Try again, or head back to the dashboard.
          </p>
          <p className="mt-3 truncate rounded bg-slate-50 px-3 py-2 font-mono text-xs text-slate-500">
            {error.message}
          </p>
          <div className="mt-4 flex justify-center gap-2">
            <Button onClick={this.handleReset}>Try again</Button>
            <Button variant="secondary" onClick={() => window.location.assign('/')}>
              Go to dashboard
            </Button>
          </div>
        </div>
      </div>
    )
  }
}
