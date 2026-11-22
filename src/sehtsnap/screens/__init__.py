"""Application screens."""

from __future__ import annotations

import flet as ft

from sehtsnap.screens.advice import build_advice
from sehtsnap.screens.auth import build_auth
from sehtsnap.screens.food_detail import build_food_detail
from sehtsnap.screens.history import build_history
from sehtsnap.screens.home import build_home
from sehtsnap.screens.log import build_log
from sehtsnap.screens.onboarding import build_onboarding
from sehtsnap.screens.profile import build_profile, build_setup
from sehtsnap.screens.settings import build_settings
from sehtsnap.screens.snap import build_snap

BUILDERS = {
    "/": build_onboarding,
    "/auth": build_auth,
    "/setup": build_setup,
    "/home": build_home,
    "/snap": build_snap,
    "/log": build_log,
    "/history": build_history,
    "/profile": build_profile,
    "/advice": build_advice,
    "/settings": build_settings,
}


def build_view(router, route: str) -> ft.View:
    if route.startswith("/food/"):
        return build_food_detail(router, route.removeprefix("/food/"))
    return BUILDERS.get(route, build_home)(router)
