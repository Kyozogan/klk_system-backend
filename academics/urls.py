from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    InstitutionViewSet, AcademicYearViewSet,
    CBCLevelViewSet, CBCPerformanceViewSet,
    OldCurriculumLevelViewSet, OldCurriculumPerformanceViewSet,
    UniversityEnrollmentViewSet, UniversitySemesterResultViewSet,
    EmploymentRecordViewSet, CalendarEventViewSet
)

router = DefaultRouter()
router.register('institutions', InstitutionViewSet)
router.register('academic-years', AcademicYearViewSet)
router.register('cbc-levels', CBCLevelViewSet)
router.register('cbc-performance', CBCPerformanceViewSet)
router.register('old-curriculum-levels', OldCurriculumLevelViewSet)
router.register('old-curriculum-performance', OldCurriculumPerformanceViewSet)
router.register('university-enrollments', UniversityEnrollmentViewSet)
router.register('semester-results', UniversitySemesterResultViewSet)
router.register('employment', EmploymentRecordViewSet)
router.register('calendar', CalendarEventViewSet)

urlpatterns = [path('', include(router.urls))]
