type Artifact = { type: string; value: string; context?: string }
export function ArtifactsTable({ data }: { data: Artifact[] }) {
  if (!data?.length) return <div className="text-sm text-zinc-400">No artifacts extracted yet.</div>
  return (
    <div className="rounded-xl border border-white/10 bg-white/5 backdrop-blur-md p-4 space-y-2">
      {data.map((a, i) => (
        <div key={i} className="text-sm">
          <span className="text-zinc-400">{a.type}:</span> <span className="font-mono">{a.value}</span>
          {a.context && <span className="text-zinc-500"> — {a.context}</span>}
        </div>
      ))}
    </div>
  )
}
