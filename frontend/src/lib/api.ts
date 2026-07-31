import type { Course, InterviewStep, UserSettings, UserSettingsPatch } from '../types/course';

const API_BASE_URL = 'http://localhost:5000/api';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  });
  if (!response.ok) {
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

export function startCourse(message: string): Promise<InterviewStep> {
  return request<InterviewStep>('/courses', {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function submitInterviewAnswer(courseId: string, answer: string): Promise<InterviewStep> {
  return request<InterviewStep>(`/courses/${courseId}/interview-messages`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
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
