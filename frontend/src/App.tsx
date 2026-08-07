import { Routes, Route } from 'react-router-dom';
import { AppShell } from './components/layout/AppShell';
import { Today } from './pages/Today';
import { MyCourses } from './pages/MyCourses';
import { CourseHome } from './pages/CourseHome';
import { CreateCourse } from './pages/CreateCourse';
import { OutlineReview } from './pages/OutlineReview';
import { ChangeDirection } from './pages/ChangeDirection';
import { ChangeDirectionReview } from './pages/ChangeDirectionReview';
import { Lesson } from './pages/Lesson';
import { Settings } from './pages/Settings';
import { ResourcePicker } from './pages/ResourcePicker';
import { FlashCardsSession } from './pages/FlashCardsSession';
import { QuizMeSession } from './pages/QuizMeSession';
import { AskMeAnything } from './pages/AskMeAnything';
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
        <Route
          path="/courses/:courseId/modules/:moduleId/change-direction"
          element={<ChangeDirection />}
        />
        <Route
          path="/courses/:courseId/modules/:moduleId/change-direction/review"
          element={<ChangeDirectionReview />}
        />
        <Route
          path="/resources/flash-cards"
          element={
            <ResourcePicker
              title="Flash Cards"
              description="Pick a course and module to study with question/answer flash cards, generated once and reused."
              basePath="/resources/flash-cards"
            />
          }
        />
        <Route path="/resources/flash-cards/:courseId/:moduleId" element={<FlashCardsSession />} />
        <Route
          path="/resources/quiz-me"
          element={
            <ResourcePicker
              title="Quiz Me"
              description="Pick a course and module to generate a standalone quiz, saved for next time."
              basePath="/resources/quiz-me"
            />
          }
        />
        <Route path="/resources/quiz-me/:courseId/:moduleId" element={<QuizMeSession />} />
        <Route path="/resources/ask-me-anything" element={<AskMeAnything />} />
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
