import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import type { Course, UserSettings, UserSettingsPatch } from '../types/course';
import {
  fetchCourses,
  fetchSettings,
  updateSettings,
  completeActivity as apiCompleteActivity,
  deleteCourse as apiDeleteCourse,
  generateModuleActivities as apiGenerateModuleActivities,
} from '../lib/api';

const DEFAULT_USER: UserSettings = {
  name: 'Learner',
  feedbackTone: 'encouraging',
  thumbnailGenerationEnabled: true,
  modelProvider: { tier: 'hosted', hasApiKey: false },
  hasTavilyApiKey: false,
  deepSearchEnabled: false,
};

interface AppDataContextValue {
  courses: Course[];
  user: UserSettings;
  loading: boolean;
  getCourse: (courseId: string) => Course | undefined;
  completeActivity: (activityId: string) => void;
  deleteCourse: (courseId: string) => Promise<void>;
  generateModuleActivities: (moduleId: string) => Promise<void>;
  updateUserSettings: (patch: UserSettingsPatch) => Promise<void>;
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

  // Rethrows after logging (same reasoning as generateModuleActivities
  // below) so MyCourses can show an error instead of the course silently
  // staying in the list with no sign the delete failed.
  const deleteCourse = (courseId: string) => {
    return apiDeleteCourse(courseId)
      .then(() => {
        setCourses((prev) => prev.filter((c) => c.id !== courseId));
      })
      .catch((err) => {
        console.error('Failed to delete course:', err);
        throw err;
      });
  };

  // Called when the learner reaches an in-progress module that has no
  // activities yet: generates them server-side, then replaces the course
  // in local state with the server's authoritative result.
  // Rethrows after logging (unlike the other mutators here) so callers that
  // need to react to failure - e.g. CourseHome showing a retry option
  // instead of an indefinite "Generating..." - can do so.
  const generateModuleActivities = (moduleId: string) => {
    return apiGenerateModuleActivities(moduleId)
      .then((updatedCourse) => {
        setCourses((prev) => prev.map((c) => (c.id === updatedCourse.id ? updatedCourse : c)));
      })
      .catch((err) => {
        console.error('Failed to generate module activities:', err);
        throw err;
      });
  };

  // Rethrows after logging (same reasoning as generateModuleActivities
  // above) so callers - e.g. Settings showing a save confirmation or error
  // for a write-only API key field - can react to failure instead of the
  // field just silently clearing with no sign of whether it actually saved.
  const updateUserSettingsRemote = (patch: UserSettingsPatch) => {
    return updateSettings(patch)
      .then((updated) => setUser(updated))
      .catch((err) => {
        console.error('Failed to update settings:', err);
        throw err;
      });
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
      deleteCourse,
      generateModuleActivities,
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
