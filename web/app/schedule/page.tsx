"use client"

import { useEffect, useState } from "react"
import { getScheduledQueries, createSchedule, deleteSchedule } from "@/lib/api"
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Trash2, Plus } from "lucide-react"
import { useToast } from "@/components/hooks/use-toast"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"

export default function SchedulePage() {
  const { toast } = useToast()
  const [queries, setQueries] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [open, setOpen] = useState(false)

  // Form state
  const [name, setName] = useState("")
  const [queryText, setQueryText] = useState("")
  const [schedule, setSchedule] = useState("0 * * * *") // Default hourly

  function load() {
    setLoading(true)
    getScheduledQueries()
      .then(data => setQueries(data.queries))
      .catch(console.error)
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
  }, [])

  async function handleCreate() {
    try {
      await createSchedule(name, queryText, schedule, ["google"]) // Default engine
      toast({ description: "Schedule created" })
      setOpen(false)
      load()
      setName("")
      setQueryText("")
    } catch (e: any) {
      toast({ description: "Failed to create schedule", variant: "destructive" })
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Are you sure?")) return
    try {
      await deleteSchedule(id)
      toast({ description: "Schedule deleted" })
      load()
    } catch (e) {
      toast({ description: "Failed to delete", variant: "destructive" })
    }
  }

  if (loading) return <div className="p-8">Loading schedules...</div>

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold">Scheduled Queries</h1>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild>
            <Button><Plus className="w-4 h-4 mr-2" /> New Schedule</Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Scheduled Query</DialogTitle>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label>Name</Label>
                <Input value={name} onChange={e => setName(e.target.value)} placeholder="Daily Ransomware Check" />
              </div>
              <div className="space-y-2">
                <Label>Query</Label>
                <Input value={queryText} onChange={e => setQueryText(e.target.value)} placeholder="ransomware leak site" />
              </div>
              <div className="space-y-2">
                <Label>Cron Schedule</Label>
                <Input value={schedule} onChange={e => setSchedule(e.target.value)} placeholder="0 * * * *" />
                <p className="text-xs text-zinc-500">Format: minute hour day month day-of-week</p>
              </div>
              <Button onClick={handleCreate} className="w-full">Create</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4">
        {queries.map((q) => (
          <Card key={q.id} className="bg-zinc-900 border-zinc-800">
            <CardHeader className="pb-2">
              <div className="flex justify-between items-start">
                <div>
                  <CardTitle className="text-lg font-medium text-zinc-100">{q.name}</CardTitle>
                  <div className="text-sm text-zinc-500 mt-1">{q.query_text}</div>
                </div>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(q.id)} className="text-red-500 hover:text-red-400 hover:bg-red-950/30">
                  <Trash2 className="w-4 h-4" />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex gap-6 text-sm">
                <div>
                  <span className="text-zinc-500">Schedule:</span> <code className="bg-zinc-800 px-1 rounded">{q.schedule}</code>
                </div>
                <div>
                  <span className="text-zinc-500">Last Run:</span> {q.last_run_timestamp ? new Date(q.last_run_timestamp.replace("Z", "")).toLocaleString() : "Never"}
                </div>
                <div>
                  <span className="text-zinc-500">Status:</span> {q.is_active ? <span className="text-green-500">Active</span> : <span className="text-zinc-500">Inactive</span>}
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
        {queries.length === 0 && (
          <div className="text-zinc-500 text-center py-12">
            No scheduled queries. Create one to automate your OSINT.
          </div>
        )}
      </div>
    </div>
  )
}
