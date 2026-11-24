"use client";

import { useEffect, useRef, useState } from "react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { type ChatTurn, askQuestion, getChat } from "@/lib/api";

export function Chat({ analysisId }: { analysisId: string }) {
  const [turns, setTurns] = useState<ChatTurn[] | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [question, setQuestion] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [askError, setAskError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let cancelled = false;
    getChat(analysisId)
      .then((loaded) => !cancelled && setTurns(loaded))
      .catch((error) => !cancelled && setLoadError(error instanceof Error ? error.message : "Could not load the chat."));
    return () => {
      cancelled = true;
    };
  }, [analysisId]);

  useEffect(() => {
    endRef.current?.scrollIntoView?.({ block: "nearest" });
  }, [turns, pending]);

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    const text = question.trim();
    if (!text || pending) return;
    setAskError(null);
    setPending(text);
    try {
      const turn = await askQuestion(analysisId, text);
      setTurns((current) => [...(current ?? []), turn]);
      setQuestion("");
    } catch (error) {
      setAskError(error instanceof Error ? error.message : "Could not get an answer.");
    } finally {
      setPending(null);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Ask about this video</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {loadError && (
          <Alert variant="destructive" role="alert">
            <AlertTitle>Could not load the chat</AlertTitle>
            <AlertDescription>{loadError}</AlertDescription>
          </Alert>
        )}
        {turns === null && !loadError && <Skeleton className="h-16 w-full" />}
        {turns?.length === 0 && !pending && (
          <p className="text-sm text-stone-500">Ask a question and Vidora answers from the transcript.</p>
        )}
        <ol className="space-y-4" aria-label="Chat history">
          {turns?.map((turn) => (
            <li key={turn.id} className="space-y-2 text-sm">
              <p className="ml-auto w-fit max-w-[85%] rounded-xl bg-emerald-800 px-4 py-2 text-white">{turn.question}</p>
              <p className="w-fit max-w-[85%] whitespace-pre-wrap rounded-xl bg-stone-100 px-4 py-2 leading-6 text-stone-800">{turn.answer}</p>
            </li>
          ))}
          {pending && (
            <li className="space-y-2 text-sm" aria-live="polite">
              <p className="ml-auto w-fit max-w-[85%] rounded-xl bg-emerald-800 px-4 py-2 text-white">{pending}</p>
              <p className="w-fit rounded-xl bg-stone-100 px-4 py-2 text-stone-500">Thinking...</p>
            </li>
          )}
        </ol>
        <div ref={endRef} />
        {askError && (
          <Alert variant="destructive" role="alert">
            <AlertTitle>No answer</AlertTitle>
            <AlertDescription>{askError}</AlertDescription>
          </Alert>
        )}
        <form onSubmit={onSubmit} className="flex flex-col gap-3 sm:flex-row" noValidate>
          <Input
            aria-label="Your question"
            placeholder="What did they decide about...?"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            disabled={!!pending || !!loadError}
            className="h-11 flex-1 bg-white"
          />
          <Button
            type="submit"
            size="lg"
            disabled={!!pending || !!loadError || !question.trim()}
            className="h-11 bg-emerald-800 px-6 hover:bg-emerald-900"
          >
            {pending ? "Asking..." : "Ask"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
