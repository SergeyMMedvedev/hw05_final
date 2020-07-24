from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Group, Comment, Follow
from .forms import PostForm, CommentForm
from datetime import datetime as dt
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator


User = get_user_model()


def index(request):
    post_list = Post.objects.order_by("-pub_date").all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        "index.html",
        {"page": page,
         "paginator": paginator,
         "page_number": page_number}
    )


def group_posts(request, slug):
    group = get_object_or_404(Group, slug=slug)
    post_list = group.posts.all().order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(
        request,
        "group.html",
         {"group": group,
          "page": page,
          "paginator": paginator}
    )


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST or None, files=request.FILES or None)
        if form.is_valid():
            created_post = form.save(commit=False)
            created_post.author = request.user
            created_post.pub_date = dt.now()
            created_post.save()
            return redirect("/")

        return render(request, "index.html", {'form': form})
    form = PostForm()
    return render(request, "new_post.html", {'form': form})


def profile(request, username):
    profile = get_object_or_404(User, username=username)
    post_list = Post.objects.filter(author=profile.id).order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    posts_count = post_list.count()
    num_of_follow = profile.follower.count()
    num_of_followers = profile.following.count()
    try:
        user = User.objects.get(username=request.user)
    except User.DoesNotExist:
        user = None
    authors = []
    if user:
        for item in user.follower.all():
            authors.append(item.author)
    following = False
    if profile in authors:
        following = True
    return render(request, 'profile.html',
                  {"page": page,
                   "paginator": paginator,
                   "posts_count": posts_count,
                   "profile": profile,
                   "following": following,
                   "num_of_follow": num_of_follow,
                   "num_of_followers": num_of_followers,
                   }
                  )


def post_view(request, username, post_id):
    author = User.objects.get(username=username)
    post_list = Post.objects.filter(author=author.id)
    posts_count = post_list.count()
    post = Post.objects.get(pk=post_id)
    form = CommentForm()
    comments = Comment.objects.filter(post=post).order_by("-created")
    num_of_follow = author.follower.count()
    num_of_followers = author.following.count()
    return render(request, 'post.html',
                  {"posts_count": posts_count,
                   "author": author,
                   "post": post,
                   "form": form,
                   "items": comments,
                   "num_of_follow": num_of_follow,
                   "num_of_followers": num_of_followers,
                   }
                  )


def post_edit(request, username, post_id):
    if request.user.username != username:
        return redirect(f'/{username}/{post_id}/')
    else:
        profile = get_object_or_404(User, username=username)
        edit_post = get_object_or_404(Post, pk=post_id, author=profile)
        form = PostForm(request.POST or None, files=request.FILES or None,
                        instance=edit_post)
        if request.method == 'POST':

            if form.is_valid():
                edit_post.text = form.cleaned_data['text']
                edit_post.group = form.cleaned_data['group']
                edit_post.save()
                return redirect(f'/{username}/{post_id}')

            return render(request, 'index.html', {'form': form})

        form = PostForm(initial={
            'text': edit_post.text,
            'group': edit_post.group,
        })
        return render(request, 'new_post.html', {'form': form,
                                                 'action_edit_post': True,
                                                 'username': username,
                                                 'post_id': post_id,
                                                 'post': edit_post
                                                 })


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


@login_required()
def add_comment(request, username, post_id):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            created_comment = form.save(commit=False)
            created_comment.author = request.user
            created_comment.created = dt.now()
            created_comment.post = Post.objects.get(pk=post_id)
            created_comment.save()
            return redirect(f"/{username}/{post_id}/")
        return render(request, "index.html", {'form': form})
    return redirect(f"/{username}/{post_id}/")


@login_required
def follow_index(request):
    user = User.objects.get(pk=request.user.id)
    authors = []
    for item in user.follower.all():
        authors.append(item.author.id)
    post_list = Post.objects.filter(author__in=authors).order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    page = paginator.get_page(page_number)
    return render(request,
                  "follow.html",
                  {"page": page,
                   "paginator": paginator,
                   "page_number": page_number})


@login_required
def profile_follow(request, username):
    if (request.user.username != username and
        Follow.objects.filter(
            user=User.objects.get(username=request.user),
            author=User.objects.get(username=username)).count() == 0):
        subscribe = Follow.objects.create(
            user=request.user,
            author=User.objects.get(username=username)
        )
        subscribe.save()
    return redirect(f'/{username}/')


@login_required
def profile_unfollow(request, username):
    subscribe = Follow.objects.filter(
        user=request.user,
        author=User.objects.get(username=username)
    )
    subscribe.delete()
    return redirect(f'/{username}/')
