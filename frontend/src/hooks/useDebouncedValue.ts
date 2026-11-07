import { useEffect, useState } from 'react'

/** Wartość aktualizowana dopiero po przerwie w pisaniu: wyszukiwanie nie wysyła zapytania po każdej literze. */
export function useDebouncedValue<T>(value: T, delayMs = 300): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}
