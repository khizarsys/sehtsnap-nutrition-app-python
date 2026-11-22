"""Route guards and view navigation."""

from __future__ import annotations

import flet as ft

from sehtsnap.core.state import AppState

PUBLIC_ROUTES = {"/", "/auth"}


class Router:
    """Build one view for the current route."""

    def __init__(self, page: ft.Page, state: AppState) -> None:
        self.page = page
        self.state = state
        self.file_picker = ft.FilePicker()
        page.on_route_change = lambda _: self.render()

    def go(self, route: str) -> None:
        if route == self.page.route:
            self.render()
        else:
            self.page.run_task(self.page.push_route, route)

    def _guard(self, route: str) -> str | None:
        if self.state.user is None:
            return None if route in PUBLIC_ROUTES else "/"
        if self.state.profile is None:
            return None if route == "/setup" else "/setup"
        if route in PUBLIC_ROUTES or route == "/setup":
            return "/home"
        return None

    def render(self) -> None:
        from sehtsnap.screens import build_view

        route = (self.page.route or "/").split("?")[0]
        redirect = self._guard(route)
        if redirect:
            self.go(redirect)
            return
        view = build_view(self, route)
        self.page.views.clear()
        self.page.views.append(view)
        self.page.update()
