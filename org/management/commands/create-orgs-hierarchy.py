import pandas as pd
from django.core.management.base import BaseCommand
from orgs.models import Directorate, Department, Office

class Command(BaseCommand):
    help = "Import directorates, departments, and offices from Excel"

    def add_arguments(self, parser):
        parser.add_argument("excel_file", type=str, help="Path to Excel file")

    def handle(self, *args, **options):
        file_path = options["excel_file"]
        df = pd.read_excel(file_path)

        for _, row in df.iterrows():
            directorate_name = row["Directorate Name"]
            department_name = row.get("Department Name")
            office_name = row.get("Office Name")

            if pd.isna(directorate_name):
                continue

            directorate, _ = Directorate.objects.get_or_create(name=directorate_name)

            department = None
            if pd.notna(department_name):
                department, _ = Department.objects.get_or_create(
                    name=department_name,
                    directorate=directorate,
                )

            if pd.notna(office_name) and department:
                Office.objects.get_or_create(
                    name=office_name,
                    department=department,
                )

        self.stdout.write(self.style.SUCCESS("✅ Data imported successfully!"))
