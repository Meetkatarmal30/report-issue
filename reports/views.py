from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db import models
from django.contrib.auth.models import User  # Example, if you're using User model
from django.utils import timezone
from .models import Issue
from django.http import HttpResponseBadRequest
from .models import Issue, Comment, Vote
from .forms import IssueForm, CommentForm
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
from django.shortcuts import render, redirect
from django.core.mail import send_mail
import reports.views as views
from django.utils.timezone import now
import json
import uuid



VULGAR_WORDS = ['badword1', 'badword2', 'badword3']


def issues_view(request):
    # Fetch the issues from the database
    issues = Issue.objects.all()  # Replace with your actual model
    
    # Convert issues to a JSON-compatible format
    issues_data = [
        {
            'id': issue.id,
            'title': issue.title,
            'description': issue.description,
            'lat': issue.lat,
            'lng': issue.lng,
        }
        for issue in issues if issue.lat and issue.lng
    ]
    
    issues_json = json.dumps(issues_data)  # Convert to JSON format

    return render(request, 'your_template.html', {'issues_json': issues_json})


def add_comment(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    
    if request.method == 'POST':
        comment_text = request.POST.get('text')
        
        # For anonymous commenting, we'll create a guest user-like model
        # Here we can store comments with a "guest" name or similar
        username = request.POST.get('username', 'Guest')  # Default to 'Guest' if no name provided
        
        # Create and save the new comment
        comment = Comment(user=username, text=comment_text, issue=issue)
        comment.save()
        
        # Redirect to the issue detail page after adding the comment
        return redirect('issue_detail', issue_id=issue.id)
    
    return render(request, 'reports/issue_detail.html', {'issue': issue})

def forward_to_government(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    issue.status = 'Sent to Government'
    issue.save()

    # Send email to government official
    send_mail(
        f"Issue Forwarded: {issue.title}",
        f"Issue Description: {issue.description}\nLocation: {issue.location}",
        'from@example.com',
        ['government@example.com'],
        fail_silently=False,
    )

    return redirect('admin_dashboard')


def issue_list(request):
    issues = Issue.objects.all()  # Get all issues
    issues_json = json.dumps([{
    'id': issue.id,
    'title': issue.title,
    'status':issue.status,
    'description': issue.description,
    'location': issue.location,
    'lat': issue.lat,
    'lng': issue.lng,
    } for issue in issues])

    return render(request, 'reports/issue_list.html', {'issues': issues, 'issues_json': issues_json})



def issue_detail(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    comment_form = CommentForm()
    return render(request, "reports/issue_detail.html", {"issue": issue, "comment_form": comment_form})



def report_issue(request):
    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        category = request.POST.get("category")
        location = request.POST.get("location")  # User-entered location
        lat = request.POST.get("lat")  # Ensure it matches frontend key
        lng = request.POST.get("lng")  # Ensure it matches frontend key
        image = request.FILES.get("image")

        # Debugging: Print received data
        print("Received Data:", title, description, category, location, lat, lng, image)

        if not lat or not lng:
            return JsonResponse({"error": "Latitude or Longitude is missing"}, status=400)

        # Create a unique token for the issue
        token = uuid.uuid4().hex

        # Save to database
        issue = Issue.objects.create(
            title=title,
            description=description,
            category=category,
            location=location if location else f"{lat}, {lng}",  # Use lat/lng if location is empty
            lat=lat,
            lng=lng,
            image=image,
            token=token  # Store the unique token
        )

        return JsonResponse({"message": "Issue reported successfully!", "issue_id": issue.id, "token": token})

    return render(request, "reports/report_issue.html")



# def report_issue(request):
#     if request.method == 'POST':
#         form = IssueForm(request.POST, request.FILES)
#         if form.is_valid():
#             issue = form.save(commit=False)
#             issue.status = 'Pending'  # Set default status
#             if request.user.is_authenticated:
#                 issue.user = request.user
#             issue.save()
#             return JsonResponse({'message': 'Issue reported successfully'}, status=200)
#     else:
#         form = IssueForm()
#     return render(request, 'reports/report_issue.html', {'form': form})

# views.py


class CommentView(models.Model):
    issue = models.ForeignKey('Issue', on_delete=models.CASCADE, related_name='comment_view')
    user = models.CharField(max_length=100)  
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)  # Keep only this

    def __str__(self):
        return f'Comment by {self.user} on {self.issue.title}'


def delete_issue(request, issue_id):
    issue = get_object_or_404(Issue, id=issue_id)
    issue.delete()
    return redirect('issue_list')  # Redirect to issue list after deletion


def vote_issue(request, issue_id):
    if request.method == 'POST':
        vote_type = request.POST.get('vote_type')  # Get the vote type (Upvote or Downvote)

        # Check if vote_type is missing
        if not vote_type:
            return JsonResponse({"error": "Vote type is missing."}, status=400)

        issue = get_object_or_404(Issue, id=issue_id)

        # Identify user (use session or IP if not logged in)
        if request.user.is_authenticated:
            user_identifier = request.user
            ip_address = None
        else:
            user_identifier = None
            ip_address = request.META.get('REMOTE_ADDR')

        # Check if the user (or IP) has already voted
        if Vote.objects.filter(issue=issue, user=user_identifier, ip_address=ip_address).exists():
            return JsonResponse({"error": "You have already voted on this issue."}, status=400)

        # Create or update the vote
        vote, created = Vote.objects.get_or_create(
            issue=issue,
            user=user_identifier,
            ip_address=ip_address,
            defaults={"vote_type": vote_type}
        )

        # Update vote type if it was changed
        if not created and vote.vote_type != vote_type:
            vote.vote_type = vote_type
            vote.save()

        # Update aggregated vote count
        upvotes = issue.votes.filter(vote_type="Upvote").count()
        downvotes = issue.votes.filter(vote_type="Downvote").count()
        issue.votes_count = upvotes - downvotes
        issue.save()

        return redirect('issue_detail', issue_id=issue_id)

    return JsonResponse({"error": "Invalid request method."}, status=405)


# Define the admin_dashboard view (you can customize it)
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')

def admin_login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('admin_dashboard')  # Redirect to admin dashboard
    else:
        form = AuthenticationForm()
    return render(request, 'admin_login.html', {'form': form})

# Define the update_issue_status view (you can customize it)
def update_issue_status(request, issue_id):
    # Add logic to update issue status
    return render(request, 'update_issue_status.html', {'issue_id': issue_id})


def get_issue_data():
    issues = Issue.objects.all()  # Get all issues from the database
    cleaned_issues = []
    
    for issue in issues:
        lat, lng = None, None
        # If the location is stored as a string like "lat,lng"
        if issue.location:
            try:
                lat, lng = map(float, issue.location.split(','))
            except ValueError:
                pass  # Skip invalid location data
        
        # If lat and lng are still None, use default or skip
        if lat is None or lng is None:
            continue  # Skip this issue or set default values
            
        cleaned_issues.append({
            'id': issue.id,
            'title': issue.title,
            'description': issue.description,
            'lat': lat,
            'lng': lng,
        })
    
    return cleaned_issues


def search_issue(request):
    issues = None
    if 'token' in request.GET:
        token = request.GET['token']
        issues = Issue.objects.filter(token=token)
    
    return render(request, 'reports/search_issue.html', {'issues': issues})