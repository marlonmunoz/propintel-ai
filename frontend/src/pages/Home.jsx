import { Link } from "react-router-dom";

export default function Home() {
    return (
        <main className="min-h-screen bg-slate-950 text-white">
            <section className="mx-auto flex min-h-screen max-w-6xl flex-col items-center justify-center px-6 text-center">
                <p className="mb-3 text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
                    PropIntel AI
                </p>
                <h1 className="max-w-4xl text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl">
                    AI-powered property valuation and investment analysis
                </h1>

                <p className="mt-6 max-w-2xl text-base text-slate-300 sm:text-lg">
                    Analyze residential properties with a product-ready AI workflow built
                    on PropIntel&apos;s v2 backend contract. 
                </p>

                <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
                    <Link
                        to="/analyze"
                        className="rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400"
                    >
                        Analyze Property
                    </Link>

                    <a  href="http://127.0.0.1:8000/docs"
                        target="_blank"
                        rel="norferrer"
                        className="rounded-xl border border-slate-700 px-6 py-3 font-semibold text-white transition hover:border-slate-500 hover:bg-slate-900"
                    >
                        View API Flow
                    </a>
                </div>
            </section>
        </main>
    )
}