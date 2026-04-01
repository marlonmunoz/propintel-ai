const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
const API_KEY = import.meta.env.VITE_API_KEY

const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
}

async function handleResponse(response) {
    if (!response.ok) {
        let message = 'Request failed'
        try {
            const data = await response.json()
            message = data.message || message
        } catch {
            // Keep fallback
        }
        throw new Error(message)
    }
    return await response.json()
}

export async function getProperties(params = {}) {
    const query = new URLSearchParams(params).toString()
    const url = `${API_BASE_URL}/properties/${query ? '?' + query : ''}`
    const response = await fetch(url, { headers })
    return handleResponse(response)
} 

export async function createProperty(payload) {
    const response = await fetch(`${API_BASE_URL}/properties/`, {
        method: 'POST',
        headers,
        body: JSON.stringify(payload),
    })
    return handleResponse(response)
}

export async function updateProperty(id, payload) {
    const response = await fetch(`${API_BASE_URL}/properties/${id}`, {
        method: 'PATCH',
        headers,
        body: JSON.stringify(payload),
    })
    return handleResponse(response)
}

export async function deleteProperty(id) {
    const response = await fetch(`${API_BASE_URL}/properties/${id}`,{
        method: 'DELETE',
        headers,
    })
    return handleResponse(response)
}