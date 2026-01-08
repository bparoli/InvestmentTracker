import streamlit as st
import google_auth_oauthlib.flow
from googleapiclient.discovery import build
import os

# Configuration
# The user needs to download this from Google Cloud Console
CLIENT_SECRET_FILE = 'client_secret.json'
SCOPES = ['openid', 'https://www.googleapis.com/auth/userinfo.email', 'https://www.googleapis.com/auth/userinfo.profile']
REDIRECT_URI = 'http://localhost:8501'

def get_flow():
    """Creates the OAuth flow object."""
    if not os.path.exists(CLIENT_SECRET_FILE):
        return None
        
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    return flow

def login():
    """Handles the login process."""
    if "user_info" not in st.session_state:
        st.session_state.user_info = None

    # check if client_secret exists
    flow = get_flow()
    if not flow:
        st.error(f"❌ `{CLIENT_SECRET_FILE}` not found. Please follow the instructions to download it from Google Cloud Console and place it in the root directory.")
        return

    # Check for query params (callback)
    # Streamlit 1.30+ uses st.query_params
    if "code" in st.query_params:
        code = st.query_params["code"]
        
        try:
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user info
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            st.session_state.user_info = user_info
            
            # Clear query params to prevent re-execution/clean URL
            st.query_params.clear()
            st.rerun() # Rerun to update the UI
            
        except Exception as e:
            st.error(f"An error occurred during authentication: {e}")
            # simple clear on error
            st.query_params.clear()

    # Show Login Button if not logged in
    if not st.session_state.user_info:
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        
        st.markdown(
            f'''
            <div style="text-align: center; margin-top: 50px;">
                <h2>Welcome to Investment Tracker</h2>
                <p>Please sign in to continue.</p>
                <a href="{authorization_url}" target="_self">
                    <button style="
                        background-color: #4285F4;
                        color: white;
                        padding: 12px 24px;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                        font-size: 16px;
                        font-family: Roboto, sans-serif;
                        display: inline-flex;
                        align-items: center;
                        gap: 10px;
                    ">
                        Sign in with Google
                    </button>
                </a>
            </div>
            ''',
            unsafe_allow_html=True
        )

def logout():
    """Logs the user out."""
    if st.button("Logout"):
        st.session_state.user_info = None
        st.rerun()

def get_user_email():
    """Returns the email of the logged-in user."""
    if st.session_state.user_info:
        return st.session_state.user_info.get("email")
    return None
