from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from .models import Request, Approval, Department, ActivityLog
from django.db.models import Count
from django.http import HttpResponse
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from django.conf import settings
from django.http import FileResponse
import os
from io import BytesIO
import csv

User = get_user_model()

def admin_only(view_func):
    def wrapper(request, *args, **kwargs):
        if request.user.role != 'ADMIN':
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if request.user.role not in allowed_roles:
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

@login_required
def dashboard(request):
    pending = Request.objects.filter(status='PENDING').count()
    approved = Request.objects.filter(status='APPROVED').count()
    rejected = Request.objects.filter(status='REJECTED').count()
    in_progress = Request.objects.filter(status='IN_PROGRESS').count()

    recent = Request.objects.order_by('-created_at')[:5]

    context = {
        'pending': pending,
        'approved': approved,
        'rejected': rejected,
        'in_progress': in_progress,
        'recent': recent,
    }
    return render(request, 'dashboard.html', context)

@login_required
def request_list(request):
    user = request.user
    if user.role == 'EMPLOYEE':
        requests = Request.objects.filter(created_by=user)
    elif user.role == 'APPROVER':
        requests = Request.objects.filter(approver_step1=user,current_step=1,status='PENDING') | Request.objects.filter(approver_step2=user,current_step=2,status='IN_PROGRESS')
    elif user.role == 'ADMIN':
        requests = Request.objects.all()
    
    total_requests = Request.objects.count()

    # EMPLOYEE KPI
    my_requests = Request.objects.filter(created_by=user).count()

    # APPROVER KPI
    pending_step1 = Request.objects.filter(
        approver_step1=user,
        current_step=1,
        status='PENDING'
    ).count()

    pending_step2 = Request.objects.filter(
        approver_step2=user,
        current_step=2,
        status='IN_PROGRESS'
    ).count()

    context = {
        'total_requests': total_requests,
        'my_requests': my_requests,
        'pending_step1': pending_step1,
        'pending_step2': pending_step2,
        'requests': requests,
    }

    return render(request, 'request_list.html', context)

@login_required
@role_required(['EMPLOYEE'])
def create_request(request):
    user = request.user
    approvers = User.objects.filter(role='APPROVER',department=user.department)

    if request.method == 'POST':
        Request.objects.create(
            title=request.POST['title'],
            description=request.POST['description'],
            file=request.FILES.get('file'),
            created_by=request.user,
            approver_step1_id=request.POST['approver1'],
            approver_step2_id=request.POST['approver2']
        )
        return redirect('request_list')

    return render(request, 'create_request.html', {
        'approvers': approvers
    })


@login_required
def request_detail(request, pk):
    req = get_object_or_404(Request, pk=pk)
    return render(request, 'request_detail.html', {'req': req})


@login_required
@role_required(['APPROVER', 'ADMIN'])
def approve_request(request, pk):
    req = get_object_or_404(Request, pk=pk)

    if req.current_step == 1 and request.user == req.approver_step1:
        req.current_step = 2
        req.status = 'IN_PROGRESS'
        req.save()

    elif req.current_step == 2 and request.user == req.approver_step2:
        req.status = 'APPROVED'
        req.save()

    ActivityLog.objects.create(
    request=req,
    user=request.user,
    action='อนุมัติ',
    comment=request.POST.get('comment'),
    )

    return redirect('request_list')

@login_required
@role_required(['APPROVER', 'ADMIN'])
def reject_request(request, pk):
    req = get_object_or_404(Request, pk=pk)
    req.status = 'REJECTED'
    req.save()

    ActivityLog.objects.create(
    request=req,
    user=request.user,
    action='ไม่อนุมัติ',
    comment=request.POST.get('comment'),
    )
    return redirect('request_list')

@login_required
def reports(request):
    status_filter = request.GET.get('status')
    requests = Request.objects.all()

    if status_filter:
        requests = requests.filter(status=status_filter)

    return render(request, 'reports.html', {
        'requests': requests
    })


@login_required
def export_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="report.csv"'

    writer = csv.writer(response)
    writer.writerow(['ID', 'Title', 'Status', 'Created Date'])

    for r in Request.objects.all():
        writer.writerow([r.id, r.title, r.status, r.created_at])

    return response

@login_required
def profile(request):
    user = request.user
    if request.method == 'POST':
        user.username = request.POST.get("username")
        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']
        user.phone = request.POST['phone']
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if password1 or password2:

            if password1 != password2:
                messages.error(request, "รหัสผ่านไม่ตรงกัน")
                return redirect("profile")

            else:
                user.set_password(password1)
                update_session_auth_hash(request, user)

        if request.FILES.get("picture"):
            user.picture = request.FILES.get("picture")

        user.save()


    return render(request, "profile.html", {"user": user})

@login_required
@admin_only
def manage_users(request):
    users = User.objects.all()
    return render(request, 'admin_users.html', {'users': users})


@login_required
@admin_only
def create_user(request):
    departments = Department.objects.all()
    if request.method == 'POST':
        User.objects.create_user(
            username=request.POST['username'],
            password=request.POST['password'],
            role=request.POST['role'],
            department_id=request.POST.get('department') or None
        )
        return redirect('manage_users')

    return render(request, 'admin_create_user.html', {
        'departments': departments
    })


@login_required
@admin_only
def edit_user(request, user_id):
    user_obj = User.objects.get(id=user_id)
    departments = Department.objects.all()

    if request.method == 'POST':
        user_obj.role = request.POST['role']
        user_obj.department_id = request.POST.get('department') or None
        user_obj.save()
        return redirect('manage_users')

    return render(request, 'admin_edit_user.html', {
        'user_obj': user_obj,
        'departments': departments
    })

@login_required
@admin_only
def delete_user(request, pk):
    user = get_object_or_404(User, id=pk)
    user.delete()
    return redirect("manage_users")

@login_required
@admin_only
def manage_departments(request):
    departments = Department.objects.all()
    return render(request, 'admin_departments.html', {
        'departments': departments
    })


@login_required
@admin_only
def create_department(request):
    if request.method == 'POST':
        Department.objects.create(
            name=request.POST['name']
        )
        return redirect('manage_departments')

    return render(request, 'admin_create_department.html')

@login_required
@admin_only
def edit_department(request, pk):
    dept = get_object_or_404(Department, id=pk)

    if request.method == "POST":
        dept.name = request.POST.get("name")
        dept.save()
        return redirect("manage_departments")

    return render(request, "admin_edit_department.html", {"dept": dept})

@login_required
@admin_only
def delete_department(request, pk):
    dept = Department.objects.get(id=pk)
    dept.delete()
    return redirect('manage_departments')


@login_required
def export_request_pdf(request, pk):

    req = get_object_or_404(Request, id=pk)
    logs = ActivityLog.objects.filter(request=req).order_by("timestamp")

    buffer = BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=25,
        bottomMargin=60
    )

    elements = []

    # ---------------- FONT ----------------
    font_path = os.path.join(settings.BASE_DIR, "fonts", "THSarabunNew.ttf")
    pdfmetrics.registerFont(TTFont("THSarabun", font_path))

    styles = getSampleStyleSheet()

    normal = ParagraphStyle(
        'thai',
        parent=styles['Normal'],
        fontName='THSarabun',
        fontSize=16,
        leading=20,
    )

    title = ParagraphStyle(
        'title',
        parent=styles['Normal'],
        fontName='THSarabun',
        fontSize=24,
        alignment=1
    )

    # ---------------- TITLE ----------------

    elements.append(Paragraph("<b>คำขออนุมัติ</b>", title))
    elements.append(Spacer(1,25))

    # ---------------- HEADER ----------------

    logo_path = os.path.join(settings.BASE_DIR, "static","icon","pfp.png")
    logo = Image(logo_path, width=70, height=70)

    file_name = req.file.name.split("/")[-1] if req.file else "-"

    header_data = [[

        logo,

        Paragraph(
        f"""
        <b>หัวข้อ</b> : {req.title}<br/>
        <b>โดย</b> : {req.created_by.get_full_name()}<br/>
        <b>ไฟล์ที่แนบมา</b> : {file_name}
        """,
        normal
        ),

        Paragraph(
        f"""
        เลขที่ PR-{req.id:05d}<br/>
        วันที่ {req.created_at.strftime('%d/%m/%Y')}
        """,
        normal
        )

    ]]

    header_table = Table(header_data, colWidths=[90,330,120])

    header_table.setStyle(TableStyle([

        ('VALIGN',(0,0),(-1,-1),'TOP'),

        ('LEFTPADDING',(0,0),(-1,-1),4),
        ('RIGHTPADDING',(0,0),(-1,-1),4),
        ('TOPPADDING',(0,0),(-1,-1),4),
        ('BOTTOMPADDING',(0,0),(-1,-1),4)

    ]))

    elements.append(header_table)
    elements.append(Spacer(1,20))

    # ---------------- DESCRIPTION ----------------

    desc_header = Table([["รายละเอียด"]], colWidths=[520], rowHeights=[30])

    desc_header.setStyle(TableStyle([

        ('FONTNAME',(0,0),(-1,-1),'THSarabun'),
        ('FONTSIZE',(0,0),(-1,-1),18),

        ('BACKGROUND',(0,0),(-1,-1),colors.lightgrey),

        ('BOX',(0,0),(-1,-1),1,colors.black),

        ('VALIGN',(0,0),(0,0),'TOP'),

        ('TOPPADDING',(0,0),(-1,-1),6),
        ('BOTTOMPADDING',(0,0),(10,10),10)

    ]))

    desc_content = Table([
        [Paragraph(req.description, normal)]
    ], colWidths=[520], rowHeights=[120])

    desc_content.setStyle(TableStyle([

        ('FONTNAME',(0,0),(-1,-1),'THSarabun'),

        ('BOX',(0,0),(-1,-1),1,colors.black),

        ('VALIGN',(0,0),(-1,-1),'TOP'),

        ('LEFTPADDING',(0,0),(-1,-1),10),
        ('RIGHTPADDING',(0,0),(-1,-1),10),

        ('TOPPADDING',(0,0),(-1,-1),10),
        ('BOTTOMPADDING',(0,0),(-1,-1),10)

    ]))

    elements.append(desc_header)
    elements.append(desc_content)

    elements.append(Spacer(1,20))

    # ---------------- ACTIVITY TABLE ----------------

    data = [["ผู้อนุมัติ","การอนุมัติ","วันที่","หมายเหตุ"]]

    for log in logs:

        data.append([
            Paragraph(f"{log.user.first_name} {log.user.last_name}", normal),
            Paragraph(log.action, normal),
            Paragraph(log.timestamp.strftime("%d/%m/%Y %H:%M"), normal),
            Paragraph(log.comment if log.comment else "-", normal)
        ])

    table = Table(data, colWidths=[150,100,130,140])

    table.setStyle(TableStyle([

        ('FONTNAME',(0,0),(-1,-1),'THSarabun'),
        ('FONTSIZE',(0,0),(-1,-1),16),

        ('BACKGROUND',(0,0),(-1,0),colors.lightgrey),

        ('GRID',(0,0),(-1,-1),1,colors.black),

        ('VALIGN',(0,0),(0,0),'TOP'),

        ('TOPPADDING',(0,0),(-1,0),6),
        ('BOTTOMPADDING',(0,0),(10,10),10),

        ('TOPPADDING',(0,1),(-1,-1),4),
        ('BOTTOMPADDING',(0,1),(-1,-1),4)

    ]))

    elements.append(table)

    # ---------------- PAGE DESIGN ----------------

    def draw_page(canvas, doc):

        width, height = A4

        # เส้นกรอบเอกสาร
        canvas.setLineWidth(1)
        canvas.rect(20, 20, width-40, height-40)

        # footer
        canvas.setFont("THSarabun", 14)
        canvas.drawString(40, 30, "P.F.P. Design & Construct Co., Ltd.")

        canvas.drawRightString(width-40, 30, f"Generated: {req.created_at.strftime('%d/%m/%Y')}")

        # QR Code
        verify_url = f"https://pfp-w52b.onrender.com/request-file/{req.id}/"

        qr_code = qr.QrCodeWidget(verify_url)

        bounds = qr_code.getBounds()
        size = 60

        width_qr = bounds[2] - bounds[0]
        height_qr = bounds[3] - bounds[1]

        d = Drawing(size, size, transform=[size/width_qr,0,0,size/height_qr,0,0])

        d.add(qr_code)

        d.drawOn(canvas, width-90, 25)

    # ---------------- BUILD ----------------

    doc.build(elements, onFirstPage=draw_page, onLaterPages=draw_page)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="request_{req.title}.pdf"'
    response.write(pdf)

    return response

import mimetypes

def open_request_file(request, pk):
    req = get_object_or_404(Request, id=pk)

    if not req.file:
        return HttpResponse("No file", status=404)

    file_path = req.file.path
    mime_type, _ = mimetypes.guess_type(file_path)

    return FileResponse(req.file, content_type=mime_type)
