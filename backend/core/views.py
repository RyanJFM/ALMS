from rest_framework import viewsets
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from .permissions import (
    IsSelfOrAdmin,
    IsCourseInstructorOrAdmin,
    IsSessionOwnerOrInstructor,
    IsSubmissionOwnerOrInstructor,
    IsEventLogOwnerOrInstructor,
    is_admin,
    is_instructor,
)
from .models import User, Course, Assignment, AssignmentSession, EventLog, Submission
from .serializers import (
    UserSerializer,
    CourseSerializer,
    AssignmentSerializer,
    AssignmentSessionSerializer,
    EventLogSerializer,
    SubmissionSerializer
)

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsSelfOrAdmin]

    def get_queryset(self):
        if is_admin(self.request.user):
            return User.objects.all()
        return User.objects.filter(pk=self.request.user.pk)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    permission_classes = [IsCourseInstructorOrAdmin]

    def get_queryset(self):
        if is_admin(self.request.user):
            return Course.objects.all()
        if is_instructor(self.request.user):
            return Course.objects.filter(instructor=self.request.user)
        return Course.objects.all()

class AssignmentViewSet(viewsets.ModelViewSet):
    queryset = Assignment.objects.all()
    serializer_class = AssignmentSerializer
    permission_classes = [IsCourseInstructorOrAdmin]

    def get_queryset(self):
        if is_admin(self.request.user):
            return Assignment.objects.all()
        if is_instructor(self.request.user):
            return Assignment.objects.filter(course__instructor=self.request.user)
        return Assignment.objects.all()

class AssignmentSessionViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSession.objects.all()
    serializer_class = AssignmentSessionSerializer
    permission_classes = [IsSessionOwnerOrInstructor]

    def get_queryset(self):
        user = self.request.user
        if is_admin(user):
            return AssignmentSession.objects.all()
        if is_instructor(user):
            return AssignmentSession.objects.filter(assignment__course__instructor=user)
        if user.role == user.Role.STUDENT:
            return AssignmentSession.objects.filter(student=user)
        return AssignmentSession.objects.none()

    def perform_create(self, serializer):
        if is_admin(self.request.user):
            serializer.save()
        else:
            serializer.save(student=self.request.user)

    @action(detail=True, methods=['post'])
    def submit(self, request, pk=None):
        session = self.get_object()

        # check if the session is already submitted
        if session.is_submitted:
            return Response(
                {"error" : "This session has already been submitted."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # check if past due date
        if session.assignment.due_date < timezone.now():
            return Response(
                {"error" : "Due date has passed"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # process the submission
        session.is_submitted = True
        session.save()

        submission = Submission.objects.create(
            session=session,
            file_hash=request.data.get('file_hash', 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'),
            integrity_report_summary=request.data.get('integrity_report_summary', 'Clean submission')
        )

        serializer = SubmissionSerializer(submission)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class EventLogViewSet(viewsets.ModelViewSet):
    queryset = EventLog.objects.all()
    serializer_class = EventLogSerializer
    permission_classes = [IsEventLogOwnerOrInstructor]

    def get_queryset(self):
        user = self.request.user
        if is_admin(user):
            return EventLog.objects.all()
        if is_instructor(user):
            return EventLog.objects.filter(session__assignment__course__instructor=user)
        if user.role == user.Role.STUDENT:
            return EventLog.objects.filter(session__student=user)
        return EventLog.objects.none()

class SubmissionViewSet(viewsets.ModelViewSet):
    queryset = Submission.objects.all()
    serializer_class = SubmissionSerializer
    permission_classes = [IsSubmissionOwnerOrInstructor]

    def get_queryset(self):
        user = self.request.user
        if is_admin(user):
            return Submission.objects.all()
        if is_instructor(user):
            return Submission.objects.filter(session__assignment__course__instructor=user)
        if user.role == user.Role.STUDENT:
            return Submission.objects.filter(session__student=user)
        return Submission.objects.none()
