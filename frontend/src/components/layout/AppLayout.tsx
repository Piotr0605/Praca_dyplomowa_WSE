import { NavLink, Outlet } from 'react-router'
import { useAuth } from '../../hooks/useAuth'

const NAV = [
  { to: '/transactions', label: 'Transakcje' },
  { to: '/categories', label: 'Kategorie' },
  { to: '/import', label: 'Import wyciągu' },
]

export function AppLayout() {
  const { user, logout } = useAuth()

  return (
    <div className="flex min-h-screen bg-slate-50">
      <aside className="w-56 shrink-0 border-r border-slate-200 bg-white p-4">
        <p className="mb-6 text-sm font-semibold text-slate-900">Asystent finansów</p>
        <nav aria-label="Menu główne" className="flex flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-md px-3 py-2 text-sm ${isActive ? 'bg-emerald-50 font-medium text-emerald-800' : 'text-slate-700 hover:bg-slate-100'}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-end gap-4 border-b border-slate-200 bg-white px-6 py-3">
          <span className="text-sm text-slate-600">{user?.email}</span>
          <button
            type="button"
            onClick={() => logout()}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-100"
          >
            Wyloguj
          </button>
        </header>
        <main className="p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
