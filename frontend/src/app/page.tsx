import Link from "next/link";
import { Button } from "@/components/ui/button";
import { ServiceStatus } from "@/components/service-status";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f7f5ef] text-[#191a16]">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-7 md:px-10">
        <header className="flex items-center justify-between border-b border-stone-300 pb-5">
          <Link className="text-xl font-semibold tracking-tight" href="/">vidora<span className="text-emerald-700">.</span></Link>
          <ServiceStatus />
        </header>
        <section className="grid flex-1 items-center gap-12 py-16 md:grid-cols-[1.05fr_0.95fr] md:py-24">
          <div>
            <p className="mb-5 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-800">Your video, understood</p>
            <h1 className="max-w-2xl text-5xl font-semibold leading-[1.04] tracking-[-0.045em] md:text-7xl">Turn long videos into clear ideas.</h1>
            <p className="mt-7 max-w-lg text-lg leading-8 text-stone-600">Vidora turns lectures, meetings, and YouTube videos into transcripts and notes you can search and ask questions about.</p>
            <div className="mt-10 flex flex-wrap gap-3">
              <Button size="lg" className="rounded-full bg-emerald-800 px-6 hover:bg-emerald-900" disabled>Analysis workflow coming next</Button>
              <span className="self-center text-sm text-stone-500">Local-first · English transcription</span>
            </div>
          </div>
          <div className="rounded-3xl border border-stone-300 bg-[#eeece4] p-6 shadow-[0_24px_70px_-48px_rgba(20,33,24,0.5)] md:p-9">
            <div className="flex items-center justify-between border-b border-stone-300 pb-5">
              <div><p className="text-xs uppercase tracking-[0.16em] text-stone-500">A clearer way to catch up</p><p className="mt-2 text-xl font-semibold">One video. The essentials.</p></div>
              <div className="grid h-12 w-12 place-items-center rounded-2xl bg-emerald-800 text-xl text-white" aria-hidden="true">V</div>
            </div>
            <div className="space-y-3 py-6">
              {[["01", "Transcript", "Every key moment, in readable text"], ["02", "Summary", "The ideas worth remembering"], ["03", "Ask anything", "Find answers grounded in the video"]].map(([number, title, description]) => (
                <div key={number} className="flex gap-4 rounded-2xl bg-white/70 p-4">
                  <span className="pt-1 text-xs font-semibold text-emerald-800">{number}</span>
                  <div><p className="font-semibold">{title}</p><p className="mt-1 text-sm text-stone-500">{description}</p></div>
                </div>
              ))}
            </div>
            <p className="border-t border-stone-300 pt-5 text-xs leading-5 text-stone-500">Your analyses stay on this device. Connect the API to begin.</p>
          </div>
        </section>
        <footer className="border-t border-stone-300 pt-5 text-xs text-stone-500">Built for focused listening.</footer>
      </div>
    </main>
  );
}
