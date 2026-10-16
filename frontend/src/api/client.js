const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

export function getAuthToken() {
  return localStorage.getItem('newtonite_token');
}

export function setAuthToken(token) {
  if (token) {
    localStorage.setItem('newtonite_token', token);
  } else {
    localStorage.removeItem('newtonite_token');
  }
}

export function getStoredUser() {
  const u = localStorage.getItem('newtonite_user');
  try {
    return u ? JSON.parse(u) : null;
  } catch {
    return null;
  }
}

export function setStoredUser(user) {
  if (user) {
    localStorage.setItem('newtonite_user', JSON.stringify(user));
  } else {
    localStorage.removeItem('newtonite_user');
  }
}

export async function apiRequest(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Auto-generate Idempotency-Key for POST/PATCH if not explicitly provided
  if (['POST', 'PATCH'].includes(options.method?.toUpperCase()) && !headers['Idempotency-Key']) {
    headers['Idempotency-Key'] = `idem-${crypto.randomUUID()}`;
  }

  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers,
  });

  const isReplay = response.headers.get('Idempotent-Replay') === 'true';

  let data = null;
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    data = await response.json();
  } else {
    data = await response.text();
  }

  if (!response.ok) {
    const error = new Error(
      (typeof data === 'object' && data?.detail)
        ? (typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail))
        : (typeof data === 'string' ? data : `Request failed with status ${response.status}`)
    );
    error.status = response.status;
    error.data = data;
    throw error;
  }

  return { data, isReplay, status: response.status };
}

// Authentication API
export async function login(email, password) {
  const { data } = await apiRequest('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  setAuthToken(data.access_token);
  const me = await getMe();
  setStoredUser(me);
  return { token: data.access_token, user: me };
}

export async function getMe() {
  const { data } = await apiRequest('/auth/me');
  return data;
}

export async function getDemoUsers() {
  const { data } = await apiRequest('/auth/demo-users');
  return data;
}

// Teams API
export async function getTeams() {
  const { data } = await apiRequest('/teams');
  return data;
}

// Work Items API
export async function getItems(params = {}) {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') {
      query.append(k, v);
    }
  });
  const qs = query.toString() ? `?${query.toString()}` : '';
  const { data } = await apiRequest(`/items${qs}`);
  return data;
}

export async function getItem(id) {
  const { data } = await apiRequest(`/items/${id}`);
  return data;
}

export async function createItem(itemData, customIdempotencyKey = null) {
  const headers = {};
  if (customIdempotencyKey) {
    headers['Idempotency-Key'] = customIdempotencyKey;
  }
  const { data, isReplay } = await apiRequest('/items', {
    method: 'POST',
    headers,
    body: JSON.stringify(itemData),
  });
  return { item: data, isReplay };
}

export async function updateItem(id, updateData) {
  const { data } = await apiRequest(`/items/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(updateData),
  });
  return data;
}

export async function claimItem(id, customIdempotencyKey = null) {
  const headers = {};
  if (customIdempotencyKey) {
    headers['Idempotency-Key'] = customIdempotencyKey;
  }
  const { data, isReplay } = await apiRequest(`/items/${id}/claim`, {
    method: 'POST',
    headers,
  });
  return { item: data, isReplay };
}

export async function transitionItem(id, transitionData) {
  const { data } = await apiRequest(`/items/${id}/transition`, {
    method: 'POST',
    body: JSON.stringify(transitionData),
  });
  return data;
}

export async function addComment(id, content) {
  const { data } = await apiRequest(`/items/${id}/comments`, {
    method: 'POST',
    body: JSON.stringify({ content }),
  });
  return data;
}

export async function getItemActivity(id) {
  const { data } = await apiRequest(`/items/${id}/activity`);
  return data;
}
