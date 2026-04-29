import { apiFetch } from '../lib/apiClient'

export async function getProperties(params = {}) {
  const query = new URLSearchParams(params).toString()
  const path = `/properties/${query ? `?${query}` : ''}`
  return apiFetch(path, {
    method: 'GET',
    errorFallback: 'Failed to load properties',
  })
}

export async function createProperty(payload) {
  return apiFetch('/properties/', {
    method: 'POST',
    json: payload,
    errorFallback: 'Failed to create property',
  })
}

export async function updateProperty(id, payload) {
  return apiFetch(`/properties/${id}`, {
    method: 'PATCH',
    json: payload,
    errorFallback: 'Failed to update property',
  })
}

export async function deleteProperty(id) {
  return apiFetch(`/properties/${id}`, {
    method: 'DELETE',
    errorFallback: 'Failed to delete property',
  })
}
