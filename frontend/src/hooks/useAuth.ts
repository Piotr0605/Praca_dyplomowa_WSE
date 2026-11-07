import { useContext } from 'react'
import { AuthContext, type AuthState } from '../context/authContext'

export function useAuth(): AuthState {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error('useAuth wymaga AuthProvider')
  return auth
}
