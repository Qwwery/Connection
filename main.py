from flask import Flask, session, render_template, request, redirect, url_for

app = Flask(__name__)
app.secret_key = 'DOTA 2'


def main():
    app.run(debug=True)


@app.route('/')
def start():
    if not session.get('logged_in'):
        return render_template('hello.html')
    else:
        return render_template('feed.html')


if __name__ == '__main__':
    main()
