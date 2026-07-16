import Button from './Button'

export default function ErrorState({ title = 'Something went wrong', message, onRetry }) {
  return (
    <div className="px-6 py-12 text-center" role="alert">
      <h3 className="text-sm font-semibold text-red-700">{title}</h3>
      {message && <p className="mx-auto mt-1 max-w-md text-sm text-slate-600">{message}</p>}
      {onRetry && (
        <div className="mt-4 flex justify-center">
          <Button variant="secondary" onClick={onRetry}>
            Try again
          </Button>
        </div>
      )}
    </div>
  )
}
