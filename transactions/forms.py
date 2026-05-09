from django import forms


class UploadCSVForm(forms.Form):
    file = forms.FileField(label='Transactions CSV file', help_text='Upload the CSV export from your bank.')
