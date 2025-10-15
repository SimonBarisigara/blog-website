from django.urls import reverse
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.utils.text import slugify
from django.core.validators import FileExtensionValidator
from PIL import Image
import math


# Category Model
class Category(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    date_posted = models.DateTimeField(default=timezone.now)
    author = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('category-posts', kwargs={'slug': self.slug})


# Tag Model
class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('tag-posts', kwargs={'slug': self.slug})


# Updated Post Model
class Post(models.Model):
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('published', 'Published'),
        ('scheduled', 'Scheduled'),
    ]

    # Basic Information
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(max_length=300, blank=True, help_text="Brief summary for previews")
    
    # Media
    featured_image = models.ImageField(
        upload_to='post_images/%Y/%m/%d/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'webp'])],
        help_text="Recommended size: 1200x630px"
    )
    
    # Categorization
    category = models.ForeignKey(
        Category,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='posts'
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name='posts')
    
    # Author & Dates
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='posts')
    date_posted = models.DateTimeField(default=timezone.now)
    date_updated = models.DateTimeField(auto_now=True)
    publish_date = models.DateTimeField(null=True, blank=True, help_text="Schedule post for future")
    
    # Status & Settings
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')
    is_featured = models.BooleanField(default=False, help_text="Show in featured section")
    is_pinned = models.BooleanField(default=False, help_text="Pin to top of list")
    allow_comments = models.BooleanField(default=True)
    
    # Engagement Metrics
    views_count = models.IntegerField(default=0)
    reading_time = models.IntegerField(default=5, help_text="Estimated reading time in minutes")
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True, help_text="For search engines")
    meta_keywords = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ['-is_pinned', '-date_posted']
        indexes = [
            models.Index(fields=['-date_posted']),
            models.Index(fields=['status', '-date_posted']),
            models.Index(fields=['author', '-date_posted']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto-generate slug from title
        if not self.slug:
            self.slug = slugify(self.title)
            # Ensure unique slug
            original_slug = self.slug
            counter = 1
            while Post.objects.filter(slug=self.slug).exists():
                self.slug = f"{original_slug}-{counter}"
                counter += 1
        
        # Auto-generate excerpt from content if not provided
        if not self.excerpt and self.content:
            self.excerpt = self.content[:250] + "..." if len(self.content) > 250 else self.content
        
        # Calculate reading time (average 200 words per minute)
        if self.content:
            word_count = len(self.content.split())
            self.reading_time = max(1, math.ceil(word_count / 200))
        
        # Auto-generate meta description
        if not self.meta_description:
            self.meta_description = self.excerpt[:160] if self.excerpt else self.content[:160]
        
        super().save(*args, **kwargs)
        
        # Resize featured image
        if self.featured_image:
            self.resize_image()

    def resize_image(self):
        """Resize featured image to optimize storage"""
        try:
            img = Image.open(self.featured_image.path)
            
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # Resize if larger than 1200px wide
            if img.width > 1200:
                output_size = (1200, int(img.height * (1200 / img.width)))
                img.thumbnail(output_size, Image.Resampling.LANCZOS)
                img.save(self.featured_image.path, quality=85, optimize=True)
        except Exception as e:
            print(f"Error resizing image: {e}")

    def get_absolute_url(self):
        return reverse('post-detail', kwargs={'pk': self.pk})

    def increment_views(self):
        """Increment view count"""
        self.views_count += 1
        self.save(update_fields=['views_count'])

    @property
    def total_likes(self):
        """Get total number of likes"""
        return self.likes.count()

    @property
    def total_comments(self):
        """Get total number of comments"""
        return self.comments.filter(is_approved=True).count()

    @property
    def is_published(self):
        """Check if post is published"""
        return self.status == 'published'

    def get_related_posts(self, limit=3):
        """Get related posts by category and tags"""
        related = Post.objects.filter(
            status='published'
        ).exclude(id=self.id)
        
        # Filter by same category
        if self.category:
            related = related.filter(category=self.category)
        
        # Order by common tags, then by date
        return related.order_by('-date_posted')[:limit]


# Comment Model
class Comment(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=True)
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='replies'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', '-created_at']),
        ]

    def __str__(self):
        return f'Comment by {self.author.username} on {self.post.title}'

    @property
    def is_reply(self):
        """Check if this is a reply to another comment"""
        return self.parent is not None


# Like Model
class Like(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='liked_posts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('post', 'user')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['post', 'user']),
        ]

    def __str__(self):
        return f'{self.user.username} likes {self.post.title}'


# Newsletter Model
class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    unsubscribe_token = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['-subscribed_at']

    def __str__(self):
        return self.email

    def save(self, *args, **kwargs):
        # Generate unsubscribe token
        if not self.unsubscribe_token:
            import uuid
            self.unsubscribe_token = str(uuid.uuid4())
        super().save(*args, **kwargs)


# User Follow System (Optional - for following authors)
class Follow(models.Model):
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.follower.username} follows {self.following.username}'


# Reading List / Bookmarks (Optional)
class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='bookmarked_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} bookmarked {self.post.title}'


# Contact/Feedback Model (For contact forms)
class ContactMessage(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    replied = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Message from {self.name} - {self.subject}'