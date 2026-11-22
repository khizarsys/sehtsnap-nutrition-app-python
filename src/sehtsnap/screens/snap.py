"""Photo detection and manual food search."""

from __future__ import annotations

import asyncio
from pathlib import Path

import flet as ft

from sehtsnap.core import theme
from sehtsnap.screens.camera import camera_available
from sehtsnap.services.ai_vision_service import MAX_UPLOAD_BYTES
from sehtsnap.widgets.common import app_view, card, heading, muted, show_message
from sehtsnap.widgets.food_card import food_card


def _read_file(file: ft.FilePickerFile, allow_local_path: bool) -> bytes | None:
    """Read picked image data, never trusting a browser-supplied server path."""
    if file.bytes:
        data = bytes(file.bytes)
        return data if len(data) <= MAX_UPLOAD_BYTES else None
    if file.path and allow_local_path:
        path = Path(file.path)
        if path.stat().st_size > MAX_UPLOAD_BYTES:
            return None
        return path.read_bytes()
    return None


def build_snap(router) -> ft.View:
    state = router.state

    def open_food(food_id: str, servings: float = 1.0) -> None:
        state.pending_servings = servings
        router.go(f"/food/{food_id}")

    preview = ft.Container(
        visible=False, height=220, border_radius=12, clip_behavior=ft.ClipBehavior.HARD_EDGE
    )
    status = ft.Row(
        visible=False,
        controls=[ft.ProgressRing(width=20, height=20), muted("Identifying your dish...")],
    )
    feedback = ft.Text("", color=theme.ACCENT, visible=False)
    suggestions = ft.Column(spacing=8)
    results = ft.Column(spacing=8)

    def show_results(query: str) -> None:
        results.controls = [
            food_card(food, open_food) for food in state.nutrition.search(query, 12)
        ]
        if query.strip() and not results.controls:
            results.controls = [muted("No matching dishes found.")]

    search = ft.TextField(
        label="Search dishes",
        hint_text="Try biryani, daal chawal or saag",
        prefix_icon=ft.Icons.SEARCH,
        on_change=lambda event: (show_results(event.control.value or ""), router.page.update()),
    )

    async def pick_photo(_) -> None:
        files = await router.file_picker.pick_files(
            dialog_title="Choose a food photo",
            file_type=ft.FilePickerFileType.IMAGE,
            with_data=True,
        )
        if not files:
            return
        try:
            image = await asyncio.to_thread(_read_file, files[0], not router.page.web)
        except OSError:
            image = None
        if not image:
            show_message(router.page, "That photo could not be opened.")
            return
        await analyze_photo(image)

    async def analyze_photo(image: bytes) -> None:
        preview.content = ft.Image(src=image, fit=ft.BoxFit.COVER, width=640, height=220)
        preview.visible = True
        status.visible = True
        feedback.visible = False
        suggestions.controls = []
        router.page.update()

        outcome = await asyncio.to_thread(state.detect, image)
        status.visible = False
        result = outcome.result
        match = state.nutrition.match(result.dish) if result else None
        if result and match and not outcome.needs_review:
            open_food(match.food.id, result.serving_estimate)
            return

        if result and result.dish.casefold() != "unknown":
            suggestions.controls = [
                food_card(item.food, open_food)
                for item in state.nutrition.suggestions(result.dish, limit=3)
            ]
        fallback = (
            "Not sure about this dish. Is it one of these?"
            if suggestions.controls
            else "No dish was recognized. Please try another photo or search below."
        )
        feedback.value = outcome.error or fallback
        feedback.visible = True
        router.page.update()

    show_results("")
    captured_photo, state.pending_photo = state.pending_photo, None
    if captured_photo:
        router.page.run_task(analyze_photo, captured_photo)
    return app_view(
        router,
        "/snap",
        "Snap & Detect",
        [
            card(
                ft.Column(
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        heading("Photograph your meal", 16),
                        muted("Use one clear photo of a single dish for the best result."),
                        ft.FilledButton(
                            content="Take photo",
                            icon=ft.Icons.CAMERA_ALT,
                            height=48,
                            visible=camera_available(router.page),
                            on_click=lambda _: router.go("/camera"),
                        ),
                        ft.OutlinedButton(
                            content="Choose from gallery",
                            icon=ft.Icons.PHOTO_LIBRARY,
                            height=48,
                            on_click=pick_photo,
                        ),
                        preview,
                        status,
                        feedback,
                        suggestions,
                    ],
                )
            ),
            heading("Or search manually", 16),
            search,
            results,
        ],
        nav_index=1,
    )
