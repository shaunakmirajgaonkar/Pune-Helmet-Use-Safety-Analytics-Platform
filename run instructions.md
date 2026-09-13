# Run

cd ~/Downloads/Pune-Helmet-Use-Safety-Analytics-Platform
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
