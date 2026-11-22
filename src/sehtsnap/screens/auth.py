"""Sign-in and account creation."""

from __future__ import annotations

import asyncio

import flet as ft

from sehtsnap.core import theme
from sehtsnap.services.auth_service import AuthError
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import app_view, card, heading, muted


def build_auth(router) -> ft.View:
    state = router.state
    mode = {"signup": False}
    title = heading("Welcome back", 22)
    email = ft.TextField(
        label="Email", keyboard_type=ft.KeyboardType.EMAIL, autofill_hints=ft.AutofillHint.EMAIL
    )
    password = ft.TextField(label="Password", password=True, can_reveal_password=True)
    error = ft.Text("", color=theme.ACCENT, visible=False)
    submit = ft.FilledButton(content="Sign in", height=46)
    toggle = ft.TextButton(content="New here? Create an account")

    async def handle_submit(_) -> None:
        action = state.sign_up if mode["signup"] else state.sign_in
        submit.disabled = True
        error.visible = False
        router.page.update()
        try:
            await asyncio.to_thread(action, email.value or "", password.value or "")
        except (AuthError, DatabaseError) as failure:
            error.value = str(failure)
            error.visible = True
            submit.disabled = False
            router.page.update()
            return
        router.go("/home")

    def handle_toggle(_) -> None:
        mode["signup"] = not mode["signup"]
        title.value = "Create your account" if mode["signup"] else "Welcome back"
        submit.content = "Create account" if mode["signup"] else "Sign in"
        toggle.content = (
            "Already have an account? Sign in" if mode["signup"] else "New here? Create an account"
        )
        error.visible = False
        router.page.update()

    submit.on_click = handle_submit
    password.on_submit = handle_submit
    toggle.on_click = handle_toggle
    controls: list[ft.Control] = [
        card(
            ft.Column(
                spacing=14,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[title, email, password, error, submit, toggle],
            )
        )
    ]
    if state.settings.demo_mode:
        controls.append(muted("Demo mode: your account and data stay on this device."))
    return app_view(router, "/auth", "Account", controls, back_route="/")
