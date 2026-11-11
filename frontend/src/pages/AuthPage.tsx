import { type FormEvent, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { HealthStatus } from '../components/HealthStatus'
import { ErrorMessage, FormField, inputClass, primaryButton } from '../components/ui/FormField'
import { useAuth } from '../hooks/useAuth'

const MIN_PASSWORD_LENGTH = 12

/** Wspólna strona logowania i rejestracji. */
export function AuthPage({ mode }: { mode: 'login' | 'register' }) {
  const { user, login, register, notice } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const isLogin = mode === 'login'

  if (user) return <Navigate to="/dashboard" replace />

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError(null)
    setSending(true)
    try {
      await (isLogin ? login(email, password) : register(email, password))
      const from = (location.state as { from?: string } | null)?.from
      navigate(from ?? '/dashboard', { replace: true })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Nie udało się połączyć z serwerem')
    } finally {
      setSending(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h1 className="text-lg font-semibold text-slate-900">
          {isLogin ? 'Logowanie' : 'Rejestracja'}
        </h1>
        <p className="mt-1 mb-4 text-sm text-slate-500">Asystent finansów osobistych</p>
        {notice && isLogin && (
          <p role="status" className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-900">
            {notice}
          </p>
        )}
        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <FormField label="E-mail">
            <input
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className={inputClass}
            />
          </FormField>
          <FormField label="Hasło">
            <input
              type="password"
              autoComplete={isLogin ? 'current-password' : 'new-password'}
              required
              minLength={isLogin ? undefined : MIN_PASSWORD_LENGTH}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className={inputClass}
            />
          </FormField>
          {!isLogin && (
            <p className="text-xs text-slate-500">Co najmniej {MIN_PASSWORD_LENGTH} znaków.</p>
          )}
          <ErrorMessage message={error} />
          <button type="submit" disabled={sending} className={primaryButton}>
            {isLogin ? 'Zaloguj' : 'Załóż konto'}
          </button>
        </form>
        <p className="mt-4 text-sm text-slate-600">
          {isLogin ? 'Nie masz konta? ' : 'Masz już konto? '}
          <Link to={isLogin ? '/register' : '/login'} className="font-medium text-emerald-700">
            {isLogin ? 'Zarejestruj się' : 'Zaloguj się'}
          </Link>
        </p>
        <div className="mt-6 border-t border-slate-100 pt-2">
          <HealthStatus />
        </div>
      </div>
    </main>
  )
}
