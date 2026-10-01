from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid
import hashlib


# Create your models here.

# custom user model
class User(AbstractUser):
    class Role(models.TextChoices):
            INSTRUCTOR = 'INSTRUCTOR', 'Instructor'
            STUDENT = 'STUDENT', 'Student'

    role = models.CharField(
          max_length=20,
          choices=Role.choices,
          default=Role.STUDENT
    )

# course model
class Course(models.Model):
    title = models.CharField(max_length=255)
    code = models.CharField(
         max_length=20,
         unique=True
    )
    instructor = models.ForeignKey(
         User,
         on_delete=models.CASCADE,
         related_name='courses_taught'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
         return f"{self.title} ({self.code})"

# assignment model
class Assignment(models.Model):
    class AssignmentType(models.TextChoices):
        PROGRAMMING = 'Programming', 'VS Code Programming'
        WRITTEN = 'WRITTEN', 'Web Editor Report'

    course = models.ForeignKey(
         Course,
         on_delete=models.CASCADE,
         related_name='assignments'
    )

    title = models.CharField(max_length=225)
    prompt = models.TextField()
    assignment_type = models.CharField(
         max_length=20,
         choices=AssignmentType.choices,
         default=AssignmentType.WRITTEN
    )
    due_date = models.DateTimeField()

    def __str__(self):
         return f"{self.title} ({self.course.code})"

# session
class AssignmentSession(models.Model):
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='work_sessions'
    )
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='sessions'
    )
    session_token = models.UUIDField(
        default=uuid.uuid4,
        editable=False,
        unique=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)

    is_submitted = models.BooleanField(default=False)

    def __str__(self):
         return f"Session {self.session_token} blong to {self.student.username}"

# event log
class EventLog(models.Model):
    session = models.ForeignKey(
        AssignmentSession,
        on_delete=models.CASCADE,
        related_name='events'
     )

    timestamp = models.DateTimeField(auto_now_add=True)
    event_type = models.CharField(max_length=50)
    source = models.CharField(max_length=50)
    metadata = models.JSONField(default=dict)

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"

class Submission(models.Model):
    session = models.OneToOneField(
        AssignmentSession,
        on_delete=models.CASCADE,
        related_name='submission'
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    verification_key = models.CharField(max_length=64, unique=True, editable=False)
    file_hash = models.CharField(max_length=64)
    integrity_report_summary = models.JSONField(default=dict)

    def save(self, *args, **kwargs):
        if not self.verification_key:
            raw_string = f"{self.session.student.id}-{self.session.assignment.id}-{self.submitted_at}"
            self.verification_key = hashlib.sha256(raw_string.encode()).hexdigest()[:16].upper()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Submission {self.verification_key} : {self.session.student.username}"

    
