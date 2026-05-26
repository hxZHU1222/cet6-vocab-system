from __future__ import annotations
from flask import Blueprint, current_app, redirect, render_template, request, session, url_for

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if not current_app.config.get("AUTH_ENABLED", True):
        session["authenticated"] = True
        return redirect(url_for("pages.index"))
    error = ""
    if request.method == "POST":
        password = request.form.get("password", "")
        if password == current_app.config.get("APP_PASSWORD"):
            session.permanent = True
            session["authenticated"] = True
            return redirect(request.args.get("next") or url_for("pages.index"))
        error = "密码不正确"
    return render_template("login.html", error=error)

@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
