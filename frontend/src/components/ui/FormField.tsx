import { type ReactElement, cloneElement, useId } from 'react'

export const inputClass =
  'w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:border-emerald-600 focus:outline-none focus:ring-1 focus:ring-emerald-600 disabled:bg-slate-100 disabled:text-slate-500'

export const primaryButton =
  'rounded-md bg-emerald-700 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-800 disabled:opacity-50'

export const secondaryButton =
  'rounded-md border border-slate-300 px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 disabled:opacity-50'

/**
 * Etykieta powiązana z polem przez `for`/`id`. Etykieta obejmująca pole <select> dodawała do jego
 * nazwy dostępnej treść wszystkich opcji, więc czytnik ekranu odczytywał całą listę jako nazwę pola.
 */
export function FormField({
  label,
  children,
}: {
  label: string
  children: ReactElement<{ id?: string }>
}) {
  const id = useId()
  return (
    <div className="flex flex-col gap-1 text-sm">
      <label htmlFor={id} className="font-medium text-slate-700">
        {label}
      </label>
      {cloneElement(children, { id })}
    </div>
  )
}

export function ErrorMessage({ message }: { message: string | null }) {
  if (!message) return null
  return (
    <p role="alert" className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-800">
      {message}
    </p>
  )
}
