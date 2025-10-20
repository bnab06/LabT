import streamlit as st
import sys
import pandas as pd
import numpy as np

st.title("LabT - Test minimal")
st.write("Python:", sys.version)
st.write("pandas:", pd.__version__)
st.write("numpy:", np.__version__)