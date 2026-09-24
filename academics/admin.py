from django.contrib import admin
from .models import Institution, AcademicYear, CBCLevel, CBCPerformance, OldCurriculumLevel, OldCurriculumPerformance, UniversityEnrollment, EmploymentRecord, AcademicCalendarEvent
for model in [Institution, AcademicYear, CBCLevel, CBCPerformance, OldCurriculumLevel, OldCurriculumPerformance, UniversityEnrollment, EmploymentRecord, AcademicCalendarEvent]:
    admin.site.register(model)
