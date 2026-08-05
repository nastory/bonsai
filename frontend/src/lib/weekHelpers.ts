import type { Course } from '../types/course';

/** Midnight (local time) of the Monday on or before the given date. */
export function startOfWeek(date: Date): Date {
  const result = new Date(date);
  result.setHours(0, 0, 0, 0);
  const daysSinceMonday = (result.getDay() + 6) % 7;
  result.setDate(result.getDate() - daysSinceMonday);
  return result;
}

/** How many activities, across every course, were completed on or after `since`. */
export function countActivitiesCompletedSince(courses: Course[], since: Date): number {
  let count = 0;
  for (const course of courses) {
    for (const module of course.modules) {
      for (const activity of module.activities) {
        if (activity.completedAt && new Date(activity.completedAt) >= since) count += 1;
      }
    }
  }
  return count;
}
