from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Avg
import joblib, os

from .models import StressRecord, EmployeeProfile, Project, ProjectAllocation

# 🔹 Load ML model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model = joblib.load(os.path.join(BASE_DIR, "stress_model.pkl"))
scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))

# 🔹 Home Page
def home(request):
    return render(request, 'admin_home.html')

# 🔹 Login
def user_login(request):
    error = None
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            if user.is_superuser or user.is_staff:
                return redirect('/admin-dashboard/')

            profile = EmployeeProfile.objects.filter(user=user).first()
            if profile:
                if profile.role == 'PM':
                    return redirect('/pm-dashboard/')
                elif profile.role == 'EMP':
                    return redirect('/employee-dashboard/')
            return redirect('/')
        else:
            error = "Invalid credentials"
    return render(request, 'login.html', {'error': error})

# 🔹 Admin Dashboard
@login_required
def admin_dashboard(request):
    if not request.user.is_superuser:
        return redirect('/')

    employees = EmployeeProfile.objects.all()
    projects = Project.objects.all()
    allocations = ProjectAllocation.objects.all()
    records = StressRecord.objects.all()

    total_employees = employees.count()
    total_projects = projects.count()
    total_allocations = allocations.count()
    avg_score = records.aggregate(Avg('mental_health_score'))['mental_health_score__avg']
    high_risk_records = StressRecord.objects.filter(mental_health_score__lt=40)

    return render(request, 'admin_dashboard.html', {
        'employees': employees,
        'records': records,   # ✅ ADD THIS LINE
        'total_employees': total_employees,
        'total_projects': total_projects,
        'total_allocations': total_allocations,
        'avg_score': avg_score,
        'high_risk_records': high_risk_records
    })

# 🔹 PM Dashboard
@login_required
def pm_dashboard(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        if request.user.is_superuser:
            return redirect('/admin-dashboard/')
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)
    project_data = []
    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)
        project_data.append({
            'project': project,
            'allocations': allocations,
            'allocated_count': allocations.count()
        })

    return render(request, 'pm_dashboard.html', {'project_data': project_data})

# 🔹 PM Profile
@login_required
def pm_profile(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')
    return render(request, 'pm_profile.html', {'profile': profile})

# 🔹 Add Employee
@login_required
def add_employee(request):
    if not request.user.is_superuser:
        return redirect('/')
    message = None
    if request.method == 'POST':
        user = User.objects.create_user(
            username=request.POST.get('username'),
            password=request.POST.get('password')
        )
        EmployeeProfile.objects.create(
            user=user,
            employee_id=request.POST.get('employee_id'),
            full_name=request.POST.get('full_name'),
            age=request.POST.get('age'),
            gender=request.POST.get('gender'),
            department=request.POST.get('department'),
            job_role=request.POST.get('job_role'),
            work_experience=request.POST.get('work_experience'),
            role=request.POST.get('role')
        )
        message = "Employee Registered Successfully"
    return render(request, 'add_emp.html', {'message': message})

# 🔹 Employee Dashboard
@login_required
def employee_dashboard(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'EMP':
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(employee=profile)
    total_allocated_hours = sum(a.allocated_hours_per_week for a in allocations)

    score, status, recommendation = None, None, None
    if request.method == 'POST':
        workload_score = float(request.POST.get('workload_score'))
        job_satisfaction = float(request.POST.get('job_satisfaction'))
        sleep_hours = float(request.POST.get('sleep_hours'))
        physical_activity = float(request.POST.get('physical_activity'))
        caffeine = float(request.POST.get('caffeine'))
        stress_level = float(request.POST.get('stress_level'))

        input_data = [[
            total_allocated_hours,
            workload_score,
            job_satisfaction,
            sleep_hours,
            physical_activity,
            caffeine,
            stress_level
        ]]
        input_scaled = scaler.transform(input_data)
        score = model.predict(input_scaled)[0]

        if score < 40:
            status = "High Risk"
            recommendation = "You are under high stress. Reduce workload, improve sleep, reduce caffeine, and consider taking leave."
        elif score < 70:
            status = "Medium Risk"
            recommendation = "Moderate stress detected. Improve sleep schedule and increase physical activity."
        else:
            status = "Healthy"
            recommendation = "Good mental health. Maintain work-life balance and healthy routine."

        StressRecord.objects.create(
            user=request.user,
            work_hours_per_week=total_allocated_hours,
            workload_score=workload_score,
            job_satisfaction=job_satisfaction,
            sleep_hours=sleep_hours,
            physical_activity_hrs=physical_activity,
            caffeine_intake=caffeine,
            stress_level=stress_level,
            mental_health_score=score
        )

    records = StressRecord.objects.filter(user=request.user).order_by('-created_at')
    chart_labels = [r.created_at.strftime("%Y-%m-%d") for r in records[::-1]]
    chart_scores = [r.mental_health_score for r in records[::-1]]

    return render(request, 'emp_dashboard.html', {
        'profile': profile,
        'allocations': allocations,
        'total_allocated_hours': total_allocated_hours,
        'score': score,
        'status': status,
        'recommendation': recommendation,
        'records': records,
        'chart_labels': chart_labels,
        'chart_scores': chart_scores
    })

# 🔹 Project Management
@login_required
def create_project(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')
    if request.method == 'POST':
        Project.objects.create(
            project_name=request.POST.get('project_name'),
            project_description=request.POST.get('project_description'),
            max_employees=request.POST.get('max_employees'),
            start_date=request.POST.get('start_date'),
            end_date=request.POST.get('end_date'),
            created_by=request.user
        )
        return redirect('/pm-dashboard/')
    return render(request, 'create_project.html')

@login_required
def allocate_employee(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')
    employees = EmployeeProfile.objects.filter(role='EMP')
    projects = Project.objects.filter(created_by=request.user)
    error = None
    if request.method == 'POST':
        project_id = request.POST.get('project')
        selected_employees = request.POST.getlist('employees')
        project = Project.objects.get(id=project_id)
        current_count = ProjectAllocation.objects.filter(project=project).count()
        if current_count + len(selected_employees) > project.max_employees:
            error = f"Only {project.max_employees - current_count} slots remaining!"
        else:
            for emp_id in selected_employees:
                employee = EmployeeProfile.objects.get(id=emp_id)
                hours = request.POST.get(f'hours_{emp_id}')
                if hours:
                    ProjectAllocation.objects.create(
                        employee=employee,
                        project=project,
                        allocated_hours_per_week=hours,
                        allocated_by=request.user
                    )
            return redirect('/project-allocations/')
    return render(request, 'allocate_employee.html', {
        'employees': employees,
        'projects': projects,
        'error': error
    })

# 🔹 Project Allocations (Admin + PM)
@login_required
def project_allocations(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if request.user.is_superuser:
        projects = Project.objects.all()
    elif profile and profile.role == 'PM':
        projects = Project.objects.filter(created_by=request.user)
    else:
        return redirect('/')

    project_data = []
    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)
        total_hours = sum(a.allocated_hours_per_week for a in allocations)
        project_data.append({
            'project': project,
            'allocations': allocations,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })
    return render(request, 'project_allocations.html', {'project_data': project_data})

# 🔹 Project Detail
@login_required
def project_detail(request, project_id):
    profile = EmployeeProfile.objects.filter(user=request.user).first()

    if request.user.is_superuser:
        project = get_object_or_404(Project, id=project_id)
    elif profile and profile.role == 'PM':
        project = get_object_or_404(Project, id=project_id, created_by=request.user)
    else:
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(project=project)
    total_hours = sum(a.allocated_hours_per_week for a in allocations)

    return render(request, 'project_detail.html', {
        'project': project,
        'allocations': allocations,
        'total_hours': total_hours,
        'employee_count': allocations.count()
    })

# 🔹 Project Mental Report (PM only)
@login_required
def project_mental_report(request):
    profile = EmployeeProfile.objects.filter(user=request.user).first()
    if not profile or profile.role != 'PM':
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)
    report_data = []

    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)
        employee_data = []
        for allocation in allocations:
            latest_record = StressRecord.objects.filter(
                user=allocation.employee.user
            ).order_by('-created_at').first()
            score = latest_record.mental_health_score if latest_record else None
            employee_data.append({
                'employee': allocation.employee,
                'score': score
            })
        report_data.append({
            'project': project,
            'employees': employee_data
        })

    return render(request, 'project_mental_report.html', {'report_data': report_data})

# 🔹 Logout
def logout_view(request):
    logout(request)
    return redirect('login')

# 🔹 View Employees (Admin only)
@login_required
def view_employees(request):
    if not request.user.is_superuser:
        return redirect('/')
    employees = EmployeeProfile.objects.filter(role='EMP')
    return render(request, 'view_emp.html', {'employees': employees})

# 🔹 View Project Managers (Admin only)
@login_required
def view_project_managers(request):
    if not request.user.is_superuser:
        return redirect('/')
    managers = EmployeeProfile.objects.filter(role='PM')
    return render(request, 'view_pm.html', {'managers': managers})

# 🔹 Login Redirect (role-based)
@login_required
def login_redirect(request):
    if request.user.is_superuser:
        return redirect('/admin-dashboard/')
    else:
        profile = EmployeeProfile.objects.filter(user=request.user).first()
        if profile and profile.role == 'PM':
            return redirect('/pm-dashboard/')
        elif profile and profile.role == 'EMP':
            return redirect('/employee-dashboard/')
        else:
            return redirect('/')



@login_required
def admin_project_allocations(request):
    if not request.user.is_superuser:
        return redirect('/')

    projects = Project.objects.all()
    project_data = []
    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)
        total_hours = sum(a.allocated_hours_per_week for a in allocations)
        project_data.append({
            'project': project,
            'allocations': allocations,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })

    return render(request, 'admin_project_allocation.html', {
        'project_data': project_data
    })


@login_required
def admin_project_detail(request, project_id):
    if not request.user.is_superuser:
        return redirect('/')

    project = get_object_or_404(Project, id=project_id)
    allocations = ProjectAllocation.objects.filter(project=project)
    total_hours = sum(a.allocated_hours_per_week for a in allocations)

    return render(request, 'admin_project_details.html', {
        'project': project,
        'allocations': allocations,
        'total_hours': total_hours,
        'employee_count': allocations.count()
    })
