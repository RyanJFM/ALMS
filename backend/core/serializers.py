from rest_framework import serializers
from .models import User, Course, Assignment, AssignmentSession, EventLog, Submission
from django.utils import timezone
from .permissions import is_admin, is_instructor

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if not request or not is_admin(request.user):
            fields['role'].read_only = True
        return fields

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'code', 'instructor', 'created_at']

    def validate_instructor(self, instructor):
        request = self.context.get('request')
        if request and not is_admin(request.user) and instructor.pk != request.user.pk:
            raise serializers.ValidationError("You can only manage courses assigned to you.")
        return instructor

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'course', 'title', 'prompt', 'assignment_type', 'due_date']

    def validate_course(self, course):
        request = self.context.get('request')
        if request and not is_admin(request.user):
            if not is_instructor(request.user) or course.instructor_id != request.user.id:
                raise serializers.ValidationError("You can only manage assignments in your courses.")
        return course

class AssignmentSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentSession
        fields = [
            'id', 
            'student', 
            'assignment', 
            'session_token', 
            'started_at', 
            'last_active', 
            'is_submitted'
        ]
        read_only_fields = ['session_token', 'started_at', 'last_active']

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get('request')
        if not request or not is_admin(request.user):
            fields['student'].read_only = True
        # Submission state is changed by the dedicated submit action only.
        fields['is_submitted'].read_only = True
        return fields

    def validate_assignment(self, value):
        if value.due_date < timezone.now():
            raise serializers.ValidationError("Cannot start a session for an overdue assignment!")
        return value

    def validate_student(self, value):
        request = self.context.get('request')
        if request and not is_admin(request.user) and value.pk != request.user.pk:
            raise serializers.ValidationError("You can only create a session for yourself.")
        return value

class EventLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = EventLog
        fields = ['id', 
                  'session', 
                  'timestamp', 
                  'event_type', 
                  'source', 
                  'metadata']
        read_only_fields = ['timestamp']

    def validate_session(self, session):
        request = self.context.get('request')
        if request:
            user = request.user
            allowed = (
                is_admin(user)
                or (is_instructor(user) and session.assignment.course.instructor_id == user.id)
                or (user.role == user.Role.STUDENT and session.student_id == user.id)
            )
            if not allowed:
                raise serializers.ValidationError("You cannot add events to this session.")
        return session

class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = ['id', 
                  'session', 
                  'submitted_at', 
                  'verification_key', 
                  'file_hash', 
                  'integrity_report_summary']
        read_only_fields = ['submitted_at', 'verification_key']

    def validate_session(self, session):
        request = self.context.get('request')
        if request:
            user = request.user
            allowed = (
                is_admin(user)
                or (is_instructor(user) and session.assignment.course.instructor_id == user.id)
                or (user.role == user.Role.STUDENT and session.student_id == user.id)
            )
            if not allowed:
                raise serializers.ValidationError("You cannot submit work for this session.")
        return session
