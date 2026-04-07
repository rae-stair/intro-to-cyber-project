Run (from this folder): pip install -r requirements.txt
Then: python app.py
Open http://127.0.0.1:5000/login

TEMPORARY: With debug on (default for python app.py), the login page shows
"Skip login (dev only)" which opens /staff (prototype). To allow skip with
debug off: set environment variable ALLOW_DEV_LOGIN_SKIP=1
Remove /dev/skip-login and this bypass before production.
