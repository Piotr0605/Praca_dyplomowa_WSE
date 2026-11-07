import { createContext } from 'react'
import type { User } from '../types/api'

export type AuthState = {
  user: User | null
  /** true, dopóki nie wiadomo, czy zapisany token jest jeszcze ważny. */
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: (reason?: string) => void
  /** Komunikat pokazywany na stronie logowania, np. o wygaśnięciu sesji. */
  notice: string | null
}

export const AuthContext = createContext<AuthState | null>(null)
