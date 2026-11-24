import Link from "next/link";
import { Analyzer } from "@/components/analyzer";
import { ServiceStatus } from "@/components/service-status";

export default function Home() {
  return (
    <main className="min-h-screen bg-[#f7f5ef] text-[#191a16]">
      <div className="mx-auto flex min-h-screen w-full max-w-6xl flex-col px-6 py-7 md:px-10">
        <header className="flex items-center justify-between border-b border-stone-300 pb-5">
          <Link className="text-xl font-semibold tracking-tight" href="/">vidora<span className="text-emerald-700">.</span></Link>
          <ServiceStatus />
        </header>
        <section className="flex-1 py-12 md:py-16">
          <p className="mb-5 text-xs font-semibold uppercase tracking-[0.22em] text-emerald-800">Your video, understood</p>
          <h1 className="max-w-3xl text-4xl font-semibold leading-[1.05] tracking-[-0.04em] md:text-6xl">Turn long videos into clear ideas.</h1>
          <p className="mb-10 mt-5 max-w-xl text-lg leading-8 text-stone-600">Paste a YouTube link. Vidora transcribes it in English and writes the summary, action items, decisions and open questions. Your analyses stay on this device.</p>
          <Analyzer />
        </section>
        <footer className="border-t border-stone-300 pt-5 text-xs text-stone-500">Built for focused listening.</footer>
      </div>
    </main>
  );
}
