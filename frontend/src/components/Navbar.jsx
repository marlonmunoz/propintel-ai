import { Link, useLocation } from "react-router-dom";

export default function Navbar() {
  const location = useLocation();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link to="/" className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-cyan-500">
            <span className="text-sm font-black text-slate-950">P</span>
          </div>
          <span className="text-lg font-bold tracking-tight text-white">
            PropIntel <span className="text-cyan-400">AI</span>
          </span>
        </Link>

        <nav className="flex items-center gap-6">
          <Link
            to="/"
            className={`text-sm font-medium transition ${
              location.pathname === "/"
                ? "text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Home
          </Link>
          <Link
            to="/analyze"
            className={`text-sm font-medium transition ${
              location.pathname === "/analyze"
                ? "text-white"
                : "text-slate-400 hover:text-white"
            }`}
          >
            Analyze
          </Link>
          <a
            href="http://127.0.0.1:8000/docs"
            target="_blank"
            rel="noreferrer"
            className="text-sm font-medium text-slate-400 transition hover:text-white"
          >
            API Docs
          </a>
        </nav>
      </div>
    </header>
  );
}
