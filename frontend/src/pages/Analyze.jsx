import { useState } from 'react'
import { Link } from 'react-router-dom'

const initialForm = {
  borough: '',
  neighborhood: '',
  building_class: '',
  year_built: '',
  gross_sqft: '',
  land_sqft: '',
  latitude: '',
  longitude: '',
  market_price: '',
}

export default function Analyze() {
  const [formData, setFormData] = useState(initialForm)

  function handleChange(event) {
    const { name, value } = event.target
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }))
  }

  function handleSubmit(event) {
    event.preventDefault()
    console.log('Form ready for API connection:', formData)
  }

  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="mx-auto max-w-6xl px-6 py-12">
        <div className="mb-10 flex items-center justify-between gap-4">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
              PropIntel AI
            </p>
            <h1 className="mt-3 text-3xl font-bold tracking-tight sm:text-4xl">
              Property Analysis Workspace
            </h1>
            <p className="mt-3 max-w-2xl text-slate-300">
              Enter property details below to prepare an analysis request for
              the
              <span className="mx-1 font-semibold text-white">
                /analyze-property-v2
              </span>
              endpoint.
            </p>
          </div>

          <Link
            to="/"
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-white transition hover:border-slate-500 hover:bg-slate-900"
          >
            Back Home
          </Link>
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Analysis Form</h2>
            <p className="mt-2 text-sm text-slate-400">
              Fill in the property inputs required by the v2 analysis contract.
            </p>

            <form onSubmit={handleSubmit} className="mt-6 space-y-6">
              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                  Property Basics
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="borough"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Borough
                    </label>
                    <input
                      id="borough"
                      name="borough"
                      type="text"
                      value={formData.borough}
                      onChange={handleChange}
                      placeholder="Brooklyn"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="neighborhood"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Neighborhood
                    </label>
                    <input
                      id="neighborhood"
                      name="neighborhood"
                      type="text"
                      value={formData.neighborhood}
                      onChange={handleChange}
                      placeholder="Park Slope"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div className="sm:col-span-2">
                    <label
                      htmlFor="building_class"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Building Class
                    </label>
                    <input
                      id="building_class"
                      name="building_class"
                      type="text"
                      value={formData.building_class}
                      onChange={handleChange}
                      placeholder="02 TWO FAMILY DWELLINGS"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="year_built"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Year Built
                    </label>
                    <input
                      id="year_built"
                      name="year_built"
                      type="number"
                      value={formData.year_built}
                      onChange={handleChange}
                      placeholder="1925"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                  Size & Location
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="gross_sqft"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Gross Sqft
                    </label>
                    <input
                      id="gross_sqft"
                      name="gross_sqft"
                      type="number"
                      value={formData.gross_sqft}
                      onChange={handleChange}
                      placeholder="1800"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="land_sqft"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Land Sqft
                    </label>
                    <input
                      id="land_sqft"
                      name="land_sqft"
                      type="number"
                      value={formData.land_sqft}
                      onChange={handleChange}
                      placeholder="2000"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="latitude"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Latitude
                    </label>
                    <input
                      id="latitude"
                      name="latitude"
                      type="number"
                      step="any"
                      value={formData.latitude}
                      onChange={handleChange}
                      placeholder="40.6720"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>

                  <div>
                    <label
                      htmlFor="longitude"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Longitude
                    </label>
                    <input
                      id="longitude"
                      name="longitude"
                      type="number"
                      step="any"
                      value={formData.longitude}
                      onChange={handleChange}
                      placeholder="-73.9778"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
                  Pricing
                </h3>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <div>
                    <label
                      htmlFor="market_price"
                      className="mb-2 block text-sm font-medium text-slate-200"
                    >
                      Market Price
                    </label>
                    <input
                      id="market_price"
                      name="market_price"
                      type="number"
                      value={formData.market_price}
                      onChange={handleChange}
                      placeholder="1250000"
                      className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none transition placeholder:text-slate-500 focus:border-cyan-400"
                    />
                  </div>
                </div>
              </div>

              <button
                type="submit"
                className="inline-flex items-center justify-center rounded-xl bg-cyan-500 px-6 py-3 font-semibold text-slate-950 transition hover:bg-cyan-400"
              >
                Run Analysis
              </button>
            </form>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 shadow-sm">
            <h2 className="text-xl font-semibold">Analysis Results</h2>
            <p className="mt-2 text-sm text-slate-400">
              Next step: connect the form to the backend and render real
              valuation, investment score, drivers, and AI explanation here.
            </p>

            <div className="mt-6 rounded-xl border border-dashed border-slate-700 p-6 text-sm text-slate-500">
              Result cards powered by the v2 backend response will appear here
              after we connect the API.
            </div>
          </div>
        </div>
      </section>
    </main>
  )
}