from django.db import models
from beneficiaries.models import Beneficiary
from simple_history.models import HistoricalRecords


class Institution(models.Model):
    LEVEL_CHOICES = [
        ('ecde', 'ECDE/Pre-School'), ('primary', 'Primary School'),
        ('junior_secondary', 'Junior Secondary (CBC)'), ('senior_secondary', 'Senior Secondary (CBC)'),
        ('secondary', 'Secondary School (8-4-4)'), ('university', 'University/College'),
        ('vocational', 'Vocational/TVET'),
    ]
    name = models.CharField(max_length=200)
    level = models.CharField(max_length=30, choices=LEVEL_CHOICES)
    sub_county = models.CharField(max_length=100, blank=True)
    county = models.CharField(max_length=100, blank=True)
    registration_no = models.CharField(max_length=50, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"


class AcademicYear(models.Model):
    year = models.CharField(max_length=10)
    start_date = models.DateField()
    end_date = models.DateField()
    is_current = models.BooleanField(default=False)

    class Meta:
        ordering = ['-year']

    def __str__(self):
        return self.year

    def save(self, *args, **kwargs):
        if self.is_current:
            AcademicYear.objects.filter(is_current=True).update(is_current=False)
        super().save(*args, **kwargs)


class CBCLevel(models.Model):
    STAGE_CHOICES = [
        ('pp1','PP1'), ('pp2','PP2'),
        ('grade1','Grade 1'), ('grade2','Grade 2'), ('grade3','Grade 3'),
        ('grade4','Grade 4'), ('grade5','Grade 5'), ('grade6','Grade 6'),
        ('grade7','Grade 7'), ('grade8','Grade 8'), ('grade9','Grade 9'),
        ('grade10','Grade 10'), ('grade11','Grade 11'), ('grade12','Grade 12'),
    ]
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='cbc_levels')
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    stream = models.CharField(max_length=50, blank=True)
    admission_no = models.CharField(max_length=30, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    promoted = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return f"{self.beneficiary.full_name} - {self.get_stage_display()}"


class CBCPerformance(models.Model):
    TERM_CHOICES = [('1','Term 1'), ('2','Term 2'), ('3','Term 3')]
    RATING_CHOICES = [('EE','Exceeds Expectation'), ('ME','Meets Expectation'), ('AE','Approaches Expectation'), ('BE','Below Expectation')]
    LEARNING_AREA_CHOICES = [
        ('literacy','Literacy Activities'), ('numeracy','Numeracy Activities'), ('hygiene','Hygiene & Nutrition'),
        ('environmental','Environmental Activities'), ('psychomotor','Psychomotor & Creative Arts'),
        ('english','English'), ('kiswahili','Kiswahili/KSL'), ('mathematics','Mathematics'),
        ('integrated_science','Integrated Science'), ('social_studies','Social Studies'),
        ('religious_ed','Religious Education'), ('creative_arts','Creative Arts & Sports'),
        ('agriculture','Pre-Technical & Pre-Career Education'), ('ict','Digital Literacy/ICT'),
        ('core_science','Core Science'), ('humanities','Humanities'), ('applied_science','Applied Sciences'),
        ('arts_sports','Arts & Sports Science'),
    ]
    cbc_level = models.ForeignKey(CBCLevel, on_delete=models.CASCADE, related_name='performances')
    term = models.CharField(max_length=1, choices=TERM_CHOICES)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    learning_area = models.CharField(max_length=50, choices=LEARNING_AREA_CHOICES)
    rating = models.CharField(max_length=2, choices=RATING_CHOICES)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    teacher_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        unique_together = ['cbc_level', 'term', 'academic_year', 'learning_area']


class OldCurriculumLevel(models.Model):
    GRADE_CHOICES = [
        ('std1','Standard 1'), ('std2','Standard 2'), ('std3','Standard 3'), ('std4','Standard 4'),
        ('std5','Standard 5'), ('std6','Standard 6'), ('std7','Standard 7'), ('std8','Standard 8'),
        ('form1','Form 1'), ('form2','Form 2'), ('form3','Form 3'), ('form4','Form 4'),
    ]
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='old_curriculum_levels')
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.CharField(max_length=10, choices=GRADE_CHOICES)
    stream = models.CharField(max_length=50, blank=True)
    admission_no = models.CharField(max_length=30, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    promoted = models.BooleanField(default=False)
    class_position = models.PositiveIntegerField(null=True, blank=True)
    total_students = models.PositiveIntegerField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ['-start_date']


class OldCurriculumPerformance(models.Model):
    TERM_CHOICES = [('1','Term 1'), ('2','Term 2'), ('3','Term 3')]
    SUBJECT_CHOICES = [
        ('english','English'), ('kiswahili','Kiswahili'), ('mathematics','Mathematics'),
        ('science','Science'), ('social_studies','Social Studies'), ('religious_ed','CRE/IRE/HRE'),
        ('biology','Biology'), ('chemistry','Chemistry'), ('physics','Physics'),
        ('geography','Geography'), ('history','History'), ('business_studies','Business Studies'),
        ('computer','Computer Studies'), ('agriculture','Agriculture'), ('french','French'),
        ('art_design','Art & Design'), ('music','Music'), ('home_science','Home Science'),
    ]
    old_curriculum_level = models.ForeignKey(OldCurriculumLevel, on_delete=models.CASCADE, related_name='performances')
    term = models.CharField(max_length=1, choices=TERM_CHOICES)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=30, choices=SUBJECT_CHOICES)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    grade = models.CharField(max_length=2, blank=True)
    teacher_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-created_at']
        unique_together = ['old_curriculum_level', 'term', 'academic_year', 'subject']

    def save(self, *args, **kwargs):
        s = float(self.score)
        if s >= 75: self.grade = 'A'
        elif s >= 70: self.grade = 'A-'
        elif s >= 65: self.grade = 'B+'
        elif s >= 60: self.grade = 'B'
        elif s >= 55: self.grade = 'B-'
        elif s >= 50: self.grade = 'C+'
        elif s >= 45: self.grade = 'C'
        elif s >= 40: self.grade = 'C-'
        elif s >= 35: self.grade = 'D+'
        elif s >= 30: self.grade = 'D'
        elif s >= 25: self.grade = 'D-'
        else: self.grade = 'E'
        super().save(*args, **kwargs)


class UniversityEnrollment(models.Model):
    DEGREE_TYPE_CHOICES = [
        ('certificate','Certificate'), ('diploma','Diploma'), ('degree',"Bachelor's Degree"),
        ('masters',"Master's Degree"), ('phd','PhD'), ('tvet','TVET/Vocational'),
    ]
    STATUS_CHOICES = [
        ('enrolled','Enrolled'), ('on_leave','On Study Leave'), ('graduated','Graduated'),
        ('withdrawn','Withdrawn'), ('deferred','Deferred'),
    ]
    # unique=True — a scholar has exactly one university/tertiary record in
    # this system. Previously this had no constraint at all, so the same
    # scholar could be enrolled at a university twice, with no way to tell
    # which record was "the real one." One record is edited going forward;
    # if a scholar genuinely needs a fresh record (transferred institutions,
    # started a postgraduate programme), staff delete the old one first,
    # which is enforced by the API rather than the database alone so the
    # error message on a duplicate attempt is readable instead of a raw
    # IntegrityError.
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE,
                                    related_name='university_enrollments', unique=True)
    institution = models.ForeignKey(Institution, on_delete=models.SET_NULL, null=True, blank=True)
    degree_type = models.CharField(max_length=20, choices=DEGREE_TYPE_CHOICES)
    course_name = models.CharField(max_length=200)
    student_id = models.CharField(max_length=50, blank=True)
    start_year = models.PositiveIntegerField()
    expected_end_year = models.PositiveIntegerField(null=True, blank=True)
    actual_end_year = models.PositiveIntegerField(null=True, blank=True)
    current_year_of_study = models.PositiveSmallIntegerField(default=1)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='enrolled')
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    graduation_class = models.CharField(max_length=50, blank=True)
    notes = models.TextField(blank=True)
    history = HistoricalRecords()

    class Meta:
        ordering = ['-start_year']

    def __str__(self):
        return f"{self.beneficiary.full_name} - {self.course_name}"


class UniversitySemesterResult(models.Model):
    enrollment = models.ForeignKey(UniversityEnrollment, on_delete=models.CASCADE, related_name='semester_results')
    year_of_study = models.PositiveSmallIntegerField()
    semester = models.CharField(max_length=10)
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.SET_NULL, null=True, blank=True)
    gpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    cgpa = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    units_taken = models.PositiveSmallIntegerField(default=0)
    units_passed = models.PositiveSmallIntegerField(default=0)
    remarks = models.TextField(blank=True)

    class Meta:
        ordering = ['-year_of_study', '-semester']
        unique_together = ['enrollment', 'year_of_study', 'semester']


class EmploymentRecord(models.Model):
    EMPLOYMENT_TYPE = [
        ('fulltime','Full Time'), ('parttime','Part Time'), ('contract','Contract'),
        ('self_employed','Self Employed'), ('internship','Internship'), ('volunteer','Volunteer'),
    ]
    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='employment_records')
    employer = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200)
    employment_type = models.CharField(max_length=20, choices=EMPLOYMENT_TYPE)
    industry = models.CharField(max_length=100, blank=True)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    is_current = models.BooleanField(default=True)
    monthly_salary = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-start_date']


class AcademicCalendarEvent(models.Model):
    EVENT_TYPE_CHOICES = [
        ('term_start','Term Start'), ('term_end','Term End'), ('exam','Examination'),
        ('holiday','Public Holiday'), ('school_event','School Event'), ('meeting','Meeting'),
        ('deadline','Deadline'), ('other','Other'),
    ]
    title = models.CharField(max_length=200)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True)
    applies_to_curriculum = models.CharField(max_length=10, choices=[('all','All'), ('cbc','CBC Only'), ('844','8-4-4 Only')], default='all')
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['start_date']

    def __str__(self):
        return f"{self.title} ({self.start_date})"
