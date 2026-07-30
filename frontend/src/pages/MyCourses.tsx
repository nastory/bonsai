import { Link } from 'react-router-dom';
import { Plus } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { CourseCard } from '../components/course/CourseCard';
import { Button } from '../components/ui/Button';

export function MyCourses() {
  const { courses } = useAppData();

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-bonsai-text">My Courses</h1>
        <Link to="/create">
          <Button>
            <Plus className="h-4 w-4" />
            New Course
          </Button>
        </Link>
      </div>

      <div className="flex flex-col gap-3">
        {courses.map((course) => (
          <CourseCard key={course.id} course={course} />
        ))}
      </div>
    </div>
  );
}
