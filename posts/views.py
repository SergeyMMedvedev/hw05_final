from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect

from .forms import PostForm, CommentForm
from .models import Post, Group, Follow


User = get_user_model()


def index(request):
    post_list = Post.objects.select_related(
        'author').order_by("-pub_date").all()
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
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
    page_number = request.GET.get("page")
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
    form = PostForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        created_post = form.save(commit=False)
        created_post.author = request.user
        created_post.save()
        return redirect("index")
    return render(request, "new_post.html", {"form": form})


def profile(request, username):
    profile = get_object_or_404(User, username=username)
    post_list = profile.posts.all().order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    posts_count = post_list.count()
    num_of_follow = profile.follower.count()
    num_of_followers = profile.following.count()
    following = False
    if (request.user.__str__() != 'AnonymousUser' and
            request.user.follower.filter(author=profile.id).exists()):
        following = True
    return render(request, "profile.html",
                  {"page": page,
                   "paginator": paginator,
                   "posts_count": posts_count,
                   "profile": profile,
                   "following": following,
                   "num_of_follow": num_of_follow,
                   "num_of_followers": num_of_followers,
                   "user": request.user.username
                   }
                  )


def post_view(request, username, post_id):
    author = get_object_or_404(User, username=username)
    post_list = author.posts.all()
    posts_count = post_list.count()
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm()
    comments = post.comments.all().order_by("-created")
    num_of_follow = author.follower.count()
    num_of_followers = author.following.count()
    return render(request, "post.html",
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
        return redirect(f"/{username}/{post_id}/")
    edit_post = get_object_or_404(Post, pk=post_id, author=request.user)
    form = PostForm(request.POST or None, files=request.FILES or None,
                    instance=edit_post)
    if form.is_valid():
        edit_post.save()
        return redirect(f"/{username}/{post_id}")
    form = PostForm(initial={
        "text": edit_post.text,
        "group": edit_post.group,
    })
    return render(request, "new_post.html", {"form": form,
                                             "action_edit_post": True,
                                             "username": username,
                                             "post_id": post_id,
                                             "post": edit_post
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
    form = CommentForm(request.POST or None)
    if form.is_valid():
        created_comment = form.save(commit=False)
        created_comment.author = request.user
        created_comment.post = get_object_or_404(Post, pk=post_id)
        created_comment.save()
        return redirect("post", post_id=post_id, username=username)
    return redirect("post", post_id=post_id, username=username)


@login_required
def follow_index(request):
    user_follows = Follow.objects.select_related(
        'author').filter(user=request.user).values_list("author")
    post_list = Post.objects.filter(
        author__in=user_follows).order_by("-pub_date")
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get("page")
    page = paginator.get_page(page_number)
    return render(request,
                  "follow.html",
                  {"page": page,
                   "paginator": paginator,
                   "page_number": page_number})


@login_required
def profile_follow(request, username):
    if request.user.username != username:
        Follow.objects.get_or_create(
            user=request.user,
            author=User.objects.get(username=username)
        )
    return redirect("profile", username=username)


@login_required
def profile_unfollow(request, username):
    subscribe = Follow.objects.filter(
        user=request.user,
        author=get_object_or_404(User, username=username)
    )
    subscribe.delete()
    return redirect("profile", username=username)
