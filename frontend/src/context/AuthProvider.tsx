import { useQueryClient } from '@tanstack/react-query'
import { type ReactNode, useCallback, useEffect, useMemo, useState } from 'react'
import { setUnauthorizedHandler } from '../api/client'
import { authApi } from '../api/endpoints'
import { tokenStore } from '../api/token'
import type { User } from '../types/api'
import { AuthContext, type AuthState } from './authContext'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(() => tokenStore.get() !== null)
  const [notice, setNotice] = useState<string | null>(null)

  const logout = useCallback(
    (reason?: string) => {
      tokenStore.clear()
      // Dane poprzedniego użytkownika nie mogą zostać w pamięci podręcznej przeglądarki.
      queryClient.clear()
      setUser(null)
      setNotice(reason ?? null)
    },
    [queryClient],
  )

  useEffect(() => {
    setUnauthorizedHandler(() => logout('Sesja wygasła. Zaloguj się ponownie.'))
  }, [logout])

  // Po odświeżeniu strony token jest w sessionStorage: sprawdzamy, czy nadal jest ważny.
  useEffect(() => {
    if (!tokenStore.get()) return
    authApi
      .me()
      .then(setUser)
      .catch(() => tokenStore.clear())
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    tokenStore.set(access_token)
    setUser(await authApi.me())
    setNotice(null)
  }, [])

  const register = useCallback(
    async (email: string, password: string) => {
      await authApi.register(email, password)
      await login(email, password)
    },
    [login],
  )

  const value = useMemo<AuthState>(
    () => ({ user, loading, login, register, logout, notice }),
    [user, loading, login, register, logout, notice],
  )
  return <AuthContext value={value}>{children}</AuthContext>
}
