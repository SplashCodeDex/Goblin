"use client"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { Label } from "@/components/ui/label"

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
  minStars: number
  setMinStars: (n: number) => void
  minForks: number
  setMinForks: (n: number) => void
  includeCommits: boolean
  setIncludeCommits: (v: boolean) => void
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
            <Checkbox id="useCache" checked={useCache} onCheckedChange={(v)=> setUseCache(Boolean(v))} />
            <Label htmlFor="useCache" className="text-sm">Use disk cache</Label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="loadCachedOnly" checked={loadCachedOnly} onCheckedChange={(v)=> setLoadCachedOnly(Boolean(v))} />
            <Label htmlFor="loadCachedOnly" className="text-sm">Load cached only (Offline mode)</label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="translate" checked={translate} onCheckedChange={(v)=> setTranslate(Boolean(v))} />
            <Label htmlFor="translate" className="text-sm">Auto-translate non-English content</label>
          </div>
          <div className="flex items-center gap-2">
            <Checkbox id="detailed" checked={!!detailed} onCheckedChange={(v)=> setDetailed?.(Boolean(v))} />
            <Label htmlFor="detailed" className="text-sm">Detailed per-URL progress (sequential)</label>
          </div>
          <div className="grid gap-2">
            <label className="text-sm font-semibold">GitHub Filters</label>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-xs">Min Stars</label>
                <Input type="number" min={0} value={props.minStars} onChange={e => props.setMinStars(Number(e.target.value))} />
              </div>
              <div>
                <label className="text-xs">Min Forks</label>
                <Input type="number" min={0} value={props.minForks} onChange={e => props.setMinForks(Number(e.target.value))} />
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <Checkbox id="includeCommits" checked={props.includeCommits} onCheckedChange={(v)=> props.setIncludeCommits(Boolean(v))} />
              <Label htmlFor="includeCommits" className="text-sm">Search Commit History (Secrets)</label>
            </div>
          </div>
          <DialogFooter>
            <Button variant="secondary" onClick={onClose}>Close</Button>
          </DialogFooter>
        </div>
      </DialogContent>
    </Dialog>
  )
}
