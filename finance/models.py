from django.db import models
from beneficiaries.models import Beneficiary
from simple_history.models import HistoricalRecords


class BudgetCategory(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = 'Budget Categories'

    def __str__(self):
        return self.name


class FinancialAidPackage(models.Model):
    AID_TYPE_CHOICES = [
        ('full', 'Full Scholarship'),
        ('partial', 'Partial Scholarship'),
        ('bursary', 'Bursary'),
        ('loan', 'Study Loan'),
        ('emergency', 'Emergency Fund'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
    ]

    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='aid_packages')
    aid_type = models.CharField(max_length=20, choices=AID_TYPE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    annual_amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_packages')
    approval_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.beneficiary.full_name} - {self.get_aid_type_display()} ({self.status})"


class Disbursement(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('mpesa', 'M-Pesa'),
        ('bank_transfer', 'Bank Transfer'),
        ('cheque', 'Cheque'),
        ('cash', 'Cash'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processed', 'Processed'),
        ('failed', 'Failed'),
        ('reversed', 'Reversed'),
    ]

    aid_package = models.ForeignKey(FinancialAidPackage, on_delete=models.CASCADE, related_name='disbursements')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    currency = models.CharField(max_length=3, default='KES')
    disbursement_date = models.DateField()
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    reference_no = models.CharField(max_length=100, blank=True)
    category = models.ForeignKey(BudgetCategory, on_delete=models.SET_NULL, null=True, blank=True)
    purpose = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    processed_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True, related_name='processed_disbursements')
    receipt = models.FileField(upload_to='receipts/', blank=True, null=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    history = HistoricalRecords()

    def __str__(self):
        return f"{self.aid_package.beneficiary.full_name} - KES {self.amount} ({self.disbursement_date})"


class SchoolFeeRecord(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('partial', 'Partially Paid'),
        ('paid', 'Fully Paid'),
        ('waived', 'Waived'),
    ]

    beneficiary = models.ForeignKey(Beneficiary, on_delete=models.CASCADE, related_name='fee_records')
    academic_year = models.CharField(max_length=10)
    term = models.CharField(max_length=1, choices=[('1', 'Term 1'), ('2', 'Term 2'), ('3', 'Term 3')])
    institution_name = models.CharField(max_length=200)
    total_fee = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    due_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.balance = self.total_fee - self.amount_paid
        if self.balance <= 0:
            self.status = 'paid'
        elif self.amount_paid > 0:
            self.status = 'partial'
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.beneficiary.full_name} - {self.academic_year} T{self.term} ({self.status})"


class AnnualBudget(models.Model):
    year = models.CharField(max_length=10, unique=True)
    total_budget = models.DecimalField(max_digits=15, decimal_places=2)
    allocated_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    spent_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey('users.User', on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Budget {self.year}: KES {self.total_budget}"
