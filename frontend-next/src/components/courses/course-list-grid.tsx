// src/components/courses/course-list-grid.tsx
import { CourseCard } from "./course-card";
import type { CourseListItem } from "@/lib/types/course";

interface CourseListGridProps {
  courses: CourseListItem[];
}

export function CourseListGrid({ courses }: CourseListGridProps) {
  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3">
      {courses.map((course) => (
        <CourseCard key={course.id} course={course} />
      ))}
    </div>
  );
}