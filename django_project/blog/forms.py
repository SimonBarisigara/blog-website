from django import forms
from django.core.exceptions import ValidationError
from blog.models import Post, Comment, Newsletter, ContactMessage


class PostForm(forms.ModelForm):
    """Form for creating and updating posts"""
    
    class Meta:
        model = Post
        fields = [
            'title',
            'content',
            'excerpt',
            'featured_image',
            'category',
            'tags',
            'status',
            'is_featured',
            'is_pinned',
            'allow_comments',
            'meta_description',
            'meta_keywords'
        ]
        
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter an engaging title...',
                'maxlength': '200'
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control rich-editor',
                'placeholder': 'Write your post content here...',
                'rows': 15
            }),
            'excerpt': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Brief summary of your post...',
                'rows': 3,
                'maxlength': '300'
            }),
            'featured_image': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control'
            }),
            'tags': forms.CheckboxSelectMultiple(),
            'status': forms.Select(attrs={
                'class': 'form-control'
            }),
            'meta_description': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'SEO meta description...',
                'rows': 2,
                'maxlength': '160'
            }),
            'meta_keywords': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'keyword1, keyword2, keyword3...'
            }),
        }
        
        labels = {
            'featured_image': 'Featured Image',
            'is_featured': 'Mark as Featured Post',
            'is_pinned': 'Pin to Top',
            'allow_comments': 'Allow Comments',
            'meta_description': 'Meta Description (SEO)',
            'meta_keywords': 'Meta Keywords (SEO)',
        }
        
        help_texts = {
            'excerpt': 'This appears in previews and search results (auto-generated if left blank)',
            'featured_image': 'Recommended size: 1200x630px (will be auto-resized)',
            'meta_description': 'Brief description for search engines (160 characters max)',
            'tags': 'Select relevant tags for better discoverability',
        }
    
    def clean_title(self):
        """Validate title"""
        title = self.cleaned_data.get('title')
        if len(title) < 10:
            raise ValidationError('Title must be at least 10 characters long.')
        return title
    
    def clean_content(self):
        """Validate content"""
        content = self.cleaned_data.get('content')
        if len(content) < 50:
            raise ValidationError('Content must be at least 50 characters long.')
        return content
    
    def clean_featured_image(self):
        """Validate image size"""
        image = self.cleaned_data.get('featured_image')
        if image:
            # Check file size (max 5MB)
            if image.size > 5 * 1024 * 1024:
                raise ValidationError('Image file size must be less than 5MB.')
        return image


class CommentForm(forms.ModelForm):
    """Form for adding comments"""
    
    class Meta:
        model = Comment
        fields = ['content']
        
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Write your comment...',
                'rows': 3
            })
        }
        
        labels = {
            'content': ''
        }
    
    def clean_content(self):
        """Validate comment content"""
        content = self.cleaned_data.get('content')
        if len(content) < 2:
            raise ValidationError('Comment must be at least 2 characters long.')
        if len(content) > 1000:
            raise ValidationError('Comment must be less than 1000 characters.')
        return content


class NewsletterForm(forms.ModelForm):
    """Form for newsletter subscription"""
    
    class Meta:
        model = Newsletter
        fields = ['email']
        
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'newsletter-input',
                'placeholder': 'Enter your email',
                'required': True
            })
        }
        
        labels = {
            'email': ''
        }
    
    def clean_email(self):
        """Validate email"""
        email = self.cleaned_data.get('email')
        # Additional email validation if needed
        return email.lower()


class ContactMessageForm(forms.ModelForm):
    """Form for contact messages"""
    
    class Meta:
        model = ContactMessage
        fields = ['name', 'email', 'subject', 'message']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Your name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'your.email@example.com'
            }),
            'subject': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Subject'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Your message...',
                'rows': 6
            })
        }
    
    def clean_message(self):
        """Validate message"""
        message = self.cleaned_data.get('message')
        if len(message) < 10:
            raise ValidationError('Message must be at least 10 characters long.')
        return message


class SearchForm(forms.Form):
    """Form for search functionality"""
    
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'search-input',
            'placeholder': 'Search posts...',
            'type': 'search'
        })
    )
    
    category = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    tag = forms.ModelChoiceField(
        queryset=None,  # Will be set in __init__
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category, Tag
        self.fields['category'].queryset = Category.objects.all()
        self.fields['tag'].queryset = Tag.objects.all()