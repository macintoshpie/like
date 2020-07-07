import os
import uuid
import secrets

from flask import request, session, redirect, url_for, g
import sqlite3
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from like import app
from like.config import SESSION_LIFETIME_MINUTES, EMAIL_STATE_LIFETIME_MINUTES, PAGINATION_PER_PAGE
from like.db import datetime_now_str, query_db, get_db
from like.views.utils import (
    make_response,
    get_active_session,
    is_authenticated,
    is_account_owner,
    get_request_json,
)


def create_user_session(user_id, db_con):
    session_data = {
        "user_id": user_id,
        "session_id": str(uuid.uuid4()),
        "expiration": datetime_now_str(SESSION_LIFETIME_MINUTES),
    }
    db_con.execute(
        "INSERT OR REPLACE INTO user_sessions (user_id, session_id, expiration) VALUES (:user_id, :session_id, :expiration)",
        session_data,
    )
    session["session_id"] = session_data["session_id"]
    session["user_id"] = session_data["user_id"]


def delete_user_session(user_id, db_con):
    db_con.execute(
        "DELETE FROM user_sessions WHERE user_id = :user_id", {"user_id": user_id},
    )
    del session["session_id"]
    del session["user_id"]


def create_user_email_state(user_id, db_con):
    state = secrets.token_hex(32)
    db_con.execute(
        "INSERT INTO user_email_state (user_id, state, expiration) VALUES (:user_id, :state, :expiration)",
        {
            "user_id": user_id,
            "state": state,
            "expiration": datetime_now_str(EMAIL_STATE_LIFETIME_MINUTES),
        },
    )
    return state


@app.route("/api/users/me", methods=["GET"])
def get_current_user():
    db_session = get_active_session()
    if db_session is None:
        return make_response(400, 'Not logged in')
    
    user = query_db(
        "SELECT * FROM users where id = :user_id",
        {'user_id': session['user_id']},
        one=True
    )
    return make_response(200, items=[user])


@app.route("/api/feed", methods=["GET"])
def feed():
    try:
        before_post = request.args.get("before_post")
        if before_post is not None:
            before_post = int(before_post)
    except:
        before_post = None
    posts = query_db(
        """
        SELECT posts.*, users.username FROM posts
        JOIN users ON users.id = posts.user_id
        """
        f"{'WHERE posts.id < :before_post' if before_post is not None else ''}"
        """
        ORDER BY posts.id DESC
        LIMIT :limit
        """,
        {
            "before_post": before_post,
            "limit": PAGINATION_PER_PAGE,
        }
    )
    data = {
        'items': posts
    }
    if len(posts) == PAGINATION_PER_PAGE:
        return make_response(200, items=posts, nextLink=f'api/feed?before_post={posts[-1]["id"]}')

    return make_response(200, items=posts)


@app.route("/api/users/", methods=["GET"])
def users_list():
    return {"data": {"items": query_db("SELECT * FROM users")}}, 200


@app.route("/api/users/", methods=["POST"])
def users_create():
    if get_active_session() is not None:
        return make_response(400, "Already authenticated")

    cur = None
    body = get_request_json()
    with get_db() as con:
        try:
            cur = con.execute(
                "INSERT INTO users (username, email) VALUES (:username, :email)", body
            )
            user_id = cur.lastrowid
            create_user_session(user_id, con)
            return make_response(
                201,
                items=[{"id": user_id, "username": body["username"], "email": body["email"]}])
        except sqlite3.IntegrityError as e:
            con.rollback()
            if "email" in str(e):
                return make_response(400, "Email already in use")
            elif "username" in str(e):
                return make_response(400, "Username already in use")
            else:
                return make_response(500, errors=[str(e)])
        except Exception as e:
            con.rollback()
            return make_response(500, errors=[str(e)])
        finally:
            if cur is not None:
                cur.close()


@app.route("/api/users/<int:user_id>", methods=["GET"])
def users_retrieve(user_id):
    user = query_db(
        "SELECT * FROM users WHERE id=:user_id", {"user_id": user_id}, one=True
    )
    if user is None:
        return make_response(404, "User not found")
    return make_response(200, items=[user])


@app.route("/api/users/<int:user_id>/session", methods=["GET"])
def session_create(user_id):
    if request.args.get("state") is None:
        return make_response(400, "Missing `state` query param")

    # user clicked link from email
    # if the state matches what we have for this user, then create a session
    email_state = query_db(
        """
        SELECT * FROM user_email_state WHERE
            user_id = :user_id
            AND state = :state
            AND :current_datetime < expiration
        """,
        {
            "user_id": user_id,
            "state": request.args.get("state"),
            "current_datetime": datetime_now_str(),
        },
        one=True,
    )
    if email_state is None:
        return make_response(400, "Invalid state")

    with get_db() as con:
        try:
            con.execute(
                "DELETE FROM user_email_state WHERE user_id = :user_id",
                {"user_id": user_id},
            )
            create_user_session(user_id, con)
            return redirect(url_for('index'))
        except Exception as e:
            return make_response(500, errors=[str(e)])


@app.route("/api/users/<int:user_id>/session", methods=["DELETE"])
@is_account_owner
def session_delete(user_id):
    if not is_authenticated(user_id):
        return make_response(403)

    with get_db() as con:
        try:
            delete_user_session(user_id, con)
            return make_response(200, "Deleted")
        except Exception as e:
            return make_response(500, errors=[str(e)])


@app.route("/api/users/<int:user_id>/session", methods=["POST"])
def request_email_login(user_id):
    # user is requesting a link to be sent to email to authenticate
    with get_db() as con:
        try:
            con.execute(
                "DELETE FROM user_email_state WHERE user_id = :user_id",
                {"user_id": user_id},
            )
            state = create_user_email_state(user_id, con)
            link = f'{request.url_root}api/users/{user_id}/session?state={state}'
            html_content = f"Click here to log in: <a href='{link}'>{link}</a>"
            if os.environ.get('FLASK_ENV') == 'development':
                print(html_content)
            else:
                if getattr(g, '_user_email', None) is not None:
                    to_email = g._user_email
                else:
                    to_email = query_db('SELECT email FROM users WHERE id = :id', {'id': user_id}, one=True)['email']
                message = Mail(
                    from_email='ted.summer2@gmail.com',
                    to_emails='ted.summer2@gmail.com', # to_email,
                    subject='Like app login',
                    html_content=html_content,
                )
                sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                response = sg.send(message)
                print(response.status_code)
                print(response.body)
                print(response.headers)

            return make_response(200, "Please check your email")
        except Exception as e:
            return make_response(500, errors=[str(e), str(e.body)])

@app.route("/api/login", methods=["POST"])
def request_email_login_username():
    body = get_request_json()
    if 'email' not in body or not body['email']:
        return make_response(400, 'Missing valid `email` in request body')

    user = query_db("SELECT * FROM users WHERE email = :email", {'email': body['email']}, one=True)
    if user is None:
        return make_response(404, 'Email not registered')

    g._user_email = user['email']
    return request_email_login(user['id'])


@app.route("/api/users/<int:user_id>/posts/", methods=["POST"])
@is_account_owner
def posts_create(user_id):
    body = get_request_json()
    cur = None
    with get_db() as con:
        try:
            params = body.copy()
            created = datetime_now_str()
            params.update({"user_id": user_id, "created": created})
            cur = con.execute(
                """
                INSERT INTO posts (uri, user_id, created)
                SELECT
                    :uri, :user_id, :created
                WHERE NOT EXISTS (
                    SELECT 1 FROM posts
                    WHERE
                        date(created) = date(:created)
                        AND user_id = :user_id
                )
                """,
                params,
            )
            post_id = cur.lastrowid
            if post_id == 0:
                return make_response(
                    400, "A post for today already exists for this user"
                )
            else:
                return make_response(201, items=[{"id": post_id, "user_id": user_id, "created": created, "uri": params["uri"]}])
        except Exception as e:
            return make_response(500, errors=[str(e)])
        finally:
            if cur is not None:
                cur.close()


@app.route("/api/users/<int:user_id>/posts/", methods=["GET"])
def posts_list(user_id):
    return make_response(
        200,
        items=query_db(
            """
            SELECT * FROM posts
            WHERE
                user_id = :user_id
            """,
            {"user_id": user_id},
        ),
    )


@app.route("/api/users/<int:user_id>/posts/<int:post_id>", methods=["GET"])
def posts_retrieve(user_id, post_id):
    post = query_db(
        """
        SELECT * FROM posts
        WHERE
            user_id = :user_id
            AND id = :post_id
        """,
        {"user_id": user_id, "post_id": post_id},
        one=True,
    )
    if post is None:
        return make_response(404)
    return make_response(200, items=[post])


@app.route("/api/users/<int:user_id>/posts/<int:post_id>", methods=["DELETE"])
@is_account_owner
def posts_delete(user_id, post_id):
    query_db(
        """
        DELETE FROM posts
        WHERE
            user_id = :user_id
            AND id = :post_id
        """,
        {"user_id": user_id, "post_id": post_id},
    )
    return make_response(200, "Deleted")
