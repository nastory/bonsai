import type {
  AMAMessage,
  Course,
  DirectionChangeInterviewStep,
  DirectionChangeProposal,
  FlashCardSet,
  InterviewStep,
  QuizSet,
  UserSettings,
  UserSettingsPatch,
} from '../types/course';

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

export function generateActivityFeedback(activityId: string, response: string): Promise<{ feedback: string }> {
  return request<{ feedback: string }>(`/activities/${activityId}/feedback`, {
    method: 'POST',
    body: JSON.stringify({ response }),
  });
}

export function submitDiscussionReply(
  activityId: string,
  message: string,
): Promise<{ done: boolean; message: string }> {
  return request<{ done: boolean; message: string }>(`/activities/${activityId}/discussion-messages`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function fetchCourse(courseId: string): Promise<Course> {
  return request<Course>(`/courses/${courseId}`);
}

export function deleteCourse(courseId: string): Promise<void> {
  return request<void>(`/courses/${courseId}`, { method: 'DELETE' });
}

export function startCourse(
  message: string,
  files: File[] = [],
  parentCourseId?: string,
  supplementWithWebSearch?: boolean,
): Promise<InterviewStep> {
  const formData = new FormData();
  formData.append('message', message);
  files.forEach((file) => formData.append('files', file));
  if (parentCourseId) formData.append('parentCourseId', parentCourseId);
  if (supplementWithWebSearch) formData.append('supplementWithWebSearch', 'true');
  return request<InterviewStep>('/courses', {
    method: 'POST',
    body: formData,
  });
}

export function submitInterviewAnswer(
  courseId: string,
  answer: string,
  files: File[] = [],
  supplementWithWebSearch?: boolean,
): Promise<InterviewStep> {
  const formData = new FormData();
  formData.append('answer', answer);
  files.forEach((file) => formData.append('files', file));
  if (supplementWithWebSearch) formData.append('supplementWithWebSearch', 'true');
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

export function startDirectionChange(moduleId: string, message: string): Promise<DirectionChangeInterviewStep> {
  return request<DirectionChangeInterviewStep>(`/modules/${moduleId}/direction-interview`, {
    method: 'POST',
    body: JSON.stringify({ message }),
  });
}

export function submitDirectionChangeAnswer(
  moduleId: string,
  answer: string,
): Promise<DirectionChangeInterviewStep> {
  return request<DirectionChangeInterviewStep>(`/modules/${moduleId}/direction-interview-messages`, {
    method: 'POST',
    body: JSON.stringify({ answer }),
  });
}

export function generateDirectionChangeOutline(moduleId: string): Promise<DirectionChangeProposal> {
  return request<DirectionChangeProposal>(`/modules/${moduleId}/direction-outline`, { method: 'POST' });
}

export function submitDirectionChangeFeedback(
  moduleId: string,
  feedback: string,
): Promise<DirectionChangeProposal> {
  return request<DirectionChangeProposal>(`/modules/${moduleId}/direction-outline-feedback`, {
    method: 'POST',
    body: JSON.stringify({ feedback }),
  });
}

export function approveDirectionChange(moduleId: string): Promise<Course> {
  return request<Course>(`/modules/${moduleId}/direction-outline-approve`, { method: 'POST' });
}

// Bypasses request(): it always parses JSON, but an export archive is a
// binary .zip download, not a JSON body.
export async function exportData(): Promise<Blob> {
  const response = await fetch(`${API_BASE_URL}/data/export`);
  if (!response.ok) {
    throw new Error(`GET /data/export failed: ${response.status}`);
  }
  return response.blob();
}

export function importData(file: File): Promise<void> {
  const formData = new FormData();
  formData.append('file', file);
  return request<void>('/data/import', { method: 'POST', body: formData });
}

export function generateFlashCards(moduleId: string): Promise<FlashCardSet> {
  return request<FlashCardSet>(`/modules/${moduleId}/flash-cards`, { method: 'POST' });
}

export function generateQuizSet(moduleId: string): Promise<QuizSet> {
  return request<QuizSet>(`/modules/${moduleId}/quiz-set`, { method: 'POST' });
}

export function askAMA(
  message: string,
  history: AMAMessage[],
): Promise<{ reply: string; courseIds: string[]; citations: AMAMessage['citations'] }> {
  return request(`/ama/messages`, {
    method: 'POST',
    body: JSON.stringify({ message, history }),
  });
}
