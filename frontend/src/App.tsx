import { HealthStatus } from './components/HealthStatus'

export default function App() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-6">
      <div className="w-full max-w-sm rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
        <h1 className="text-lg font-semibold text-slate-900">Asystent finansów osobistych</h1>
        <p className="mt-1 mb-4 text-sm text-slate-500">Stan systemu</p>
        <HealthStatus />
      </div>
    </main>
  )
}
