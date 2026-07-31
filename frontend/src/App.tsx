import { Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { Today } from './pages/Today';
import { MyCourses } from './pages/MyCourses';
import { CourseHome } from './pages/CourseHome';
import { CreateCourse } from './pages/CreateCourse';
import { OutlineReview } from './pages/OutlineReview';
import { Lesson } from './pages/Lesson';
import { Settings } from './pages/Settings';
import { Library } from './pages/Library';
import { About } from './pages/About';
import { Terms } from './pages/Terms';
import { Privacy } from './pages/Privacy';
import { UserPolicy } from './pages/UserPolicy';

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Today />} />
        <Route path="/courses" element={<MyCourses />} />
        <Route path="/courses/:courseId" element={<CourseHome />} />
        <Route path="/create" element={<CreateCourse />} />
        <Route path="/create/review/:courseId" element={<OutlineReview />} />
        <Route
          path="/courses/:courseId/modules/:moduleId/activities/:activityId"
          element={<Lesson />}
        />
        <Route path="/library" element={<Library />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/about" element={<About />} />
        <Route path="/terms" element={<Terms />} />
        <Route path="/privacy" element={<Privacy />} />
        <Route path="/policy" element={<UserPolicy />} />
      </Route>
    </Routes>
  );
}

export default App;
