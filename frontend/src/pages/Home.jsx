import { Link } from "react-router-dom";
import { BarChart3, Brain, ShieldCheck } from "lucide-react";
import Navbar from "../components/Navbar";

const features = [
  {
    icon: BarChart3,
    title: "ML-Powered Valuation",
    description:
      "XGBoost models trained on real NYC sales data route to the best segment model for your property type — one family, multi-family, condo, co-op, or rental.",
  },
  {
    icon: Brain,
    title: "AI Investment Analysis",
    description:
      "Get a full investment breakdown: ROI estimate, valuation gap, deal label (Buy / Hold / Avoid), and an LLM-generated narrative explanation.",
  },
  {
    icon: ShieldCheck,
    title: "Production-Grade API",
    description:
      "Built on a hardened FastAPI backend with authentication, rate limiting, structured logging, and a consistent JSON contract.",
  },
];

export default function Home() {
  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />

      {/* Hero */}
      <section className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 pt-20 text-center">
        <p className="mb-3 text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
          PropIntel AI
        </p>
        <h1 className="max-w-4xl text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
          AI-powered property valuation and investment analysis
        </h1>
        <p className="mt-6 max-w-2xl text-base text-slate-300 sm:text-lg">
          Analyze NYC residential properties with a production-ready AI workflow.
          Get valuations, investment scores, and LLM-generated deal narratives in seconds.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/analyze"
            className="rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            Analyze Property
          </Link>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="rounded-xl border border-slate-700 px-6 py-3 font-semibold text-white transition hover:border-slate-500 hover:bg-slate-900"
          >
            View API Docs
          </a>
        </div>
      </section>

      {/* Features */}
      <section className="mx-auto max-w-6xl px-6 pb-24">
        <div className="grid gap-6 sm:grid-cols-3">
          {features.map(({ icon: Icon, title, description }) => (
            <div
              key={title}
              className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 transition hover:border-slate-600"
            >
              <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-cyan-500/10">
                <Icon className="h-5 w-5 text-cyan-400" />
              </div>
              <h3 className="mb-2 font-semibold text-white">{title}</h3>
              <p className="text-sm leading-relaxed text-slate-400">{description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
