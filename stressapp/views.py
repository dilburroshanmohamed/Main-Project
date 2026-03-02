from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.db.models import Max
from .models import StressRecord, EmployeeProfile, Project, ProjectAllocation
from django.db.models import Avg
from django.contrib.auth import logout 
from django.shortcuts import redirect
import joblib
import os

# 🔹 Load ML model
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
model = joblib.load(os.path.join(BASE_DIR, "stress_model.pkl"))
scaler = joblib.load(os.path.join(BASE_DIR, "scaler.pkl"))


# 🔹 Home Page
def home(request):
    return render(request, 'admin_home.html')


# 🔹 Common Login

def user_login(request):
    error = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # 👑 Admin (HR)
            if user.is_staff:
                return redirect('/admin-dashboard/')

            # Get employee profile
            profile = EmployeeProfile.objects.get(user=user)

            # 👨‍💼 Project Manager
            if profile.role == 'PM':
                return redirect('/pm-dashboard/')

            # 👨‍💻 Employee
            return redirect('/employee-dashboard/')

        else:
            error = "Invalid credentials"

    return render(request, 'login.html', {'error': error})

# 🔹 Admin Dashboard
from .models import Project, ProjectAllocation
from django.db.models import Avg

@login_required
def admin_dashboard(request):

    if not request.user.is_staff:
        return redirect('/')

    employees = EmployeeProfile.objects.all()
    projects = Project.objects.all()
    allocations = ProjectAllocation.objects.all()
    records = StressRecord.objects.all()

    total_employees = employees.count()
    total_projects = projects.count()
    total_allocations = allocations.count()

    avg_score = records.aggregate(Avg('mental_health_score'))['mental_health_score__avg']

    # High risk employees
    high_risk_records = StressRecord.objects.filter(mental_health_score__lt=40)

    return render(request, 'admin_dashboard.html', {
        'employees': employees,
        'total_employees': total_employees,
        'total_projects': total_projects,
        'total_allocations': total_allocations,
        'avg_score': avg_score,
        'high_risk_records': high_risk_records
    })



@login_required
def pm_dashboard(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
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

    return render(request, 'pm_dashboard.html', {
        'project_data': project_data
    })
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    allocations = ProjectAllocation.objects.filter(
        project__created_by=request.user
    )

    return render(request, 'pm_dashboard.html', {
        'projects': projects,
        'allocations': allocations
    })




@login_required
def pm_profile(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    return render(request, 'pm_profile.html', {
        'profile': profile
    })




# 🔹 Add Employee
@login_required
def add_employee(request):

    if not request.user.is_staff:
        return redirect('/')

    message = None

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        employee_id = request.POST.get('employee_id')
        full_name = request.POST.get('full_name')
        age = request.POST.get('age')
        gender = request.POST.get('gender')
        department = request.POST.get('department')
        job_role = request.POST.get('job_role')
        work_experience = request.POST.get('work_experience')
        role = request.POST.get('role')
        user = User.objects.create_user(username=username, password=password)


        EmployeeProfile.objects.create(
            user=user,
            employee_id=employee_id,
            full_name=full_name,
            age=age,
            gender=gender,
            department=department,
            job_role=job_role,
            work_experience=work_experience,
            role=role
        )

        message = "Employee Registered Successfully"

    return render(request, 'add_emp.html', {'message': message})


# 🔹 Employee Dashboard (ML Prediction)
@login_required
def dashboard(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    # Allow only employees
    if profile.role != 'EMP':
        return redirect('/')

    # Get allocated projects
    allocations = ProjectAllocation.objects.filter(employee=profile)

    # Calculate total weekly hours automatically
    total_allocated_hours = sum(
        allocation.allocated_hours_per_week
        for allocation in allocations
    )

    # Initialize variables
    score = None
    status = None
    recommendation = None

    if request.method == 'POST':

        workload_score = float(request.POST.get('workload_score'))
        job_satisfaction = float(request.POST.get('job_satisfaction'))
        sleep_hours = float(request.POST.get('sleep_hours'))
        physical_activity = float(request.POST.get('physical_activity'))
        caffeine = float(request.POST.get('caffeine'))
        stress_level = float(request.POST.get('stress_level'))

        # 🔥 Use allocated hours automatically
        input_data = [[
            total_allocated_hours,
            workload_score,
            job_satisfaction,
            sleep_hours,
            physical_activity,
            caffeine,
            stress_level
        ]]

        # ML Prediction
        input_scaled = scaler.transform(input_data)
        score = model.predict(input_scaled)[0]

        # Determine status
        if score < 40:
            status = "High Risk"
        elif score < 70:
            status = "Medium Risk"
        else:
            status = "Healthy"

        # Recommendation system
        if score < 40:
            recommendation = "You are under high stress. Reduce workload, improve sleep, reduce caffeine, and consider taking leave."
        elif score < 70:
            recommendation = "Moderate stress detected. Improve sleep schedule and increase physical activity."
        else:
            recommendation = "Good mental health. Maintain work-life balance and healthy routine."

        # Save record
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

    # Get previous records
    records = StressRecord.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'emp_dashboard.html', {
        'profile': profile,
        'allocations': allocations,
        'total_allocated_hours': total_allocated_hours,
        'score': score,
        'status': status,
        'recommendation': recommendation,
        'records': records
    })

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'EMP':
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(employee=profile)

    total_allocated_hours = sum(
        allocation.allocated_hours_per_week
        for allocation in allocations
    )

    score = None
    status = None

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

        # Determine status
        if score < 40:
            status = "High Risk"
        elif score < 70:
            status = "Medium Risk"
        else:
            status = "Healthy"

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

    return render(request, 'emp_dashboard.html', {
        'profile': profile,
        'allocations': allocations,
        'total_allocated_hours': total_allocated_hours,
        'score': score,
        'status': status,
        'records': records
    })
    profile = EmployeeProfile.objects.get(user=request.user)

    # Only employee allowed
    if profile.role != 'EMP':
        return redirect('/')

    score = None

    if request.method == 'POST':

        work_hours = float(request.POST.get('work_hours'))
        workload_score = float(request.POST.get('workload_score'))
        job_satisfaction = float(request.POST.get('job_satisfaction'))
        sleep_hours = float(request.POST.get('sleep_hours'))
        physical_activity = float(request.POST.get('physical_activity'))
        caffeine = float(request.POST.get('caffeine'))
        stress_level = float(request.POST.get('stress_level'))

        input_data = [[
            work_hours,
            workload_score,
            job_satisfaction,
            sleep_hours,
            physical_activity,
            caffeine,
            stress_level
        ]]

        input_scaled = scaler.transform(input_data)
        score = model.predict(input_scaled)[0]

        StressRecord.objects.create(
            user=request.user,
            work_hours_per_week=work_hours,
            workload_score=workload_score,
            job_satisfaction=job_satisfaction,
            sleep_hours=sleep_hours,
            physical_activity_hrs=physical_activity,
            caffeine_intake=caffeine,
            stress_level=stress_level,
            mental_health_score=score
        )

    records = StressRecord.objects.filter(user=request.user).order_by('-created_at')

    # Prepare data for chart
    chart_labels = []
    chart_scores = []

    for record in records[::-1]:  # oldest to newest
        chart_labels.append(record.created_at.strftime("%Y-%m-%d"))
        chart_scores.append(record.mental_health_score)

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




@login_required
def create_project(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    if request.method == 'POST':
        project_name = request.POST.get('project_name')
        project_description = request.POST.get('project_description')
        max_employees = request.POST.get('max_employees')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')

        Project.objects.create(
            project_name=project_name,
            project_description=project_description,
            max_employees=max_employees,
            start_date=start_date,
            end_date=end_date,
            created_by=request.user
        )

        return redirect('/pm-dashboard/')

    return render(request, 'create_project.html')
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    if request.method == 'POST':
        name = request.POST.get('project_name')
        desc = request.POST.get('project_description')

        Project.objects.create(
            project_name=name,
            project_description=desc,
            created_by=request.user
        )

        return redirect('/pm-dashboard/')

    return render(request, 'create_project.html')



@login_required
def allocate_employee(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    employees = EmployeeProfile.objects.filter(role='EMP')
    projects = Project.objects.filter(created_by=request.user)

    error = None

    if request.method == 'POST':
        project_id = request.POST.get('project')
        selected_employees = request.POST.getlist('employees')

        project = Project.objects.get(id=project_id)

        # Count existing allocations
        current_count = ProjectAllocation.objects.filter(project=project).count()

        # Check max limit
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
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    employees = EmployeeProfile.objects.filter(role='EMP')
    projects = Project.objects.filter(created_by=request.user)

    if request.method == 'POST':
        selected_employees = request.POST.getlist('employees')
        project_id = request.POST.get('project')
        hours = request.POST.get('hours')

        project = Project.objects.get(id=project_id)

        for emp_id in selected_employees:
            employee = EmployeeProfile.objects.get(id=emp_id)

            ProjectAllocation.objects.create(
                employee=employee,
                project=project,
                allocated_hours_per_week=hours,
                allocated_by=request.user
            )

        return redirect('/project-allocations/')

    return render(request, 'allocate_employee.html', {
        'employees': employees,
        'projects': projects
    })

    profile = EmployeeProfile.objects.get(user=request.user)

    # Only PM allowed
    if profile.role != 'PM':
        return redirect('/')

    employees = EmployeeProfile.objects.filter(role='EMP')
    projects = Project.objects.filter(created_by=request.user)

    if request.method == 'POST':
        employee_id = request.POST.get('employee')
        project_id = request.POST.get('project')
        hours = request.POST.get('hours')

        employee = EmployeeProfile.objects.get(id=employee_id)
        project = Project.objects.get(id=project_id)

        ProjectAllocation.objects.create(
            employee=employee,
            project=project,
            allocated_hours_per_week=hours,
            allocated_by=request.user
        )

        return redirect('/pm-dashboard/')

    return render(request, 'allocate_employee.html', {
        'employees': employees,
        'projects': projects
    })



@login_required
def project_allocations(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    project_data = []

    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)

        allocation_data = []

        for allocation in allocations:

            latest_record = StressRecord.objects.filter(
                user=allocation.employee.user
            ).order_by('-created_at').first()

            if latest_record:
                score = latest_record.mental_health_score
            else:
                score = None

            allocation_data.append({
                'employee': allocation.employee,
                'hours': allocation.allocated_hours_per_week,
                'score': score
            })

        total_hours = sum(
            allocation.allocated_hours_per_week
            for allocation in allocations
        )

        project_data.append({
            'project': project,
            'allocations': allocation_data,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })

    return render(request, 'project_allocations.html', {
        'project_data': project_data
    })
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    project_data = []

    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)

        total_hours = sum(
            allocation.allocated_hours_per_week
            for allocation in allocations
        )

        project_data.append({
            'project': project,
            'allocations': allocations,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })

    return render(request, 'project_allocations.html', {
        'project_data': project_data
    })
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    project_data = []

    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)

        total_hours = sum(
            allocation.allocated_hours_per_week
            for allocation in allocations
        )

        project_data.append({
            'project': project,
            'allocations': allocations,
            'total_hours': total_hours,
            'employee_count': allocations.count()
        })

    return render(request, 'project_allocations.html', {
        'project_data': project_data
    })
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    allocations = ProjectAllocation.objects.filter(
        project__created_by=request.user
    ).select_related('employee', 'project')

    return render(request, 'project_allocations.html', {
        'allocations': allocations
    })



from django.shortcuts import get_object_or_404

@login_required
def project_detail(request, project_id):
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    project = get_object_or_404(Project, id=project_id, created_by=request.user)
    allocations = ProjectAllocation.objects.filter(project=project)

    total_hours = sum(a.allocated_hours_per_week for a in allocations)

    return render(request, 'project_detail.html', {
        'project': project,
        'allocations': allocations,
        'total_hours': total_hours,
        'employee_count': allocations.count()
    })











@login_required
def project_mental_report(request):

    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
        return redirect('/')

    projects = Project.objects.filter(created_by=request.user)

    report_data = []

    # Get all stress records once
    latest_records = {}

    all_records = StressRecord.objects.order_by('user', '-created_at')

    for record in all_records:
        if record.user_id not in latest_records:
            latest_records[record.user_id] = record

    for project in projects:
        allocations = ProjectAllocation.objects.filter(project=project)

        employee_data = []

        for allocation in allocations:
            record = latest_records.get(allocation.employee.user.id)

            if record:
                score = record.mental_health_score
            else:
                score = None

            employee_data.append({
                'employee': allocation.employee,
                'score': score
            })

        report_data.append({
            'project': project,
            'employees': employee_data
        })

    return render(request, 'project_mental_report.html', {
        'report_data': report_data
    })
    profile = EmployeeProfile.objects.get(user=request.user)

    if profile.role != 'PM':
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

            if latest_record:
                score = latest_record.mental_health_score
            else:
                score = None

            employee_data.append({
                'employee': allocation.employee,
                'score': score
            })

        report_data.append({
            'project': project,
            'employees': employee_data
        })

    return render(request, 'project_mental_report.html', {
        'report_data': report_data
    })

def logout_view(request):
    logout(request) # clears the session 
    return redirect('login')


@login_required
def view_employees(request):
    if not request.user.is_staff:
        return redirect('/')
    employees = EmployeeProfile.objects.filter(role='EMP')
    return render(request, 'view_emp.html', {'employees': employees})


@login_required
def view_project_managers(request):
    if not request.user.is_staff:
        return redirect('/')
    managers = EmployeeProfile.objects.filter(role='PM')
    return render(request, 'view_pm.html', {'managers': managers})
