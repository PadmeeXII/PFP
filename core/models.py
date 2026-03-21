from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from approval_system import settings

class Department(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class User(AbstractUser):
    ROLE_CHOICES = (
        ('ADMIN', 'Admin'),
        ('EMPLOYEE', 'Employee'),
        ('APPROVER', 'Approver'),
    )

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True)
    picture = models.ImageField(upload_to='profiles/', null=True, blank=True)


class Request(models.Model):
    STATUS_CHOICES = (
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('IN_PROGRESS', 'In Progress'),
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    file = models.FileField(upload_to='requests/', null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    approver_step1 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='step1_requests'
    )
    approver_step2 = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='step2_requests'
    )
    comment = models.TextField(null=True,blank=True)
    current_step = models.IntegerField(default=1)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Approval(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    approver = models.ForeignKey(User, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='PENDING')
    comment = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)

    def approve(self):
        self.status = 'APPROVED'
        self.approved_at = timezone.now()
        self.save()
        self.request.status = 'APPROVED'
        self.request.save()

    def reject(self):
        self.status = 'REJECTED'
        self.approved_at = timezone.now()
        self.save()
        self.request.status = 'REJECTED'
        self.request.save()

class ActivityLog(models.Model):
    request = models.ForeignKey(Request, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    comment = models.TextField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action}"