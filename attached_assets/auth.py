import streamlit as st
from attached_assets.database import Database

def check_password():
    """Check if the password is correct."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        return True

    st.markdown("""
        <style>
        .stButton button {
            background-color: #4361ee;
            color: white;
            font-weight: bold;
        }
        .login-container {
            max-width: 400px;
            margin: 0 auto;
            padding: 20px;
            border-radius: 10px;
            background-color: #F0F2F6;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🧪 Molbio Reagents Inventory Management System")

    st.markdown("<div class='login-container'>", unsafe_allow_html=True)
    st.subheader("🔒 Login")
    username = st.text_input("Username", key="login_username")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        db = Database()
        if db.verify_user(username, password):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Invalid username or password")
            print(f"Login failed for user: {username}")

    st.markdown("</div>", unsafe_allow_html=True)
    return False
