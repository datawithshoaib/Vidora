"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import type { HistoryItem } from "@/lib/api";

const STATUS_LABEL: Record<HistoryItem["status"], string> = {
  queued: "Queued",
  processing: "Processing",
  completed: "Completed",
  failed: "Failed",
};

function itemName(item: HistoryItem) {
  return item.title ?? item.source;
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export function History({
  items,
  loading,
  error,
  selectedId,
  onSelect,
  onDelete,
}: {
  items: HistoryItem[] | null;
  loading: boolean;
  error: string | null;
  selectedId: string | undefined;
  onSelect: (item: HistoryItem) => void;
  onDelete: (item: HistoryItem) => Promise<void>;
}) {
  return (
    <aside aria-label="History" className="space-y-3">
      <h2 className="text-xs font-semibold uppercase tracking-[0.18em] text-stone-500">History</h2>
      {error && (
        <p role="status" className="text-sm text-red-700">
          {error}
        </p>
      )}
      {loading && items === null && (
        <div className="space-y-2" aria-label="Loading history">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
        </div>
      )}
      {items !== null && items.length === 0 && (
        <p className="text-sm text-stone-500">No analyses yet. Finished and failed jobs will appear here.</p>
      )}
      {items !== null && items.length > 0 && (
        <ul className="space-y-2">
          {items.map((item) => {
            const active = item.status === "queued" || item.status === "processing";
            return (
              <li
                key={item.id}
                className={`flex items-start gap-1 rounded-lg border bg-white p-2 ${
                  item.id === selectedId ? "border-emerald-700" : "border-stone-200"
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelect(item)}
                  className="min-w-0 flex-1 rounded-md p-1 text-left hover:bg-stone-50"
                >
                  <span className="block truncate text-sm font-medium">{itemName(item)}</span>
                  <span className="mt-1 flex items-center gap-2 text-xs text-stone-500">
                    <Badge variant={item.status === "failed" ? "destructive" : "secondary"}>
                      {STATUS_LABEL[item.status]}
                    </Badge>
                    {formatDate(item.created_at)}
                  </span>
                </button>
                <AlertDialog>
                  <AlertDialogTrigger
                    disabled={active}
                    title={active ? "Wait for the analysis to finish before deleting" : undefined}
                    aria-label={`Delete ${itemName(item)}`}
                    render={<Button variant="ghost" size="sm" />}
                  >
                    Delete
                  </AlertDialogTrigger>
                  <AlertDialogContent>
                    <AlertDialogHeader>
                      <AlertDialogTitle>Delete this analysis?</AlertDialogTitle>
                      <AlertDialogDescription>
                        &ldquo;{itemName(item)}&rdquo; and its transcript and notes will be removed from this
                        device. This cannot be undone.
                      </AlertDialogDescription>
                    </AlertDialogHeader>
                    <AlertDialogFooter>
                      <AlertDialogCancel>Cancel</AlertDialogCancel>
                      <AlertDialogAction onClick={() => void onDelete(item)}>Delete</AlertDialogAction>
                    </AlertDialogFooter>
                  </AlertDialogContent>
                </AlertDialog>
              </li>
            );
          })}
        </ul>
      )}
    </aside>
  );
}
