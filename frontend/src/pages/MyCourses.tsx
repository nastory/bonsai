import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, Pencil, Plus, Trash2, X } from 'lucide-react';
import { useAppData } from '../context/AppDataContext';
import { CourseCard } from '../components/course/CourseCard';
import { Button } from '../components/ui/Button';
import { ConfirmDialog } from '../components/layout/ConfirmDialog';

export function MyCourses() {
  const { courses, deleteCourse } = useAppData();
  const [editMode, setEditMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [actionsOpen, setActionsOpen] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  // Courses that never finished creation (still mid-interview or awaiting
  // outline approval) have no real content and no way to resume from here,
  // so they'd just be dead entries in the list.
  const visibleCourses = courses.filter((c) => c.stage === 'active' || c.stage === 'completed');

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const exitEditMode = () => {
    setEditMode(false);
    setSelectedIds(new Set());
    setActionsOpen(false);
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await Promise.all([...selectedIds].map((id) => deleteCourse(id)));
      setSelectedIds(new Set());
      setConfirming(false);
    } catch (err) {
      console.error('Failed to delete one or more courses:', err);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="mx-auto max-w-3xl px-8 py-10">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-bonsai-text">My Courses</h1>
        <div className="flex items-center gap-2">
          {editMode ? (
            <div className="relative">
              <Button variant="secondary" onClick={() => setActionsOpen((open) => !open)}>
                Actions{selectedIds.size > 0 ? ` (${selectedIds.size})` : ''}
                <ChevronDown className="h-4 w-4" />
              </Button>
              {actionsOpen && (
                <div
                  className="absolute right-0 z-10 mt-1 w-40 overflow-hidden rounded-lg border border-bonsai-border bg-white py-1 shadow-lg"
                  onMouseLeave={() => setActionsOpen(false)}
                >
                  <button
                    type="button"
                    disabled={selectedIds.size === 0}
                    onClick={() => {
                      setActionsOpen(false);
                      setConfirming(true);
                    }}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-600 hover:bg-bonsai-cream disabled:cursor-not-allowed disabled:text-bonsai-text-muted disabled:hover:bg-transparent"
                  >
                    <Trash2 className="h-4 w-4" />
                    Delete
                  </button>
                  <button
                    type="button"
                    onClick={exitEditMode}
                    className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-bonsai-text hover:bg-bonsai-cream"
                  >
                    <X className="h-4 w-4" />
                    Cancel
                  </button>
                </div>
              )}
            </div>
          ) : (
            <Button variant="outline" onClick={() => setEditMode(true)}>
              <Pencil className="h-4 w-4" />
              Edit Courses
            </Button>
          )}
          <Link to="/create">
            <Button>
              <Plus className="h-4 w-4" />
              New Course
            </Button>
          </Link>
        </div>
      </div>

      <div className="flex flex-col gap-3">
        {visibleCourses.map((course) => (
          <CourseCard
            key={course.id}
            course={course}
            selectable={editMode}
            selected={selectedIds.has(course.id)}
            onToggleSelect={() => toggleSelect(course.id)}
          />
        ))}
      </div>

      {confirming && (
        <ConfirmDialog
          title={`Delete ${selectedIds.size} course${selectedIds.size === 1 ? '' : 's'}?`}
          description="This permanently deletes the course, its modules, and everything generated in it. This can't be undone."
          confirmLabel={deleting ? 'Deleting...' : 'Delete'}
          onCancel={() => setConfirming(false)}
          onConfirm={handleDelete}
        />
      )}
    </div>
  );
}
