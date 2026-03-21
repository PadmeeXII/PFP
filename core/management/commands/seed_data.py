from django.core.management.base import BaseCommand
from core.models import Department, User
from django.contrib.auth.hashers import make_password

class Command(BaseCommand):
    help = 'Seed initial data'

    def handle(self, *args, **kwargs):

        # ✅ กันรันซ้ำ (สำคัญมาก)
        if User.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ มีข้อมูลอยู่แล้ว ข้าม"))
            return
        elif Department.objects.exists():
            self.stdout.write(self.style.WARNING("⚠️ มีข้อมูลอยู่แล้ว ข้าม"))
            return

        # =========================
        # สร้างแผนก
        # =========================
        dept_admin = Department.objects.create(name="ฝ่ายบริหาร")
        dept_engineer = Department.objects.create(name="ฝ่ายวิศวกรรม")
        dept_account = Department.objects.create(name="ฝ่ายบัญชี")
        dept_site = Department.objects.create(name="ฝ่ายหน้างานก่อสร้าง")

        password = make_password("1234")

        # =========================
        # ADMIN (2 คน)
        # =========================
        admins = [
            ("admin1", "ธนกร", "ศรีสุวรรณ"),
            ("admin2", "กนกวรรณ", "อินทรชัย"),
        ]

        for u, f, l in admins:
            User.objects.create(
                username=u,
                first_name=f,
                last_name=l,
                role="ADMIN",
                department=dept_admin,
                password=password
            )

        # =========================
        # APPROVER + EMPLOYEE
        # =========================
        data = [
            (dept_engineer,
                [("approver1","วิศรุต","ทองดี"), ("approver2","ปกรณ์","ช่างเหล็ก")],
                [("employee1","สมชาย","ใจดี"), ("employee2","ประยูร","มั่นคง"),
                 ("employee3","ธีรพงษ์","แก้วงาม"), ("employee4","อนุชา","วงศ์ดี")]
            ),
            (dept_account,
                [("approver3","อรทัย","ศรีไทย"), ("approver4","รัตนา","บุญมี")],
                [("employee5","สุภาพร","คำแสน"), ("employee6","นงลักษณ์","ทองคำ"),
                 ("employee7","ปรียา","จันทร์งาม"), ("employee8","พิมพ์ชนก","ศรีสุข")]
            ),
            (dept_site,
                [("approver5","ชัยวัฒน์","ก่อสร้าง"), ("approver6","สมพงษ์","คอนกรีต")],
                [("employee9","วิชัย","แข็งแรง"), ("employee10","บุญส่ง","ช่างปูน"),
                 ("employee11","เอกชัย","งานดี"), ("employee12","สันติ","ขยัน")]
            )
        ]

        for dept, approvers, employees in data:
            for u, f, l in approvers:
                User.objects.create(
                    username=u,
                    first_name=f,
                    last_name=l,
                    role="APPROVER",
                    department=dept,
                    password=password
                )

            for u, f, l in employees:
                User.objects.create(
                    username=u,
                    first_name=f,
                    last_name=l,
                    role="EMPLOYEE",
                    department=dept,
                    password=password
                )

        self.stdout.write(self.style.SUCCESS("✅ สร้าง user 20 คนเรียบร้อยแล้ว"))