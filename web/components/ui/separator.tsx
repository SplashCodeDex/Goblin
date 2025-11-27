export function Separator({ className = "" }: { className?: string }) {
  return <div className={["h-px w-full bg-white/10", className].join(" ")} />
}
