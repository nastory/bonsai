import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Course, UserSettings, UserSettingsPatch } from '../types/course';
import { fetchCourses, fetchSettings, updateSettings, completeActivity as apiCompleteActivity } from '../lib/api';

const DEFAULT_USER: UserSettings = {
  name: 'Learner',
  feedbackTone: 'encouraging',
  thumbnailGenerationEnabled: true,
  modelProvider: { tier: 'hosted', hasApiKey: false },
};

interface AppDataContextValue {
  courses: Course[];
  user: UserSettings;
  loading: boolean;
  getCourse: (courseId: string) => Course | undefined;
  completeActivity: (activityId: string) => void;
  updateUserSettings: (patch: UserSettingsPatch) => void;
  refreshCourses: () => Promise<void>;
}

const AppDataContext = createContext<AppDataContextValue | undefined>(undefined);

export function AppDataProvider({ children }: { children: ReactNode }) {
  const [courses, setCourses] = useState<Course[]>([]);
  const [user, setUser] = useState<UserSettings>(DEFAULT_USER);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchCourses(), fetchSettings()])
      .then(([coursesData, settingsData]) => {
        setCourses(coursesData);
        setUser(settingsData);
      })
      .catch((err) => {
        console.error('Failed to load data from the backend. Is it running?', err);
      })
      .finally(() => setLoading(false));
  }, []);

  const getCourse = (courseId: string) => courses.find((c) => c.id === courseId);

  // The backend owns the unlock cascade now (next activity, module
  // completion, next module). This just persists the change and replaces
  // the course in local state with the server's authoritative result.
  const completeActivity = (activityId: string) => {
    apiCompleteActivity(activityId)
      .then((updatedCourse) => {
        setCourses((prev) => prev.map((c) => (c.id === updatedCourse.id ? updatedCourse : c)));
      })
      .catch((err) => console.error('Failed to complete activity:', err));
  };

  const updateUserSettingsRemote = (patch: UserSettingsPatch) => {
    updateSettings(patch)
      .then((updated) => setUser(updated))
      .catch((err) => console.error('Failed to update settings:', err));
  };

  // Called after course creation finishes, so a newly-approved course shows
  // up in My Courses/Today without a full page reload.
  const refreshCourses = () => fetchCourses().then(setCourses);

  const value = useMemo(
    () => ({
      courses,
      user,
      loading,
      getCourse,
      completeActivity,
      updateUserSettings: updateUserSettingsRemote,
      refreshCourses,
    }),
    [courses, user, loading],
  );

  return <AppDataContext.Provider value={value}>{children}</AppDataContext.Provider>;
}

export function useAppData(): AppDataContextValue {
  const ctx = useContext(AppDataContext);
  if (!ctx) throw new Error('useAppData must be used within an AppDataProvider');
  return ctx;
}
