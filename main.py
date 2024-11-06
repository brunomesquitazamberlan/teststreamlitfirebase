import firebase_admin
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

firebase_credentials = dict(st.secrets["firebase"]['my_project_settings'])

#################################################################
# Verifique se já existe um app inicializado
if not firebase_admin._apps:
    cred = credentials.Certificate(firebase_admin)
    firebase_admin.initialize_app(cred)

# Conectar ao Firestore
db = firestore.client()
################################################################

st.title("hello world")
st.header("I'm alive")


