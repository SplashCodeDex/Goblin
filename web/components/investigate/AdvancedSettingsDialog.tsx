"use client"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"

export function AdvancedSettingsDialog(props: {
  open: boolean
  onClose: () => void
  threads: number
  setThreads: (n: number) => void
  maxResults: number
  setMaxResults: (n: number) => void
  detailed?: boolean
  setDetailed?: (v: boolean) => void
  requestTimeout: number
  setRequestTimeout: (n: number) => void
  useCache: boolean
  setUseCache: (v: boolean) => void
  loadCachedOnly: boolean
  setLoadCachedOnly: (v: boolean) => void
  translate: boolean
  setTranslate: (v: boolean) => void
}) {
  const {
    open, onClose, threads, setThreads, maxResults, setMaxResults, detailed, setDetailed,
    requestTimeout, setRequestTimeout, useCache, setUseCache, loadCachedOnly, setLoadCachedOnly, translate, setTranslate
  } = props
  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Advanced settings</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="grid gap-2">
            <label className="text-sm">Threads (1-16)</label>
            <Input type="number" min={1} max={16} value={threads} onChange={e => setThreads(Number(e.target.value))} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm">Max results to process (cap)</label>
            <Input type="number" min={10} max={500} value={maxResults} onChange={e => setMaxResults(Number(e.target.value))} />
          </div>
          <div className="grid gap-2">
            <label className="text-sm">Request timeout (seconds)</label>
            <Input type="number" min={5} max={90} value={requestTimeout} onChange={e => setRequestTimeout(Number(e.target.value))} />
          </div>
          <div className="flex items-center gap-2">
            <input id="useCache" type="checkbox" checked={useCache} onChange={e => setUseCache(e.target.checked)} />
            <label htmlFor="useCache" className="text-sm">Use disk cache</label>
          </div>
          <div className="flex items-center gap-2">
            <input id="loadCachedOnly" type="checkbox" checked={loadCachedOnly} onChange={e => setLoadCachedOnly(e.target.checked)} />
            <label htmlFor="loadCachedOnly" className="text-sm">Load cached only (Offline mode)</label>
          </div>
          <div className="flex items-center gap-2">
            <input id="translate" type="checkbox" checked={translate} onChange={e => setTranslate(e.target.checked)} />
            <label htmlFor="translate" className="text-sm">Auto-translate non-English content</label>
          </div>
          <div className="flex items-center gap-2">
            <input id="detailed" type="checkbox" checked={!!detailed} onChange={e => setDetailed?.(e.target.checked)} />
            <label htmlFor="detailed" className="text-sm">Detailed per-URL progress (sequential)</label>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={onClose}>Close</Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}
