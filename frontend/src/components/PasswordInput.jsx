import { useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'

const inputClass =
  'w-full rounded-lg border border-slate-200 bg-slate-50 py-2.5 pl-3.5 pr-10 text-sm text-slate-900 placeholder-slate-400 transition focus:border-cyan-500 focus:outline-none focus:ring-2 focus:ring-cyan-500/20 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:placeholder-slate-500'

/**
 * Password field with show/hide toggle — same pattern as Login, Register, Profile.
 */
export default function PasswordInput({
  id,
  label,
  value,
  onChange,
  autoComplete,
  placeholder,
  required = false,
  className = '',
}) {
  const [visible, setVisible] = useState(false)

  return (
    <div>
      {label ? (
        <label
          htmlFor={id}
          className="mb-1.5 block text-sm font-medium text-slate-700 dark:text-slate-300"
        >
          {label}
        </label>
      ) : null}
      <div className="relative">
        <input
          id={id}
          type={visible ? 'text' : 'password'}
          required={required}
          autoComplete={autoComplete}
          value={value}
          onChange={onChange}
          placeholder={placeholder}
          className={`${inputClass} ${className}`.trim()}
        />
        <button
          type="button"
          onClick={() => setVisible((v) => !v)}
          className="absolute right-2 top-1/2 flex h-8 w-8 -translate-y-1/2 items-center justify-center rounded-md text-slate-500 transition hover:bg-slate-200/80 hover:text-slate-700 dark:text-slate-400 dark:hover:bg-slate-700/80 dark:hover:text-slate-200"
          aria-label={visible ? 'Hide password' : 'Show password'}
        >
          {visible ? <EyeOff className="h-4 w-4" aria-hidden /> : <Eye className="h-4 w-4" aria-hidden />}
        </button>
      </div>
    </div>
  )
}
