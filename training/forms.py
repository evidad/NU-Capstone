from django import forms

class FitUploadForm(forms.Form):
    file = forms.FileField(
        label="Upload .fit file",
        help_text="Select a Garmin .fit file",
        widget=forms.ClearableFileInput(attrs={"accept": ".fit"})
    )

    def clean_file(self):
        f = self.cleaned_data["file"]
        name = (f.name or "").lower()
        if not name.endswith(".fit"):
            raise forms.ValidationError("Only .fit files are allowed.")
        return f
