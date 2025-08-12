from django import forms
from .models import Contact


class ContactForm(forms.ModelForm):
    """Form for creating and updating contacts"""
    
    class Meta:
        model = Contact
        fields = [
            # Essential fields
            'first_name', 'last_name', 'email', 'job_title', 'phone_number',
            
            # Location
            'location_city', 'location_country',
            
            # Company information
            'company_name', 'company_industry', 'company_website', 
            'company_description', 'company_linkedin_url', 'company_headcount',
            
            # Professional data
            'linkedin_url', 'linkedin_headline', 'linkedin_position', 'linkedin_summary',
            
            # Campaign customization
            'tailored_tone_first_line', 'tailored_tone_ps_statement', 'tailored_tone_subject',
            'custom_ai_1', 'custom_ai_2',
            
            # Media
            'profile_image_url', 'logo_image_url',
            
            # Additional tracking data
            'funnel_unique_id', 'funnel_step', 'sequence_unique_id', 'variation_unique_id',
            'websitecontent', 'leadscore', 'esp'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter email address',
                'required': True
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter job title'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter phone number'
            }),
            'location_city': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter city'
            }),
            'location_country': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter country'
            }),
            'company_name': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter company name'
            }),
            'company_industry': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter company industry'
            }),
            'company_website': forms.URLInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://company-website.com'
            }),
            'company_description': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter company description',
                'rows': 3
            }),
            'company_linkedin_url': forms.URLInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://linkedin.com/company/...'
            }),
            'company_headcount': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'e.g., 1-10, 11-50, 51-200'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://linkedin.com/in/...'
            }),
            'linkedin_headline': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter LinkedIn headline'
            }),
            'linkedin_position': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter LinkedIn position'
            }),
            'linkedin_summary': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter LinkedIn summary',
                'rows': 3
            }),
            'tailored_tone_first_line': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter personalized opening line',
                'rows': 2
            }),
            'tailored_tone_ps_statement': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter P.S. statement',
                'rows': 2
            }),
            'tailored_tone_subject': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter custom email subject'
            }),
            'custom_ai_1': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter custom AI field 1',
                'rows': 2
            }),
            'custom_ai_2': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter custom AI field 2',
                'rows': 2
            }),
            'profile_image_url': forms.URLInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://example.com/profile-image.jpg'
            }),
            'logo_image_url': forms.URLInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'https://example.com/company-logo.jpg'
            }),
            'funnel_unique_id': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter funnel ID'
            }),
            'funnel_step': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter funnel step'
            }),
            'sequence_unique_id': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter sequence ID'
            }),
            'variation_unique_id': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter variation ID'
            }),
            'websitecontent': forms.Textarea(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter website content',
                'rows': 3
            }),
            'leadscore': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter lead score (1-3)'
            }),
            'esp': forms.TextInput(attrs={
                'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
                'placeholder': 'Enter email service provider'
            }),
        }
        
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address *',
            'job_title': 'Job Title',
            'phone_number': 'Phone Number',
            'location_city': 'City',
            'location_country': 'Country',
            'company_name': 'Company Name',
            'company_industry': 'Company Industry',
            'company_website': 'Company Website',
            'company_description': 'Company Description',
            'company_linkedin_url': 'Company LinkedIn URL',
            'company_headcount': 'Company Size',
            'linkedin_url': 'LinkedIn Profile URL',
            'linkedin_headline': 'LinkedIn Headline',
            'linkedin_position': 'LinkedIn Position',
            'linkedin_summary': 'LinkedIn Summary',
            'tailored_tone_first_line': 'Personalized Opening Line',
            'tailored_tone_ps_statement': 'P.S. Statement',
            'tailored_tone_subject': 'Custom Email Subject',
            'custom_ai_1': 'Custom AI Field 1',
            'custom_ai_2': 'Custom AI Field 2',
            'profile_image_url': 'Profile Image URL',
            'logo_image_url': 'Company Logo URL',
            'funnel_unique_id': 'Funnel ID',
            'funnel_step': 'Funnel Step',
            'sequence_unique_id': 'Sequence ID',
            'variation_unique_id': 'Variation ID',
            'websitecontent': 'Website Content',
            'leadscore': 'Lead Score',
            'esp': 'Email Service Provider',
        }
    
    def clean_email(self):
        """Validate email uniqueness"""
        email = self.cleaned_data.get('email')
        if email:
            # Check if editing existing contact
            if self.instance.pk:
                # Exclude current instance from uniqueness check
                if Contact.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                    raise forms.ValidationError("A contact with this email already exists.")
            else:
                # New contact - check if email exists
                if Contact.objects.filter(email=email).exists():
                    raise forms.ValidationError("A contact with this email already exists.")
        return email
    
    def clean_leadscore(self):
        """Validate lead score"""
        leadscore = self.cleaned_data.get('leadscore')
        if leadscore and leadscore not in ['1', '2', '3', '']:
            raise forms.ValidationError("Lead score must be 1, 2, or 3.")
        return leadscore


class ContactSearchForm(forms.Form):
    """Form for searching contacts"""
    
    search = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500',
            'placeholder': 'Search by name, email, or company...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Statuses'),
            ('not_sent', 'Not Sent'),
            ('sent', 'Sent'),
            ('delivered', 'Delivered'),
            ('opened', 'Opened'),
            ('clicked', 'Clicked'),
            ('bounced', 'Bounced'),
            ('complained', 'Complained'),
            ('failed', 'Failed'),
        ],
        widget=forms.Select(attrs={
            'class': 'w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-blue-500'
        })
    )


class CSVUploadForm(forms.Form):
    """Form for uploading CSV files to import contacts"""
    
    csv_file = forms.FileField(
        label="CSV File",
        help_text="Upload a CSV file containing contact information",
        widget=forms.FileInput(attrs={
            'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
            'accept': '.csv'
        })
    )
    
    def clean_csv_file(self):
        csv_file = self.cleaned_data.get('csv_file')
        
        if csv_file:
            # Check file extension
            if not csv_file.name.endswith('.csv'):
                raise forms.ValidationError("File must be a CSV file.")
            
            # Check file size (limit to 10MB)
            if csv_file.size > 10 * 1024 * 1024:
                raise forms.ValidationError("File size must be less than 10MB.")
        
        return csv_file
