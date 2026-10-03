from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Assignment, AssignmentSession, Course, EventLog, Submission, User
from .permissions import is_admin, is_instructor


class AuthorizationAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.student = User.objects.create_user(
            username='student-one', password='test-password', role=User.Role.STUDENT
        )
        self.other_student = User.objects.create_user(
            username='student-two', password='test-password', role=User.Role.STUDENT
        )
        self.instructor = User.objects.create_user(
            username='instructor-one', password='test-password', role=User.Role.INSTRUCTOR
        )
        self.other_instructor = User.objects.create_user(
            username='instructor-two', password='test-password', role=User.Role.INSTRUCTOR
        )
        self.staff = User.objects.create_user(
            username='staff-user', password='test-password', is_staff=True
        )
        self.superuser = User.objects.create_superuser(
            username='super-user', password='test-password', email='super@example.test'
        )
        self.superuser.is_staff = False
        self.superuser.save(update_fields=['is_staff'])

        self.course = Course.objects.create(
            title='Course One', code='COURSE1', instructor=self.instructor
        )
        self.other_course = Course.objects.create(
            title='Course Two', code='COURSE2', instructor=self.other_instructor
        )
        due_date = timezone.now() + timedelta(days=3)
        self.assignment = Assignment.objects.create(
            course=self.course, title='Assignment One', prompt='Prompt one', due_date=due_date
        )
        self.other_assignment = Assignment.objects.create(
            course=self.other_course, title='Assignment Two', prompt='Prompt two', due_date=due_date
        )
        self.session = AssignmentSession.objects.create(
            student=self.student, assignment=self.assignment
        )
        self.other_session = AssignmentSession.objects.create(
            student=self.other_student, assignment=self.assignment
        )
        self.foreign_course_session = AssignmentSession.objects.create(
            student=self.student, assignment=self.other_assignment
        )
        self.submission = Submission.objects.create(
            session=self.session, file_hash='a' * 64, integrity_report_summary={}
        )
        self.other_submission = Submission.objects.create(
            session=self.other_session, file_hash='b' * 64, integrity_report_summary={}
        )
        self.foreign_course_submission = Submission.objects.create(
            session=self.foreign_course_session,
            file_hash='c' * 64,
            integrity_report_summary={},
        )
        self.event = EventLog.objects.create(
            session=self.session, event_type='edit', source='editor', metadata={}
        )
        self.other_event = EventLog.objects.create(
            session=self.other_session, event_type='edit', source='editor', metadata={}
        )
        self.foreign_course_event = EventLog.objects.create(
            session=self.foreign_course_session,
            event_type='edit',
            source='editor',
            metadata={},
        )

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_role_helpers_and_admin_role_choice(self):
        self.assertTrue(is_instructor(self.instructor))
        self.assertFalse(is_instructor(self.student))
        self.assertEqual(self.student.role, User.Role.STUDENT)
        self.assertTrue(is_admin(self.staff))
        self.assertTrue(is_admin(self.superuser))
        self.assertFalse(hasattr(User.Role, 'ADMIN'))
        self.assertNotIn('ADMIN', User.Role.values)

    def test_instructor_course_access_and_foreign_course_write_denied(self):
        self.authenticate(self.instructor)
        self.assertEqual(self.client.get(f'/api/courses/{self.course.pk}/').status_code, 200)
        self.assertEqual(
            self.client.patch(
                f'/api/courses/{self.other_course.pk}/', {'title': 'Changed'}, format='json'
            ).status_code,
            404,
        )

    def test_instructor_can_manage_own_assignment_but_not_foreign_assignment(self):
        self.authenticate(self.instructor)
        self.assertEqual(
            self.client.get(f'/api/assignments/{self.assignment.pk}/').status_code, 200
        )
        own_update = self.client.patch(
            f'/api/assignments/{self.assignment.pk}/', {'title': 'Updated'}, format='json'
        )
        self.assertEqual(own_update.status_code, 200)
        self.assertEqual(
            self.client.patch(
                f'/api/assignments/{self.other_assignment.pk}/',
                {'title': 'Changed'},
                format='json',
            ).status_code,
            404,
        )

    def test_student_reads_courses_and_assignments_but_cannot_write_them(self):
        self.authenticate(self.student)
        courses = self.client.get('/api/courses/')
        assignments = self.client.get('/api/assignments/')
        self.assertEqual(courses.status_code, 200)
        self.assertEqual(assignments.status_code, 200)
        self.assertEqual(len(courses.data), 2)
        self.assertEqual(len(assignments.data), 2)
        self.assertEqual(
            self.client.post(
                '/api/courses/',
                {'title': 'New', 'code': 'NEW', 'instructor': self.student.pk},
                format='json',
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f'/api/courses/{self.course.pk}/', {'title': 'Changed'}, format='json'
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.post(
                '/api/assignments/',
                {
                    'course': self.course.pk,
                    'title': 'New',
                    'prompt': 'Prompt',
                    'due_date': (timezone.now() + timedelta(days=1)).isoformat(),
                },
                format='json',
            ).status_code,
            403,
        )
        self.assertEqual(
            self.client.patch(
                f'/api/assignments/{self.assignment.pk}/', {'title': 'Changed'}, format='json'
            ).status_code,
            403,
        )

    def test_student_session_queryset_is_owner_scoped(self):
        self.authenticate(self.student)
        self.assertEqual(self.client.get(f'/api/sessions/{self.session.pk}/').status_code, 200)
        self.assertEqual(
            self.client.get(f'/api/sessions/{self.other_session.pk}/').status_code, 404
        )

    def test_instructor_session_queryset_is_course_scoped(self):
        self.authenticate(self.instructor)
        self.assertEqual(self.client.get(f'/api/sessions/{self.session.pk}/').status_code, 200)
        self.assertEqual(
            self.client.get(f'/api/sessions/{self.foreign_course_session.pk}/').status_code, 404
        )

    def test_session_create_uses_authenticated_student_and_ignores_submitted_flag(self):
        self.authenticate(self.student)
        response = self.client.post(
            '/api/sessions/',
            {
                'student': self.other_student.pk,
                'assignment': self.assignment.pk,
                'is_submitted': True,
            },
            format='json',
        )
        self.assertEqual(response.status_code, 201, response.data)
        created = AssignmentSession.objects.get(pk=response.data['id'])
        self.assertEqual(created.student_id, self.student.pk)
        self.assertFalse(created.is_submitted)

    def test_client_cannot_change_session_submitted_state(self):
        self.authenticate(self.student)
        response = self.client.patch(
            f'/api/sessions/{self.session.pk}/', {'is_submitted': True}, format='json'
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.session.refresh_from_db()
        self.assertFalse(self.session.is_submitted)

    def test_student_submission_access_is_owner_scoped(self):
        self.authenticate(self.student)
        self.assertEqual(
            self.client.get(f'/api/submissions/{self.submission.pk}/').status_code, 200
        )
        self.assertEqual(
            self.client.get(f'/api/submissions/{self.other_submission.pk}/').status_code, 404
        )

    def test_instructor_submission_access_is_course_scoped(self):
        self.authenticate(self.instructor)
        self.assertEqual(
            self.client.get(f'/api/submissions/{self.submission.pk}/').status_code, 200
        )
        self.assertEqual(
            self.client.get(f'/api/submissions/{self.foreign_course_submission.pk}/').status_code,
            404,
        )

    def test_submission_creation_must_use_submit_action(self):
        self.authenticate(self.student)
        response = self.client.post(
            '/api/submissions/',
            {'session': self.session.pk, 'file_hash': 'd' * 64},
            format='json',
        )
        self.assertEqual(response.status_code, 403)

    def test_student_event_access_is_owner_scoped(self):
        self.authenticate(self.student)
        self.assertEqual(self.client.get(f'/api/events/{self.event.pk}/').status_code, 200)
        self.assertEqual(self.client.get(f'/api/events/{self.other_event.pk}/').status_code, 404)

    def test_instructor_event_access_is_course_scoped(self):
        self.authenticate(self.instructor)
        self.assertEqual(self.client.get(f'/api/events/{self.event.pk}/').status_code, 200)
        self.assertEqual(
            self.client.get(f'/api/events/{self.foreign_course_event.pk}/').status_code, 404
        )
