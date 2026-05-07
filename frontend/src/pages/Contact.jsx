import { useRef, useState } from 'react'
import { Briefcase, CheckCircle, LifeBuoy, Loader2, Send } from 'lucide-react'
import Navbar from '../components/Navbar'
import Footer from '../components/Footer'
import { sendContactMessage } from '../services/contactApi'

const TOPICS = [
  {
    value: 'support',
    label: 'Customer support',
    description:
      'Account help, billing questions, bug reports, or anything that isn\u2019t working as expected.',
    Icon: LifeBuoy,
    iconBg: 'bg-cyan-500/15',
    iconColor: 'text-cyan-600 dark:text-cyan-400',
  },
  {
    value: 'partnerships',
    label: 'Press, partnerships \u0026 investors',
    description:
      'Media inquiries, partnership opportunities, or investor outreach — reach the founder directly.',
    Icon: Briefcase,
    iconBg: 'bg-violet-500/15',
    iconColor: 'text-violet-600 dark:text-violet-400',
  },
]

const INITIAL_FORM = { name: '', email: '', topic: 'support', message: '' }

export default function Contact() {
  const [form, setForm] = useState(INITIAL_FORM)
  const [status, setStatus] = useState('idle') // 'idle' | 'loading' | 'success' | 'error'
  const [errorMsg, setErrorMsg] = useState('')
  const formRef = useRef(null)

  function handleTopicCard(value) {
    setForm((prev) => ({ ...prev, topic: value }))
    formRef.current?.scrollIntoView?.({ behavior: 'smooth', block: 'start' })
  }

  function handleChange(e) {
    const { name, value } = e.target
    setForm((prev) => ({ ...prev, [name]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setStatus('loading')
    setErrorMsg('')
    try {
      await sendContactMessage(form)
      setStatus('success')
      setForm(INITIAL_FORM)
    } catch (err) {
      setStatus('error')
      setErrorMsg(err.message || 'Something went wrong. Please try again.')
    }
  }

  const isLoading = status === 'loading'

  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-slate-950 dark:text-white">
      <Navbar />

      <main className="flex-1">
        <section className="mx-auto max-w-3xl px-4 pb-16 pt-24 sm:px-6">
          {/* ── Header ─────────────────────────────────────────────────────── */}
          <p className="mb-2 text-xs font-semibold uppercase tracking-widest text-cyan-500">
            Contact
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-4xl">
            How can we help?
          </h1>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            We respond to most messages within one business day. Pick the right topic below so we
            can route your message faster.
          </p>

          {/* ── Topic cards (click to pre-select + scroll to form) ─────────── */}
          <div className="mt-10 grid gap-4 sm:grid-cols-2">
            {TOPICS.map((topic) => (
              <button
                key={topic.value}
                type="button"
                onClick={() => handleTopicCard(topic.value)}
                className={[
                  'flex flex-col rounded-2xl border p-6 text-left shadow-sm transition',
                  'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-500',
                  form.topic === topic.value
                    ? 'border-cyan-400 bg-cyan-50 dark:border-cyan-600 dark:bg-cyan-950/30'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:hover:border-slate-700 dark:hover:bg-slate-800/60',
                ].join(' ')}
                aria-pressed={form.topic === topic.value}
              >
                <div className="flex items-center gap-3">
                  <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${topic.iconBg}`}>
                    <topic.Icon className={`h-5 w-5 ${topic.iconColor}`} aria-hidden />
                  </div>
                  <span className="text-base font-semibold text-slate-900 dark:text-white">
                    {topic.label}
                  </span>
                </div>
                <p className="mt-3 text-sm text-slate-600 dark:text-slate-400">{topic.description}</p>
                <span className="mt-4 text-xs font-medium text-cyan-600 dark:text-cyan-400">
                  Send a message →
                </span>
              </button>
            ))}
          </div>

          {/* ── Contact form ────────────────────────────────────────────────── */}
          <div
            ref={formRef}
            className="mt-10 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900 sm:p-8"
          >
            {status === 'success' ? (
              <SuccessBanner onReset={() => setStatus('idle')} />
            ) : (
              <form onSubmit={handleSubmit} noValidate>
                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">
                  Send us a message
                </h2>
                <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
                  All fields are required.
                </p>

                <div className="mt-6 grid gap-5 sm:grid-cols-2">
                  {/* Name */}
                  <div>
                    <label
                      htmlFor="name"
                      className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
                    >
                      Your name
                    </label>
                    <input
                      id="name"
                      name="name"
                      type="text"
                      autoComplete="name"
                      required
                      maxLength={100}
                      value={form.name}
                      onChange={handleChange}
                      disabled={isLoading}
                      placeholder="Jane Smith"
                      className="block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500 dark:focus:border-cyan-400"
                    />
                  </div>

                  {/* Email */}
                  <div>
                    <label
                      htmlFor="email"
                      className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
                    >
                      Email address
                    </label>
                    <input
                      id="email"
                      name="email"
                      type="email"
                      autoComplete="email"
                      required
                      value={form.email}
                      onChange={handleChange}
                      disabled={isLoading}
                      placeholder="jane@example.com"
                      className="block w-full rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500 dark:focus:border-cyan-400"
                    />
                  </div>
                </div>

                {/* Topic radio */}
                <fieldset className="mt-5">
                  <legend className="mb-2 text-sm font-medium text-slate-700 dark:text-slate-300">
                    Topic
                  </legend>
                  <div className="flex flex-wrap gap-3">
                    {TOPICS.map(({ value, label }) => (
                      <label
                        key={value}
                        className={[
                          'flex cursor-pointer items-center gap-2 rounded-xl border px-4 py-2 text-sm font-medium transition',
                          form.topic === value
                            ? 'border-cyan-500 bg-cyan-50 text-cyan-700 dark:border-cyan-400 dark:bg-cyan-950/30 dark:text-cyan-300'
                            : 'border-slate-300 bg-white text-slate-700 hover:border-slate-400 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-300 dark:hover:border-slate-600',
                        ].join(' ')}
                      >
                        <input
                          type="radio"
                          name="topic"
                          value={value}
                          checked={form.topic === value}
                          onChange={handleChange}
                          disabled={isLoading}
                          className="sr-only"
                        />
                        {label}
                      </label>
                    ))}
                  </div>
                </fieldset>

                {/* Message */}
                <div className="mt-5">
                  <label
                    htmlFor="message"
                    className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
                  >
                    Message
                  </label>
                  <textarea
                    id="message"
                    name="message"
                    rows={5}
                    required
                    minLength={10}
                    maxLength={3000}
                    value={form.message}
                    onChange={handleChange}
                    disabled={isLoading}
                    placeholder="Describe your issue or question in as much detail as you can…"
                    className="block w-full resize-y rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm text-slate-900 placeholder-slate-400 shadow-sm transition focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/30 disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500 dark:focus:border-cyan-400"
                  />
                  <p className="mt-1 text-right text-xs text-slate-400">
                    {form.message.length} / 3 000
                  </p>
                </div>

                {/* Error banner */}
                {status === 'error' && (
                  <div
                    role="alert"
                    className="mt-4 rounded-xl bg-rose-50 px-4 py-3 text-sm text-rose-700 dark:bg-rose-900/20 dark:text-rose-400"
                  >
                    {errorMsg}
                  </div>
                )}

                {/* Submit */}
                <div className="mt-6">
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-cyan-600 px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-cyan-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-cyan-500 disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto"
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                        Sending…
                      </>
                    ) : (
                      <>
                        <Send className="h-4 w-4" aria-hidden />
                        Send message
                      </>
                    )}
                  </button>
                </div>
              </form>
            )}
          </div>

          <p className="mt-8 text-xs text-slate-500 dark:text-slate-500">
            PropIntel AI LLC — based in New York. We aim to reply within one business day.
          </p>
        </section>
      </main>

      <Footer />
    </div>
  )
}

function SuccessBanner({ onReset }) {
  return (
    <div className="flex flex-col items-center py-8 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-green-100 dark:bg-green-900/30">
        <CheckCircle className="h-7 w-7 text-green-600 dark:text-green-400" aria-hidden />
      </div>
      <h2 className="mt-4 text-xl font-semibold text-slate-900 dark:text-white">
        Message sent!
      </h2>
      <p className="mt-2 max-w-sm text-sm text-slate-600 dark:text-slate-400">
        Thanks for reaching out. We&rsquo;ll get back to you within one business day.
      </p>
      <button
        type="button"
        onClick={onReset}
        className="mt-6 text-sm font-medium text-cyan-600 underline underline-offset-2 hover:text-cyan-500 dark:text-cyan-400"
      >
        Send another message
      </button>
    </div>
  )
}
