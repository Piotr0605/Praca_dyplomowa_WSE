import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { RequireAuth } from './components/RequireAuth'
import { AppLayout } from './components/layout/AppLayout'
import { AuthProvider } from './context/AuthProvider'
import { AuthPage } from './pages/AuthPage'
import { ImportPage } from './pages/ImportPage'
import { TransactionsPage } from './pages/TransactionsPage'

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          <Routes>
            <Route path="/login" element={<AuthPage mode="login" />} />
            <Route path="/register" element={<AuthPage mode="register" />} />
            <Route element={<RequireAuth />}>
              <Route element={<AppLayout />}>
                <Route path="/transactions" element={<TransactionsPage />} />
                <Route path="/import" element={<ImportPage />} />
              </Route>
            </Route>
            <Route path="*" element={<Navigate to="/transactions" replace />} />
          </Routes>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
