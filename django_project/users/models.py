from django.db import models
from django.contrib.auth.models import User
from PIL import Image
import os


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    image = models.ImageField(default='profile_pics/default.jpg', upload_to='profile_pics', blank=True)
    bio = models.TextField(max_length=500, blank=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(max_length=200, blank=True)
    
    def __str__(self):
        return f'{self.user.username} Profile'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        # Only resize if image exists and has a path (not default)
        if self.image and hasattr(self.image, 'path'):
            try:
                # Check if file actually exists
                if os.path.exists(self.image.path):
                    img = Image.open(self.image.path)
                    if img.height > 300 or img.width > 300:
                        output_size = (300, 300)
                        img.thumbnail(output_size)
                        img.save(self.image.path)
            except (FileNotFoundError, IOError, OSError) as e:
                # Handle missing or invalid image files gracefully
                pass