import type { Course, InterviewStep, UserSettings, UserSettingsPatch } from '../types/course';

const API_BASE_URL = 'http://localhost:5000/api';

/** A backend error with a specific, user-facing message (e.g. an unsupported document format). */
export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  // FormData bodies (file uploads) need the browser to set their own
  // multipart boundary header; a hardcoded JSON content-type would break them.
  const isFormData = init?.body instanceof FormData;
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...(isFormData ? {} : { headers: { 'Content-Type': 'application/json' } }),
    ...init,
  });
  if (!response.ok) {
    const body: { error?: string } | null = await response.json().catch(() => null);
    if (body?.error) {
      throw new ApiError(body.error);
    }
    throw new Error(`${init?.method ?? 'GET'} ${path} failed: ${response.status}`);
  }
  return response.json();
}

export function fetchCourses(): Promise<Course[]> {
  return request<Course[]>('/courses');
}

export function fetchSettings(): Promise<UserSettings> {
  return request<UserSettings>('/settings');
}

export function updateSettings(patch: UserSettingsPatch): Promise<UserSettings> {
  return request<UserSettings>('/settings', {
    method: 'PUT',
    body: JSON.stringify(patch),
  });
}

export function completeActivity(activityId: string): Promise<Course> {
  return request<Course>(`/activities/${activityId}/complete`, { method: 'POST' });
}

export function fetchCourse(courseId: string): Promise<Course> {
  return request<Course>(`/courses/${courseId}`);
}

export function deleteCourse(courseId: string): Promise<void> {
  return request<void>(`/courses/${courseId}`, { method: 'DELETE' });
}

export function startCourse(message: string, files: File[] = []): Promise<InterviewStep> {
  const formData = new FormData();
  formData.append('message', message);
  files.forEach((file) => formData.append('files', file));
  return request<InterviewStep>('/courses', {
    method: 'POST',
    body: formData,
  });
}

export function submitInterviewAnswer(
  courseId: string,
  answer: string,
  files: File[] = [],
): Promise<InterviewStep> {
  const formData = new FormData();
  formData.append('answer', answer);
  files.forEach((file) => formData.append('files', file));
  return request<InterviewStep>(`/courses/${courseId}/interview-messages`, {
    method: 'POST',
    body: formData,
  });
}

export function generateOutline(courseId: string): Promise<Course> {
  return request<Course>(`/courses/${courseId}/generate-outline`, { method: 'POST' });
}

export function submitOutlineFeedback(courseId: string, feedback: string): Promise<Course> {
  return request<Course>(`/courses/${courseId}/outline-feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  });
}

export function approveOutline(courseId: string): Promise<Course> {
  return request<Course>(`/courses/${courseId}/approve-outline`, { method: 'POST' });
}

export function generateModuleActivities(moduleId: string): Promise<Course> {
  return request<Course>(`/modules/${moduleId}/generate-activities`, { method: 'POST' });
}
