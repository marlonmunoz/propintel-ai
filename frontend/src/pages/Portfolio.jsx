import { useState, useEffect } from 'react'
import { Plus, Trash2, Pencil, X, Check } from 'lucide-react'
import Navbar from '../components/Navbar'
import {
  getProperties,
  createProperty,
  updateProperty,
  deleteProperty,
} from '../services/propertiesApi'

const emptyForm = {
  address: '',
  zipcode: '',
  bedrooms: '',
  bathrooms: '',
  sqft: '',
  listing_price: '',
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0,
  }).format(value)
}

export default function Portfolio() {
  const [properties, setProperties] = useState([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formData, setFormData] = useState(emptyForm)
  const [formError, setFormError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [editData, setEditData] = useState({})
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)

  useEffect(() => {
    fetchProperties()
  }, [])

  async function fetchProperties() {
    setIsLoading(true)
    setError('')
    try {
      const data = await getProperties({ limit: 50 })
      setProperties(data)
    } catch (err) {
      setError(err.message || 'Failed to load properties.')
    } finally {
      setIsLoading(false)
    }
  }

  async function handleCreate(e) {
    e.preventDefault()
    setFormError('')
    setIsSubmitting(true)
    try {
      await createProperty({
        address: formData.address,
        zipcode: formData.zipcode,
        bedrooms: Number(formData.bedrooms),
        bathrooms: Number(formData.bathrooms),
        sqft: Number(formData.sqft),
        listing_price: Number(formData.listing_price),
      })
      setFormData(emptyForm)
      setShowForm(false)
      await fetchProperties()
    } catch (err) {
      setFormError(err.message || 'Failed to create property.')
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleDelete(id) {
    try {
      await deleteProperty(id)
      setProperties((prev) => prev.filter((p) => p.id !== id))
      setConfirmDeleteId(null)
    } catch (err) {
      setError(err.message || 'Failed to delete property.')
      setConfirmDeleteId(null)
    }
  }

  function startEdit(property) {
    setEditingId(property.id)
    setEditData({
      bedrooms: property.bedrooms,
      bathrooms: property.bathrooms,
      sqft: property.sqft,
      listing_price: property.listing_price,
    })
  }

  async function handleUpdate(id) {
    try {
      await updateProperty(id, {
        bedrooms: Number(editData.bedrooms),
        bathrooms: Number(editData.bathrooms),
        sqft: Number(editData.sqft),
        listing_price: Number(editData.listing_price),
      })
      setEditingId(null)
      await fetchProperties()
    } catch (err) {
      setError(err.message || 'Failed to update property.')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 text-white">
      <Navbar />

      <section className="mx-auto max-w-6xl px-6 pb-16 pt-24">

        {/* Header */}
        <div className="mb-8 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.2em] text-cyan-400">
              Portfolio
            </p>
            <h1 className="mt-1 text-3xl font-bold tracking-tight">
              Your Properties
            </h1>
          </div>
          <button
            onClick={() => setShowForm((v) => !v)}
            className="flex items-center gap-2 rounded-xl bg-cyan-500 px-5 py-2.5 font-semibold text-slate-950 transition hover:bg-cyan-400"
          >
            <Plus className="h-4 w-4" />
            Add Property
          </button>
        </div>

        {/* Add Property Form */}
        {showForm && (
          <form
            onSubmit={handleCreate}
            className="mb-8 rounded-2xl border border-slate-700 bg-slate-900 p-6"
          >
            <h2 className="mb-4 font-semibold text-white">New Property</h2>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {[
                { key: 'address', label: 'Address', type: 'text' },
                { key: 'zipcode', label: 'Zip Code', type: 'text' },
                { key: 'bedrooms', label: 'Bedrooms', type: 'number' },
                { key: 'bathrooms', label: 'Bathrooms', type: 'number' },
                { key: 'sqft', label: 'Sq Ft', type: 'number' },
                { key: 'listing_price', label: 'Listing Price', type: 'number' },
              ].map(({ key, label, type }) => (
                <div key={key}>
                  <label className="mb-1 block text-xs font-medium text-slate-400">
                    {label}
                  </label>
                  <input
                    type={type}
                    value={formData[key]}
                    onChange={(e) =>
                      setFormData((prev) => ({ ...prev, [key]: e.target.value }))
                    }
                    required
                    className="w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-2.5 text-white outline-none transition focus:border-cyan-400"
                  />
                </div>
              ))}
            </div>
            {formError && (
              <p className="mt-3 text-sm text-rose-400">{formError}</p>
            )}
            <div className="mt-4 flex gap-3">
              <button
                type="submit"
                disabled={isSubmitting}
                className="rounded-xl bg-cyan-500 px-5 py-2 font-semibold text-slate-950 transition hover:bg-cyan-400 disabled:opacity-50"
              >
                {isSubmitting ? 'Saving...' : 'Save Property'}
              </button>
              <button
                type="button"
                onClick={() => { setShowForm(false); setFormData(emptyForm); setFormError('') }}
                className="rounded-xl border border-slate-700 px-5 py-2 font-semibold text-white transition hover:bg-slate-800"
              >
                Cancel
              </button>
            </div>
          </form>
        )}

        {/* Error */}
        {error && (
          <div className="mb-6 rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm text-rose-400">
            {error}
          </div>
        )}

        {/* Loading */}
        {isLoading && (
          <div className="flex items-center justify-center py-20 text-slate-400">
            Loading properties...
          </div>
        )}

        {/* Empty state */}
        {!isLoading && !error && properties.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-center">
            <p className="text-lg font-semibold text-slate-300">No properties yet</p>
            <p className="mt-1 text-sm text-slate-500">
              Add your first property using the button above.
            </p>
          </div>
        )}

        {/* Property list */}
        {!isLoading && properties.length > 0 && (
          <div className="space-y-3">
            {properties.map((property) => (
              <div
                key={property.id}
                className="rounded-2xl border border-slate-800 bg-slate-900/60 p-5 transition hover:border-slate-600"
              >
                {editingId === property.id ? (
                  /* Edit mode */
                  <div className="flex flex-wrap items-end gap-4">
                    {[
                      { key: 'bedrooms', label: 'Beds' },
                      { key: 'bathrooms', label: 'Baths' },
                      { key: 'sqft', label: 'Sq Ft' },
                      { key: 'listing_price', label: 'Price' },
                    ].map(({ key, label }) => (
                      <div key={key} className="flex-1 min-w-[100px]">
                        <label className="mb-1 block text-xs text-slate-400">{label}</label>
                        <input
                          type="number"
                          value={editData[key]}
                          onChange={(e) =>
                            setEditData((prev) => ({ ...prev, [key]: e.target.value }))
                          }
                          className="w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-white outline-none focus:border-cyan-400"
                        />
                      </div>
                    ))}
                    <div className="flex gap-2">
                      <button
                        onClick={() => handleUpdate(property.id)}
                        className="flex items-center gap-1 rounded-xl bg-cyan-500 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-400"
                      >
                        <Check className="h-4 w-4" /> Save
                      </button>
                      <button
                        onClick={() => setEditingId(null)}
                        className="flex items-center gap-1 rounded-xl border border-slate-700 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
                      >
                        <X className="h-4 w-4" /> Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  /* View mode */
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div className="flex items-center gap-4">
                      <span className="flex h-7 min-w-[28px] flex-shrink-0 items-center justify-center rounded-lg bg-slate-800 px-1.5 text-xs font-bold text-slate-400">
                        {property.id}
                      </span>
                      <div>
                        <p className="font-semibold text-white">{property.address}</p>
                        <p className="text-sm text-slate-400">{property.zipcode}</p>
                      </div>
                    </div>
                    <div className="flex flex-wrap gap-6 text-sm text-slate-300">

                      <span>{property.bedrooms} bed</span>
                      <span>{property.bathrooms} bath</span>
                      <span>{property.sqft?.toLocaleString()} sqft</span>
                      <span className="font-semibold text-cyan-400">
                        {formatCurrency(property.listing_price)}
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      {confirmDeleteId === property.id ? (
                        <div className="flex items-center gap-2 rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-1.5">
                          <span className="text-sm text-rose-300">Delete?</span>
                          <button
                            onClick={() => handleDelete(property.id)}
                            className="text-sm font-semibold text-rose-400 transition hover:text-rose-300"
                          >
                            Yes
                          </button>
                          <span className="text-slate-600">·</span>
                          <button
                            onClick={() => setConfirmDeleteId(null)}
                            className="text-sm font-semibold text-slate-400 transition hover:text-white"
                          >
                            No
                          </button>
                        </div>
                      ) : (
                        <>
                          <button
                            onClick={() => startEdit(property)}
                            className="flex items-center gap-1 rounded-xl border border-slate-700 px-3 py-1.5 text-sm text-slate-300 transition hover:border-slate-500 hover:text-white"
                          >
                            <Pencil className="h-3.5 w-3.5" /> Edit
                          </button>
                          <button
                            onClick={() => setConfirmDeleteId(property.id)}
                            className="flex items-center gap-1 rounded-xl border border-rose-500/30 px-3 py-1.5 text-sm text-rose-400 transition hover:bg-rose-500/10"
                          >
                            <Trash2 className="h-3.5 w-3.5" /> Delete
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}
