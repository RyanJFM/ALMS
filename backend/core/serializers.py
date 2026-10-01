from rest_framework import serializers
from .models import User, Course, Assignment, AssignmentSession, EventLog, Submission
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role']

class CourseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Course
        fields = ['id', 'title', 'code', 'instructor', 'created_at']

class AssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Assignment
        fields = ['id', 'course', 'title', 'prompt', 'assignment_type', 'due_date']

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

    def validate_assignment(self, value):
        if value.due_date < timezone.now():
            raise serializers.ValidationError("Cannot start a session for an overdue assignment!")
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