export const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export const API_ROUTES = {
  analyze: `${BACKEND_URL}/analyze`,
  resume: (threadId: string) => `${BACKEND_URL}/resume/${threadId}`,
  status: (threadId: string) => `${BACKEND_URL}/status/${threadId}`,
  health: `${BACKEND_URL}/health`,
};
