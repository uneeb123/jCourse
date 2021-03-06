
# Shortcuts
from django.shortcuts import render, redirect, get_object_or_404
from django.http import Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout

# Mimetypes for images
from mimetypes import guess_type

# App Models
from app.models import *
from app.course_info import *
from app.context_processor import *
from app.forms import *
from app.campusnet_login import *
from app.cache import *

def home(request):
    context = {
        "page": "home",
        'user_auth': user_authenticated(request),
        'categories': MAJOR_TYPES
    }
    # Get courses
    context = dict(context.items() + get_timeline_context().items())

    return render(request, "pages/home.html", context)

def course_page(request, slug):
    course = get_object_or_404(Course, slug=slug)
    context = {
        "page": "course",
        "page_title": course.name,
        'user_auth': user_authenticated(request)
    }
    context = dict(context.items() + course_page_context(request, course).items())

    return render(request, "pages/course.html", context)

@login_required
def vote_course(request):
    context = {}
    if request.method != 'POST':
        raise Http404
    user = get_object_or_404(jUser, id=request.user.id)

    form = VoteCourseForm(request.POST)
    if not form.is_valid():
        raise Http404

    course = form.cleaned_data['course']
    rating_value = form.cleaned_data['rating_value']
    rating_type = form.cleaned_data['rating_type']

    if rating_type != PROFESSOR_R:
        ratings = Rating.objects.filter(user= user, course= course, rating_type= rating_type)
        if len(ratings) == 0:
            rating = Rating(user= user, course= course, rating= rating_value, rating_type= rating_type)
            rating.save()
        else:
            rating = ratings[0]
            rating.rating = rating_value
            rating.save()
    else:
        prof = form.cleaned_data['prof']
        ratings = Professor_Rating.objects.filter(user= user, course= course, rating_type= rating_type, prof=prof)
        if len(ratings) == 0:
            rating = Professor_Rating(user= user, course= course, rating= rating_value, rating_type= rating_type, prof=prof)
            rating.save()
        else:
            rating = ratings[0]
            rating.rating = rating_value
            rating.save()


    if rating_type == OVERALL_R:
        mark_timeline_cache()

    return redirect(form.cleaned_data['url'])


def get_course_image(request, slug):
    course = get_object_or_404(Course, slug=slug)
    if not course.image:
        raise Http404

    content_type = guess_type(course.image.name)
    return HttpResponse(course.image, mimetype=content_type)

def submit_comment(request):
    if request.method != 'POST':
        raise Http404

    form = SubmitCommentForm(request.POST)
    if not form.is_valid():
        raise Http404

    course = form.cleaned_data['course']

    comment_text = form.cleaned_data['comment']
    comment = Comment(course= course, comment= comment_text)
    comment.save()

    details = CommentDetails(comment=comment)
    if not form.cleaned_data['anonymous']:
        user = jUser.objects.get(id= request.user.id)
        details.posted_by = user
    details.save()

    return redirect(form.cleaned_data['url'])

def all_comments(request):
    context = {
        'page': 'all_comments',
        'user_auth': user_authenticated(request)
    }

    current_user = None
    if request.user.is_authenticated():
        current_user = jUser.objects.get(id=request.user.id)

    comments = Comment.objects.all()
    context['comments'] = []
    for comment in comments:
        context['comments'].append( comment_context(comment, request, current_user) )

    return render(request, 'pages/comments.html', context)


def compare_next(request, slug1=""):
    context = {
        "page": "compare",
        'user_auth': user_authenticated(request),
        'categories': MAJOR_TYPES
    }
    # Get courses
    context = dict(context.items() + get_timeline_context().items())

    message = ""
    if not slug1:
        message = "Select a course that you want to compare by clicking it's name"
    else:
        course1 = get_object_or_404(Course, slug=slug1)
        message = "You selected course '" + course1.name + "'(<a href='/compare_course/'>go back</a>). Select the course that you want to compare it with"
    context['success'] = message

    return render(request, "pages/home.html", context)


def compare(request, slug1, slug2):
    context = {
        "page": "compare",
        'user_auth': user_authenticated(request)
    }
    course1 = get_object_or_404(Course, slug=slug1)
    course2 = get_object_or_404(Course, slug=slug2)
    context['course1'] = course_page_context(request, course1)
    context['course2'] = course_page_context(request, course2)

    return render(request, "pages/compare.html", context)

@login_required
def submit_comment_upvote(request):
    if request.method != 'POST' or not 'comment_id' in request.POST \
        or not request.POST['comment_id']:
            raise Http404

    comment = get_object_or_404(Comment, id=request.POST['comment_id'])
    details = CommentDetails.objects.get_or_create(comment=comment)[0]

    user = jUser.objects.get(id=request.user.id)
    votes = CommentDetails.objects.filter(comment=comment, upvoted_by=user) | \
        CommentDetails.objects.filter(comment=comment, downvoted_by=user)
    if votes:
        raise Http404

    details.upvoted_by.add(user)

    return HttpResponse()

@login_required
def submit_comment_downvote(request):
    if request.method != 'POST' or not 'comment_id' in request.POST \
        or not request.POST['comment_id']:
            raise Http404

    comment = get_object_or_404(Comment, id=request.POST['comment_id'])
    details = CommentDetails.objects.get_or_create(comment=comment)[0]

    user = jUser.objects.get(id=request.user.id)
    votes = CommentDetails.objects.filter(comment=comment, upvoted_by=user) | \
        CommentDetails.objects.filter(comment=comment, downvoted_by=user)
    if votes:
        raise Http404

    details.downvoted_by.add(user)

    return HttpResponse()


def about_page(request):
    context = {
        "page": "about",
        'user_auth': user_authenticated(request)
    }

    return render(request, "pages/about.html", context)

def disclaimer_page(request):
    context = {
        "page": "disclaimer",
        'user_auth': user_authenticated(request)
    }

    return render(request, "pages/disclaimer.html", context)

##### User authentication here on

def login_action(request):
    context = {}
    if request.method != 'POST':
        raise Http404

    form = LoginForm(request.POST)
    if not form.is_valid():
        raise Http404

    login_username = form.cleaned_data['username']
    if not login_success(login_username, form.cleaned_data['password']):
        context['error'] = "Wrong username or password!"
        return render(request, "pages/login_page.html", context)
    
    users = jUser.objects.filter(username=login_username)
    if len(users) == 0:
        user = jUser.objects.create_user(username=login_username, password="1234")
        user.save()

    user = authenticate(username=login_username, password="1234")
    if user is not None:
        if user.is_active:
            login(request, user)
            if 'login' in request.META.get('HTTP_REFERER'):
                return redirect('/')
            return redirect(request.META.get('HTTP_REFERER'))
        else:
            context['error'] = "Invalid user! Please try again! The account may not be activated!"
            return render(request, "pages/login_page.html", context)
    else:
        context['error'] = "Invalid login! Please try again!"
        return render(request, "pages/login_page.html", context)

    raise Http404

@login_required
def logout_action(request):
    if request.user:
        user = request.user
    logout(request)
    return redirect(request.META.get('HTTP_REFERER'))
