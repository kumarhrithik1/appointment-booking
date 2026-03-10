// All API calls live here.
// BASE_URL comes from config.js — change it there for different environments.
// In development (BASE_URL = ''), CRA proxy forwards /api/* → http://127.0.0.1:8000.
// In production, set REACT_APP_API_URL=https://your-domain.com in .env
import config from './config';

async function request(path, options = {}) {
  const hasBody = options.body !== undefined;

  const headers = {
    ...(hasBody && { 'Content-Type': 'application/json' }),
    ...(options.headers || {})
  };

  const res = await fetch(`${config.BASE_URL}/api${path}`, {
    ...options,
    headers
  });

  let data = null;

  try {
    data = await res.json();
  } catch {
    data = null;
  }

  if (!res.ok) {
    throw new Error(data?.error || `Request failed (${res.status})`);
  }

  return data;
}

export const api = {
  getSlots() {
    return request('/slots?available=true');
  },

  getAppointments() {
    return request('/appointments?include_cancelled=false');
  },

  bookAppointment(slotId, name, email, note) {
    return request('/appointments', {
      method: 'POST',
      body: JSON.stringify({
        slot_id: slotId,
        customer_name: name,
        customer_email: email,
        note: note || undefined
      })
    });
  },

  cancelAppointment(id) {
    return request(`/appointments/${id}/cancel`, {
      method: 'POST'
    });
  }
};