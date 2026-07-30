import { createContext, useContext, useMemo, useState, type ReactNode } from 'react';
import type { Course, UserSettings } from '../types/course';
import { mockCourses } from '../data/mockCourses';
import { mockUser } from '../data/mockUser';

interface AppDataContextValue {
  courses: Course[];
  user: UserSettings;
  getCourse: (courseId: string) => Course | undefined;
  completeActivity: (courseId: string, moduleId: string, activityId: string) => void;
  updateUserSettings: (patch: Partial<UserSettings>) => void;
}

const AppDataContext = createContext<AppDataContextValue | undefined>(undefined);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [courses, setCourses] = useState<Course[]>(mockCourses);
  const [user, setUser] = useState<UserSettings>(mockUser);

  const getCourse = (courseId: string) => courses.find((c) => c.id === courseId);

  const completeActivity = (courseId: string, moduleId: string, activityId: string) => {
    setCourses((prev) =>
      prev.map((course) => {
        if (course.id !== courseId) return course;

        const moduleIndex = course.modules.findIndex((m) => m.id === moduleId);
        if (moduleIndex === -1) return course;

        const currentModule = course.modules[moduleIndex];
        const activityIndex = currentModule.activities.findIndex((a) => a.id === activityId);
        if (activityIndex === -1) return course;

        const activities = currentModule.activities.map((activity, i) => {
          if (i === activityIndex) return { ...activity, status: 'completed' as const };
          if (i === activityIndex + 1 && activity.status === 'locked') {
            return { ...activity, status: 'available' as const };
          }
          return activity;
        });

        const moduleCompleted = activities.every((a) => a.status === 'completed');
        const modules = course.modules.map((m, i) => {
          if (i === moduleIndex) {
            return { ...m, activities, status: moduleCompleted ? ('completed' as const) : m.status };
          }
          if (moduleCompleted && i === moduleIndex + 1 && m.status === 'locked') {
            return { ...m, status: 'in_progress' as const };
          }
          return m;
        });

        return { ...course, modules };
      }),
    );
  };

  const updateUserSettings = (patch: Partial<UserSettings>) => {
    setUser((prev) => ({ ...prev, ...patch }));
  };

  const value = useMemo(
    () => ({ courses, user, getCourse, completeActivity, updateUserSettings }),
    [courses, user],
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

export function useAppData(): AppDataContextValue {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error('useAppData must be used within an AppDataProvider');
  return ctx;
}
