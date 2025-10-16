from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.utils import timezone
from datetime import timedelta
from .models import Post, Category, Tag, Comment, Like, Newsletter, Bookmark, Follow
from .forms import PostForm, CommentForm, NewsletterForm
# ========== HOME & LIST VIEWS ==========

class PostListView(ListView):
    model = Post
    template_name = 'blog/home.html'
    context_object_name = 'posts'
    paginate_by = 6
    
    def get_queryset(self):
        queryset = Post.objects.filter(status='published').select_related(
            'author', 'author__profile', 'category'
        ).prefetch_related('tags', 'likes')
        
        # Search functionality
        search_query = self.request.GET.get('q')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(excerpt__icontains=search_query)
            )
        
        # Category filter
        category_slug = self.request.GET.get('category')
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        
        # Tag filter
        tag_slug = self.request.GET.get('tag')
        if tag_slug:
            queryset = queryset.filter(tags__slug=tag_slug)
        
        # Sorting
        sort_by = self.request.GET.get('sort', '-date_posted')
        valid_sorts = {
            'newest': '-date_posted',
            'oldest': 'date_posted',
            'popular': '-views_count',
            'trending': '-likes__created_at'
        }
        queryset = queryset.order_by(valid_sorts.get(sort_by, '-date_posted'))
        
        return queryset.distinct()
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Featured post (most recent featured or pinned post)
        context['featured_post'] = Post.objects.filter(
            status='published',
            is_featured=True
        ).select_related('author', 'author__profile').first()
        
        # Trending posts (last 7 days, ordered by views and likes)
        week_ago = timezone.now() - timedelta(days=7)
        context['trending_posts'] = Post.objects.filter(
            status='published',
            date_posted__gte=week_ago
        ).annotate(
            engagement=Count('likes') + Count('comments')
        ).order_by('-engagement', '-views_count')[:5]
        
        # Categories with post count
        context['categories'] = Category.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0)
        
        # Popular tags
        context['popular_tags'] = Tag.objects.annotate(
            post_count=Count('posts', filter=Q(posts__status='published'))
        ).filter(post_count__gt=0).order_by('-post_count')[:10]
        
        # Stats for hero section
        context['total_posts'] = Post.objects.filter(status='published').count()
        context['total_authors'] = User.objects.filter(posts__status='published').distinct().count()
        
        return context


# ========== USER POSTS VIEW ==========

class UserPostListView(ListView):
    model = Post
    template_name = 'blog/user_posts.html'
    context_object_name = 'posts'
    paginate_by = 6

    def get_queryset(self):
        self.user = get_object_or_404(User, username=self.kwargs.get('username'))
        return Post.objects.filter(
            author=self.user,
            status='published'
        ).select_related('author', 'author__profile', 'category').prefetch_related(
            'tags', 'likes', 'comments'
        ).order_by('-date_posted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['post_author'] = self.user
        context['total_posts'] = self.get_queryset().count()
        context['total_views'] = sum(post.views_count for post in self.get_queryset())
        context['total_likes'] = Like.objects.filter(post__author=self.user).count()
        
        # Check if current user follows this author
        if self.request.user.is_authenticated:
            context['is_following'] = Follow.objects.filter(
                follower=self.request.user,
                following=self.user
            ).exists()
        
        # Follower/Following counts
        context['followers_count'] = Follow.objects.filter(following=self.user).count()
        context['following_count'] = Follow.objects.filter(follower=self.user).count()
        
        return context


# ========== CATEGORY & TAG VIEWS ==========

class CategoryPostListView(ListView):
    model = Post
    template_name = 'blog/category_posts.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        self.category = get_object_or_404(Category, slug=self.kwargs.get('slug'))
        return Post.objects.filter(
            category=self.category,
            status='published'
        ).select_related('author', 'author__profile').order_by('-date_posted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['category'] = self.category
        return context


class TagPostListView(ListView):
    model = Post
    template_name = 'blog/tag_posts.html'
    context_object_name = 'posts'
    paginate_by = 9

    def get_queryset(self):
        self.tag = get_object_or_404(Tag, slug=self.kwargs.get('slug'))
        return Post.objects.filter(
            tags=self.tag,
            status='published'
        ).select_related('author', 'author__profile').order_by('-date_posted')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tag'] = self.tag
        return context


# ========== POST DETAIL VIEW ==========

class PostDetailView(DetailView):
    model = Post
    
    def get_queryset(self):
        return Post.objects.filter(status='published').select_related(
            'author', 'author__profile', 'category'
        ).prefetch_related(
            'tags',
            'likes',
            Prefetch('comments', queryset=Comment.objects.filter(
                is_approved=True, parent=None
            ).select_related('author', 'author__profile').prefetch_related('replies'))
        )
    
    def get_object(self):
        obj = super().get_object()
        # Increment view count (only once per session)
        session_key = f'viewed_post_{obj.pk}'
        if not self.request.session.get(session_key, False):
            obj.increment_views()
            self.request.session[session_key] = True
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.object
        
        # Check if user has liked the post
        if self.request.user.is_authenticated:
            context['user_has_liked'] = Like.objects.filter(
                post=post,
                user=self.request.user
            ).exists()
            context['user_has_bookmarked'] = Bookmark.objects.filter(
                post=post,
                user=self.request.user
            ).exists()
        
        # Related posts
        context['related_posts'] = post.get_related_posts(limit=3)
        
        # Comment form
        context['comment_form'] = CommentForm()
        
        # Comments count
        context['comments_count'] = post.comments.filter(is_approved=True).count()
        
        return context


# ========== POST CREATE/UPDATE/DELETE VIEWS ==========

class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        
        # Set status based on button clicked
        if 'save_draft' in self.request.POST:
            form.instance.status = 'draft'
            messages.success(self.request, 'Post saved as draft!')
        else:
            form.instance.status = 'published'
            messages.success(self.request, 'Post published successfully!')
        
        return super().form_valid(form)


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/post_form.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        
        # Update status based on button clicked
        if 'save_draft' in self.request.POST:
            form.instance.status = 'draft'
            messages.success(self.request, 'Changes saved as draft!')
        elif 'publish' in self.request.POST:
            form.instance.status = 'published'
            messages.success(self.request, 'Post updated and published!')
        else:
            messages.success(self.request, 'Post updated successfully!')
        
        return super().form_valid(form)

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Post
    success_url = '/'

    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author
    
    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Post deleted successfully!')
        return super().delete(request, *args, **kwargs)


# ========== COMMENT VIEWS ==========

@login_required
@require_POST
def add_comment(request, pk):
    """Add a comment to a post"""
    post = get_object_or_404(Post, pk=pk, status='published')
    
    if not post.allow_comments:
        return JsonResponse({'error': 'Comments are disabled for this post'}, status=403)
    
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.post = post
        comment.author = request.user
        
        # Handle reply to another comment
        parent_id = request.POST.get('parent_id')
        if parent_id:
            comment.parent = get_object_or_404(Comment, pk=parent_id)
        
        comment.save()
        messages.success(request, 'Comment added successfully!')
        return redirect('post-detail', pk=post.pk)
    
    messages.error(request, 'Error adding comment. Please try again.')
    return redirect('post-detail', pk=post.pk)


@login_required
@require_POST
def delete_comment(request, pk):
    """Delete a comment"""
    comment = get_object_or_404(Comment, pk=pk)
    post_pk = comment.post.pk
    
    if request.user == comment.author or request.user == comment.post.author:
        comment.delete()
        messages.success(request, 'Comment deleted successfully!')
    else:
        messages.error(request, 'You do not have permission to delete this comment.')
    
    return redirect('post-detail', pk=post_pk)


# ========== LIKE/UNLIKE VIEWS ==========

@login_required
@require_POST
def toggle_like(request, pk):
    """Toggle like on a post"""
    post = get_object_or_404(Post, pk=pk)
    like, created = Like.objects.get_or_create(post=post, user=request.user)
    
    if not created:
        like.delete()
        liked = False
    else:
        liked = True
    
    return JsonResponse({
        'liked': liked,
        'total_likes': post.total_likes
    })


# ========== BOOKMARK VIEWS ==========

@login_required
@require_POST
def toggle_bookmark(request, pk):
    """Toggle bookmark on a post"""
    post = get_object_or_404(Post, pk=pk)
    bookmark, created = Bookmark.objects.get_or_create(post=post, user=request.user)
    
    if not created:
        bookmark.delete()
        bookmarked = False
        messages.success(request, 'Removed from bookmarks!')
    else:
        bookmarked = True
        messages.success(request, 'Added to bookmarks!')
    
    return JsonResponse({
        'bookmarked': bookmarked
    })


@login_required
def bookmarks_list(request):
    """View user's bookmarked posts"""
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        'post', 'post__author', 'post__author__profile'
    ).order_by('-created_at')
    
    return render(request, 'blog/bookmarks.html', {'bookmarks': bookmarks})


# ========== FOLLOW VIEWS ==========

@login_required
@require_POST
def toggle_follow(request, username):
    """Toggle follow on a user"""
    user_to_follow = get_object_or_404(User, username=username)
    
    if user_to_follow == request.user:
        return JsonResponse({'error': 'You cannot follow yourself'}, status=400)
    
    follow, created = Follow.objects.get_or_create(
        follower=request.user,
        following=user_to_follow
    )
    
    if not created:
        follow.delete()
        following = False
        messages.success(request, f'Unfollowed {user_to_follow.username}')
    else:
        following = True
        messages.success(request, f'Now following {user_to_follow.username}')
    
    return JsonResponse({
        'following': following,
        'followers_count': Follow.objects.filter(following=user_to_follow).count()
    })


# ========== NEWSLETTER VIEWS ==========

@require_POST
def newsletter_subscribe(request):
    """Subscribe to newsletter"""
    form = NewsletterForm(request.POST)
    
    if form.is_valid():
        email = form.cleaned_data['email']
        newsletter, created = Newsletter.objects.get_or_create(email=email)
        
        if created:
            messages.success(request, 'Successfully subscribed to newsletter!')
            return JsonResponse({'success': True, 'message': 'Successfully subscribed!'})
        else:
            if newsletter.is_active:
                messages.info(request, 'You are already subscribed!')
                return JsonResponse({'success': False, 'message': 'Already subscribed!'})
            else:
                newsletter.is_active = True
                newsletter.save()
                messages.success(request, 'Resubscribed to newsletter!')
                return JsonResponse({'success': True, 'message': 'Resubscribed successfully!'})
    
    messages.error(request, 'Invalid email address!')
    return JsonResponse({'success': False, 'message': 'Invalid email address!'}, status=400)


def newsletter_unsubscribe(request, token):
    """Unsubscribe from newsletter"""
    newsletter = get_object_or_404(Newsletter, unsubscribe_token=token)
    newsletter.is_active = False
    newsletter.save()
    messages.success(request, 'Successfully unsubscribed from newsletter.')
    return redirect('blog-home')


# ========== ABOUT & OTHER PAGES ==========

def about(request):
    """About page with site statistics"""
    context = {
        'total_posts': Post.objects.filter(status='published').count(),
        'total_users': User.objects.filter(posts__status='published').distinct().count(),
        'total_comments': Comment.objects.filter(is_approved=True).count(),
        'total_views': sum(post.views_count for post in Post.objects.filter(status='published')),
    }
    return render(request, 'blog/about.html', context)


# ========== SEARCH VIEW ==========

def search(request):
    """Advanced search functionality"""
    query = request.GET.get('q', '')
    category_id = request.GET.get('category')
    tag_id = request.GET.get('tag')
    
    posts = Post.objects.filter(status='published')
    
    if query:
        posts = posts.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(excerpt__icontains=query) |
            Q(author__username__icontains=query)
        )
    
    if category_id:
        posts = posts.filter(category_id=category_id)
    
    if tag_id:
        posts = posts.filter(tags__id=tag_id)
    
    posts = posts.select_related('author', 'author__profile', 'category').distinct()
    
    context = {
        'posts': posts,
        'query': query,
        'categories': Category.objects.all(),
        'tags': Tag.objects.all(),
    }
    
    return render(request, 'blog/search.html', context)