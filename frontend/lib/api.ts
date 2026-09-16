import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  withCredentials: true, // send httpOnly cookie automatically
});

export default api;

// ── Auth ────────────────────────────────────────────────────────────────────
export const authApi = {
  login: (email: string, password: string) =>
    api.post("/auth/login", { email, password }),
  logout: () => api.post("/auth/logout"),
  me: () => api.get("/auth/me"),
};

// ── Candidates ───────────────────────────────────────────────────────────────
export const candidatesApi = {
  list: () => api.get("/candidates"),
  get: (id: string) => api.get(`/candidates/${id}`),
  create: (data: object) => api.post("/candidates", data),
  select: (id: string) => api.post(`/candidates/${id}/select`),
  convertToTrainee: (id: string, data: object) =>
    api.post(`/candidates/${id}/convert-to-trainee`, data),
};

// ── Documents ────────────────────────────────────────────────────────────────
export const documentsApi = {
  upload: (formData: FormData) =>
    api.post("/documents", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    }),
  download: (id: string) =>
    api.get(`/documents/${id}/download`, { responseType: "blob" }),
};

// ── Attendance ───────────────────────────────────────────────────────────────
export const attendanceApi = {
  list: (personId?: string) =>
    api.get("/attendance", { params: personId ? { person_id: personId } : {} }),
  create: (data: object) => api.post("/attendance", data),
};

// ── Leave ────────────────────────────────────────────────────────────────────
export const leaveApi = {
  list: (personId?: string) =>
    api.get("/leave", { params: personId ? { person_id: personId } : {} }),
  create: (data: object) => api.post("/leave", data),
  review: (id: string, data: object) => api.post(`/leave/${id}/review`, data),
};

// ── Evaluations ──────────────────────────────────────────────────────────────
export const evaluationsApi = {
  list: (personId?: string) =>
    api.get("/evaluations", { params: personId ? { person_id: personId } : {} }),
  create: (data: object) => api.post("/evaluations", data),
  submit: (id: string, data: object) => api.post(`/evaluations/${id}/submit`, data),
};

// ── Stipends ─────────────────────────────────────────────────────────────────
export const stipendsApi = {
  list: (personId?: string) =>
    api.get("/stipends", { params: personId ? { person_id: personId } : {} }),
  create: (data: object) => api.post("/stipends", data),
  approve: (id: string) => api.post(`/stipends/${id}/approve`),
  markPaid: (id: string, payment_date: string) =>
    api.post(`/stipends/${id}/mark-paid`, null, { params: { payment_date } }),
};
