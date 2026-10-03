from rest_framework import permissions


def is_admin(user):
    """ALMS has no `admin` role choice; Django staff/superusers are admins."""
    return bool(user and user.is_authenticated and (user.is_staff or user.is_superuser))


def is_instructor(user):
    return bool(
        user
        and user.is_authenticated
        and user.role == user.Role.INSTRUCTOR
    )


class IsSelfOrAdmin(permissions.BasePermission):
    """Users can view/edit their own account; only admins can create accounts."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == 'POST':
            return is_admin(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        return is_admin(request.user) or obj.pk == request.user.pk


class IsInstructorOrAdmin(permissions.BasePermission):
    """Authenticated users may read; only instructors/admins may write."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.method in permissions.SAFE_METHODS or is_admin(request.user) or is_instructor(request.user)


class IsCourseInstructorOrAdmin(permissions.BasePermission):
    """Authenticated users may read; writes belong to the course instructor/admin."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.method in permissions.SAFE_METHODS or is_admin(request.user) or is_instructor(request.user)

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        if hasattr(obj, 'instructor_id'):
            instructor_id = obj.instructor_id
        elif hasattr(obj, 'course_id'):
            instructor_id = obj.course.instructor_id
        else:
            return False
        return is_admin(request.user) or (
            is_instructor(request.user) and instructor_id == request.user.id
        )


class IsSessionOwnerOrInstructor(permissions.BasePermission):
    """A student owns their session/submission; instructors see their course work."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == 'POST':
            # Session creation is student-owned. Instructors/admins use their
            # course workflows; the session submit action operates on an object.
            return is_admin(request.user) or request.user.role == request.user.Role.STUDENT
        return True

    def has_object_permission(self, request, view, obj):
        if is_admin(request.user):
            return True

        if hasattr(obj, 'student_id') and hasattr(obj, 'assignment_id'):
            student_id = obj.student_id
            assignment = obj.assignment
        elif hasattr(obj, 'session_id'):
            student_id = obj.session.student_id
            assignment = obj.session.assignment
        else:
            return False

        if is_instructor(request.user):
            return assignment.course.instructor_id == request.user.id
        return (
            request.user.role == request.user.Role.STUDENT
            and student_id == request.user.id
        )


class IsSubmissionOwnerOrInstructor(IsSessionOwnerOrInstructor):
    """Submission creation must go through the session's submit action."""

    def has_permission(self, request, view):
        if getattr(view, 'action', None) == 'create':
            return False
        return super().has_permission(request, view)


class IsEventLogOwnerOrInstructor(permissions.BasePermission):
    """Event logs are visible and mutable only through their session access."""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method == 'POST':
            return is_admin(request.user) or request.user.role == request.user.Role.STUDENT or is_instructor(request.user)
        return True

    def has_object_permission(self, request, view, obj):
        if is_admin(request.user):
            return True
        session = obj.session
        if is_instructor(request.user):
            return session.assignment.course.instructor_id == request.user.id
        return (
            request.user.role == request.user.Role.STUDENT
            and session.student_id == request.user.id
        )
