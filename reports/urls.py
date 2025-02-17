from django.urls import path
from .views import (
    issue_list,
    issue_detail,
    report_issue,
    admin_dashboard,
    admin_login,
    update_issue_status,
    vote_issue,
    add_comment,
    delete_issue,
    forward_to_government,
    search_issue
)

urlpatterns = [
    path("", issue_list, name="issue_list"),
     path('issues/', issue_list, name='issue_list'),
    path('admin/login/', admin_login, name='admin_login'),  # Login page for the admin
    path("admin/dashboard/", admin_dashboard, name="admin_dashboard"),  # Admin dashboard
    path("<int:issue_id>/", issue_detail, name="issue_detail"),  # Issue detail page
    path("report/", report_issue, name="report_issue"),  # Report an issue page
    path("admin/update/<int:issue_id>/", update_issue_status, name="update_issue_status"),  # Admin updates issue status
    path("vote/<int:issue_id>/", vote_issue, name="vote_issue"),  # User voting on an issue
    path("issues/<int:issue_id>/comment/", add_comment, name="add_comment"),  # Adding a comment to an issue
    path("admin/delete/<int:issue_id>/", delete_issue, name="delete_issue"),
    path("admin/forward/<int:issue_id>/", forward_to_government, name="forward_to_government"),
    path('search_issue/', search_issue, name='search_issue'),
]