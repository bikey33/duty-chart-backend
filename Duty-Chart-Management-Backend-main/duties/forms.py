# duties/forms.py
from django import forms

from django import forms
import pandas as pd
from .serializers import ALLOWED_HEADERS

class RosterBulkUploadForm(forms.Form):
    file = forms.FileField()

    def clean_file(self):
        f = self.cleaned_data['file']

        # Verify Excel extension
        name = (f.name or "").lower()
        if not (name.endswith(".xlsx") or name.endswith(".xls")):
            raise forms.ValidationError("Only .xlsx or .xls Excel files are allowed.")

        # Try loading just the header row to validate columns
        try:
            try:
                df = pd.read_excel(f, nrows=0, engine="openpyxl")
            except Exception:
                f.seek(0)
                df = pd.read_excel(f, nrows=0)  # let pandas guess engine
        except Exception as e:
            raise forms.ValidationError(f"Could not read Excel file: {e}")

        # Normalize headers
        df.columns = [str(c).strip() for c in df.columns]

        if list(df.columns) != ALLOWED_HEADERS:
            missing = [c for c in ALLOWED_HEADERS if c not in df.columns]
            extra = [c for c in df.columns if c not in ALLOWED_HEADERS]
            msg_parts = []
            if missing:
                msg_parts.append(f"Missing columns: {', '.join(missing)}")
            if extra:
                msg_parts.append(f"Unexpected columns: {', '.join(extra)}")
            raise forms.ValidationError(" | ".join(msg_parts))

        # Reset pointer for later full read in admin view
        f.seek(0)
        return f