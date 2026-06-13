"""Template context processors for the attendance app."""

from .models import UserPreference

SESSION_KEY = "pref_id"


def get_current_user(request):
    """Return the UserPreference for the name active in this session, or None."""
    pref_id = request.session.get(SESSION_KEY)
    if pref_id:
        return UserPreference.objects.filter(pk=pref_id).first()
    return None


def user_preference(request):
    """Expose the active user (name + WFH flag + salary) to all templates."""
    pref = get_current_user(request)
    return {
        "preference": pref,
        "user_name": pref.name if pref else "",
        # Only show WFH when the active user enabled it.
        "show_wfh": pref.show_wfh if pref else False,
    }
