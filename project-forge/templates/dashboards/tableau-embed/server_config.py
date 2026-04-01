import os
from flask import Flask

app = Flask(__name__)


@app.get('/token')
def token():
    value = os.getenv('TABLEAU_JWT_TOKEN', '')
    if not value:
        return {'error': 'missing TABLEAU_JWT_TOKEN'}, 400
    return {'token': value}, 200


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
