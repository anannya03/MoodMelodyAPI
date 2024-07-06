# test_import.py
try:
    import flask_restful
    print("flask_restful is installed and can be imported.")
except ImportError:
    print("flask_restful is not installed.")
