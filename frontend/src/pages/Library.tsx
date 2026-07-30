import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAppData } from '../context/AppDataContext';
import { Input } from '../components/ui/Input';
import { activityPath } from '../lib/courseHelpers';

export function Library() {
  const { courses } = useAppData();
  const [query, setQuery] = useState('');

  const results = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return [];

    return courses.flatMap((course) =>
      course.modules.flatMap((module) =>
        module.activities
          .filter((activity) => activity.title.toLowerCase().includes(q))
          .map((activity) => ({ course, module, activity })),
      ),
    );
  }, [courses, query]);

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <h1 className="text-2xl font-semibold text-bonsai-text">Library</h1>
      <p className="mt-1 text-sm text-bonsai-text-muted">
        Search everything you've learned across your courses.
      </p>

      <div className="relative mt-6">
        <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-bonsai-text-muted" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search lessons, modules, topics..."
          className="pl-9"
        />
      </div>

      <div className="mt-6 space-y-2">
        {query && results.length === 0 && (
          <p className="text-sm text-bonsai-text-muted">No matches yet.</p>
        )}
        {results.map(({ course, module, activity }) => (
          <Link
            key={activity.id}
            to={activityPath(course.id, module.id, activity.id)}
            className="block rounded-lg border border-bonsai-border bg-white px-4 py-3 hover:bg-bonsai-cream"
          >
            <p className="text-sm font-medium text-bonsai-text">{activity.title}</p>
            <p className="text-xs text-bonsai-text-muted">
              {course.title} • {module.title}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
