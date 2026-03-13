from django.contrib.auth.models import User as AuthUser
from django.db import models
from datetime import date
from django.contrib.auth.models import User

ROLE_CHOICES = (
    ('PM', 'Project Manager'),
    ('EMP', 'Employee'),
)







class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=50)
    full_name = models.CharField(max_length=100)
    age = models.IntegerField()
    gender = models.CharField(max_length=20)
    department = models.CharField(max_length=50)
    job_role = models.CharField(max_length=50)
    work_experience = models.FloatField()
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='EMP')

    def __str__(self):
        return self.full_name


class Project(models.Model):
    project_name = models.CharField(max_length=100)
    project_description = models.TextField()
    max_employees = models.IntegerField()

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)

    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def total_days(self):
        return (self.end_date - self.start_date).days

    def __str__(self):
        return self.project_name


class ProjectAllocation(models.Model):


    TASK_CHOICES = [
        ('UI/UX', 'UI/UX'),
        ('Database Design', 'Database Design'),
        ('Backend Developer', 'Backend Developer'),
        ('Requirement Gathering', 'Requirement Gathering'),
        ('Testing', 'Testing'),
    ]

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    allocated_hours_per_week = models.FloatField()
    task_role = models.CharField(max_length=50, choices=TASK_CHOICES)
    progress = models.IntegerField(default=0)
    allocated_by = models.ForeignKey(User, on_delete=models.CASCADE)
    allocated_date = models.DateTimeField(auto_now_add=True)

    



    def __str__(self):
        return f"{self.employee.full_name} - {self.project.project_name}"

    class Meta:
        unique_together = ('employee', 'project')

class StressRecord(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    work_hours_per_week = models.FloatField()
    workload_score = models.FloatField()
    job_satisfaction = models.FloatField()
    sleep_hours = models.FloatField()
    physical_activity_hrs = models.FloatField()
    caffeine_intake = models.FloatField()
    stress_level = models.FloatField()
    mental_health_score = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.mental_health_score}"