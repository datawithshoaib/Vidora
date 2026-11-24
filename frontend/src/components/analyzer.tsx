"use client";

import { useEffect, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { type Analysis, type Job, getAnalysis, getJob, submitJob } from "@/lib/api";

const STEPS = [
  { key: "downloading", label: "Downloading audio" },
  { key: "transcribing", label: "Transcribing speech" },
  { key: "analyzing", label: "Writing notes" },
] as const;

const POLL_MS = 2000;

function Progress({ job }: { job: Job }) {
  const active = STEPS.findIndex((s) => s.key === job.step);
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-3">
          Analysis in progress
          <Badge variant="secondary">{job.status === "queued" ? "Queued" : "Processing"}</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <ol className="space-y-2 text-sm" aria-live="polite">
          <li className={job.status === "queued" ? "font-medium" : "text-stone-500"}>
            {job.status === "queued" ? "Waiting in the queue..." : "Queued"}
          </li>
          {STEPS.map((step, index) => (
            <li
              key={step.key}
              className={index === active ? "font-medium" : index < active ? "text-stone-500" : "text-stone-400"}
            >
              {index < active ? "Done: " : index === active ? "Now: " : ""}
              {step.label}
            </li>
          ))}
        </ol>
      </CardContent>
    </Card>
  );
}

function Section({ title, body }: { title: string; body: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-wrap text-sm leading-7 text-stone-700">{body}</p>
      </CardContent>
    </Card>
  );
}

function Result({ analysis }: { analysis: Analysis }) {
  return (
    <div className="space-y-4">
      <h2 className="text-3xl font-semibold tracking-tight">{analysis.title}</h2>
      <Section title="Summary" body={analysis.summary} />
      <div className="grid gap-4 md:grid-cols-3">
        <Section title="Action items" body={analysis.action_items} />
        <Section title="Key decisions" body={analysis.key_decisions} />
        <Section title="Open questions" body={analysis.open_questions} />
      </div>
      <Section title="Transcript" body={analysis.transcript} />
    </div>
  );
}

export function Analyzer() {
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [pollError, setPollError] = useState<string | null>(null);

  const jobId = job?.id;
  const active = job?.status === "queued" || job?.status === "processing";

  useEffect(() => {
    if (!jobId || !active) return;
    let cancelled = false;
    const timer = window.setInterval(async () => {
      try {
        const next = await getJob(jobId);
        if (cancelled) return;
        setPollError(null);
        setJob(next);
        if (next.status === "completed" && next.analysis_id) {
          setAnalysis(await getAnalysis(next.analysis_id));
        }
      } catch (error) {
        if (!cancelled) setPollError(error instanceof Error ? error.message : "Lost contact with the API.");
      }
    }, POLL_MS);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [jobId, active]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setFormError(null);
    setPollError(null);
    setAnalysis(null);
    setJob(null);
    setSubmitting(true);
    try {
      setJob(await submitJob(url.trim()));
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Could not start the analysis.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-8">
      <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row" noValidate>
        <Input
          aria-label="YouTube URL"
          placeholder="https://www.youtube.com/watch?v=..."
          value={url}
          onChange={(event) => setUrl(event.target.value)}
          aria-invalid={formError ? true : undefined}
          className="h-11 flex-1 bg-white"
        />
        <Button type="submit" size="lg" disabled={submitting || active} className="h-11 bg-emerald-800 px-6 hover:bg-emerald-900">
          {submitting ? "Starting..." : "Analyze video"}
        </Button>
      </form>

      {formError && (
        <Alert variant="destructive" role="alert">
          <AlertTitle>That link did not work</AlertTitle>
          <AlertDescription>{formError}</AlertDescription>
        </Alert>
      )}
      {pollError && (
        <Alert role="status">
          <AlertTitle>Connection problem</AlertTitle>
          <AlertDescription>{pollError} Still trying.</AlertDescription>
        </Alert>
      )}
      {!job && !formError && (
        <p className="text-sm text-stone-500">Paste a YouTube link to get a transcript, summary and key points.</p>
      )}
      {job && active && <Progress job={job} />}
      {job?.status === "failed" && (
        <Alert variant="destructive" role="alert">
          <AlertTitle>Analysis failed</AlertTitle>
          <AlertDescription>{job.error ?? "Something went wrong."} Check the link and try again.</AlertDescription>
        </Alert>
      )}
      {job?.status === "completed" && !analysis && <p className="text-sm text-stone-500">Loading results...</p>}
      {analysis && <Result analysis={analysis} />}
    </div>
  );
}
