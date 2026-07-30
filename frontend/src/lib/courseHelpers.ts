import type { Activity, Course, Module } from '../types/course';

export interface ActivityLocation {
  course: Course;
  module: Module;
  activity: Activity;
  indexInModule: number;
}

/** The single in-progress activity a learner should resume, if any. */
export function findCurrentActivity(course: Course): ActivityLocation | undefined {
  const module = course.modules.find((m) => m.status === 'in_progress');
  if (!module) return undefined;

  const indexInModule = module.activities.findIndex((a) => a.status === 'available');
  if (indexInModule === -1) return undefined;

  return { course, module, activity: module.activities[indexInModule], indexInModule };
}

/** The activity right after the current one, for "up next" previews. */
export function findUpNext(course: Course): ActivityLocation | undefined {
  const current = findCurrentActivity(course);
  if (!current) return undefined;

  const nextIndex = current.indexInModule + 1;
  const nextActivity = current.module.activities[nextIndex];
  if (!nextActivity) return undefined;

  return { course, module: current.module, activity: nextActivity, indexInModule: nextIndex };
}

export function activityPath(courseId: string, moduleId: string, activityId: string): string {
  return `/courses/${courseId}/modules/${moduleId}/activities/${activityId}`;
}
