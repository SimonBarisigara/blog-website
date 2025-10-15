from django.urls import path
from . import views

urlpatterns = [
    # Home & Main Views
    path('', views.PostListView.as_view(), name='blog-home'),
    path('about/', views.about, name='blog-about'),
    path('search/', views.search, name='blog-search'),
    
    # Post CRUD
    path('post/new/', views.PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('post/<int:pk>/update/', views.PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post-delete'),
    
    # User Posts
    path('user/<str:username>/', views.UserPostListView.as_view(), name='user-posts'),
    
    # Category & Tags
    path('category/<slug:slug>/', views.CategoryPostListView.as_view(), name='category-posts'),
    path('tag/<slug:slug>/', views.TagPostListView.as_view(), name='tag-posts'),
    
    # Comments
    path('post/<int:pk>/comment/', views.add_comment, name='add-comment'),
    path('comment/<int:pk>/delete/', views.delete_comment, name='delete-comment'),
    
    # Likes & Bookmarks
    path('post/<int:pk>/like/', views.toggle_like, name='toggle-like'),
    path('post/<int:pk>/bookmark/', views.toggle_bookmark, name='toggle-bookmark'),
    path('bookmarks/', views.bookmarks_list, name='bookmarks-list'),
    
    # Follow System
    path('user/<str:username>/follow/', views.toggle_follow, name='toggle-follow'),
    
    # Newsletter
    path('newsletter/subscribe/', views.newsletter_subscribe, name='newsletter-subscribe'),
    path('newsletter/unsubscribe/<str:token>/', views.newsletter_unsubscribe, name='newsletter-unsubscribe'),
]