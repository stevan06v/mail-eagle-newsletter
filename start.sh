virtualenv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -U bootstrap-flask
python app.py &

echo "http://0.0.0.0:4000/"