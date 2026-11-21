"""
Supabase client and database operations for Job Intelligence Dashboard.
Handles authentication, profile management, and user-scoped data access.
"""
import streamlit as st
from supabase import create_client, Client


@st.cache_resource
def get_supabase_client() -> Client:
    """
    Get the Supabase client using credentials from st.secrets.
    Cached so it's only created once per app session.
    """
    url = st.secrets["supabase"]["SUPABASE_URL"]
    key = st.secrets["supabase"]["SUPABASE_KEY"]
    return create_client(url, key)


def sign_up_user(email: str, password: str):
    """
    Register a new user with Supabase Auth.
    Returns the auth response or raises an exception.
    """
    supabase = get_supabase_client()
    response = supabase.auth.sign_up({
        "email": email,
        "password": password
    })
    return response


def sign_in_user(email: str, password: str):
    """
    Sign in an existing user.
    Returns the auth response or raises an exception.
    """
    supabase = get_supabase_client()
    response = supabase.auth.sign_in_with_password({
        "email": email,
        "password": password
    })
    return response


def sign_out_user():
    """
    Sign out the current user and clear session state.
    """
    supabase = get_supabase_client()
    supabase.auth.sign_out()
    st.session_state.pop("user", None)
    st.session_state.pop("profile", None)
    st.rerun()


def get_current_user():
    """
    Get the currently authenticated user.
    Returns None if no user is signed in.
    """
    supabase = get_supabase_client()
    try:
        session = supabase.auth.get_session()
        if session:
            return session.user
    except Exception:
        pass
    return None


def get_user_profile(user_id: str):
    """
    Fetch the profile for a given user.
    Returns a dictionary or None if no profile exists.
    """
    supabase = get_supabase_client()
    try:
        response = (
            supabase.table("profiles")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        if response.data and len(response.data) > 0:
            return response.data[0]
    except Exception:
        pass
    return None


def create_user_profile(user_id: str, email: str, profile_data: dict):
    """
    Create a new profile for a user after sign-up.
    """
    supabase = get_supabase_client()
    profile_data["user_id"] = user_id
    profile_data["email"] = email
    response = supabase.table("profiles").insert(profile_data).execute()
    return response


def update_user_profile(user_id: str, profile_data: dict):
    """
    Update an existing user profile.
    """
    supabase = get_supabase_client()
    response = (
        supabase.table("profiles")
        .update(profile_data)
        .eq("user_id", user_id)
        .execute()
    )
    return response


def get_user_skills(user_id: str):
    """Fetch all skills for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_skills")
        .select("*")
        .eq("user_id", user_id)
        .order("category")
        .execute()
    )
    return response.data or []


def add_user_skill(user_id: str, skill_data: dict):
    """Add a skill for a user."""
    supabase = get_supabase_client()
    skill_data["user_id"] = user_id
    response = supabase.table("user_skills").insert(skill_data).execute()
    return response


def delete_user_skill(user_id: str, skill_id: int):
    """Delete a skill for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_skills")
        .delete()
        .eq("user_id", user_id)
        .eq("id", skill_id)
        .execute()
    )
    return response


def get_user_experiences(user_id: str):
    """Fetch all experiences for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_experiences")
        .select("*")
        .eq("user_id", user_id)
        .order("display_order")
        .execute()
    )
    return response.data or []


def add_user_experience(user_id: str, exp_data: dict):
    """Add an experience for a user."""
    supabase = get_supabase_client()
    exp_data["user_id"] = user_id
    response = supabase.table("user_experiences").insert(exp_data).execute()
    return response


def get_user_projects(user_id: str):
    """Fetch all projects for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_projects")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return response.data or []


def add_user_project(user_id: str, proj_data: dict):
    """Add a project for a user."""
    supabase = get_supabase_client()
    proj_data["user_id"] = user_id
    response = supabase.table("user_projects").insert(proj_data).execute()
    return response


def get_user_education(user_id: str):
    """Fetch all education records for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_education")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return response.data or []


def add_user_education(user_id: str, edu_data: dict):
    """Add an education record for a user."""
    supabase = get_supabase_client()
    edu_data["user_id"] = user_id
    response = supabase.table("user_education").insert(edu_data).execute()
    return response


def get_user_jobs(user_id: str):
    """Fetch all saved/applied jobs for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_jobs")
        .select("*")
        .eq("user_id", user_id)
        .execute()
    )
    return response.data or []


def update_user_job_status(user_id: str, job_id: int, status: str):
    """Update the status of a job for a user."""
    supabase = get_supabase_client()
    response = (
        supabase.table("user_jobs")
        .upsert({
            "user_id": user_id,
            "job_id": job_id,
            "status": status
        }, on_conflict="user_id, job_id")
        .execute()
    )
    return response

def clear_user_skills(user_id: str):
    """Delete all skills for a user."""
    supabase = get_supabase_client()
    return supabase.table("user_skills").delete().eq("user_id", user_id).execute()


def clear_user_experiences(user_id: str):
    """Delete all experiences for a user."""
    supabase = get_supabase_client()
    return supabase.table("user_experiences").delete().eq("user_id", user_id).execute()


def clear_user_projects(user_id: str):
    """Delete all projects for a user."""
    supabase = get_supabase_client()
    return supabase.table("user_projects").delete().eq("user_id", user_id).execute()


def clear_user_education(user_id: str):
    """Delete all education records for a user."""
    supabase = get_supabase_client()
    return supabase.table("user_education").delete().eq("user_id", user_id).execute()
