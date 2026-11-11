/** Kropka w kolorze kategorii obok jej nazwy: identyfikacja, a nie jedyny nośnik informacji. */
export function ColorDot({ color }: { color: string | null }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-3 shrink-0 rounded-full ring-1 ring-slate-300"
      style={{ backgroundColor: color ?? 'transparent' }}
    />
  )
}
