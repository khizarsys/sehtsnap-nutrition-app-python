"""In-app camera capture."""

from __future__ import annotations

import asyncio
import logging

import flet as ft
import flet_camera as fc

from sehtsnap.core import theme

logger = logging.getLogger(__name__)
CAMERA_ERROR = "Camera could not start. Allow camera access in phone settings or use the gallery."
CAPTURE_ERROR = "The photo could not be taken. Please try again."
MOUNT_DELAY_SECONDS = 0.4


def camera_available(page: ft.Page) -> bool:
    """Return True on platforms supported by the Flet camera control."""
    return bool(page.web) or page.platform in (ft.PagePlatform.ANDROID, ft.PagePlatform.IOS)


def _choose_back_camera(cameras: list[fc.CameraDescription]) -> fc.CameraDescription | None:
    for camera in cameras:
        if camera.lens_direction == fc.CameraLensDirection.BACK:
            return camera
    return cameras[0] if cameras else None


def build_camera(router) -> ft.View:
    state = router.state
    camera = fc.Camera(expand=True, preview_enabled=True)
    message = ft.Text("Starting camera...", color=ft.Colors.WHITE, text_align=ft.TextAlign.CENTER)
    capture = ft.IconButton(
        icon=ft.Icons.CAMERA_ALT,
        icon_color=theme.PRIMARY,
        icon_size=34,
        bgcolor=ft.Colors.WHITE,
        width=76,
        height=76,
        tooltip="Take photo",
        disabled=True,
    )

    async def start_camera() -> None:
        await asyncio.sleep(MOUNT_DELAY_SECONDS)
        try:
            selected = _choose_back_camera(await camera.get_available_cameras())
            if selected is None:
                raise RuntimeError("No camera found")
            await camera.initialize(selected, fc.ResolutionPreset.HIGH, enable_audio=False)
        except Exception as error:
            logger.warning("Camera start failed: %s", type(error).__name__)
            message.value = CAMERA_ERROR
            router.page.update()
            return
        message.value = "Point at one dish and tap the button"
        capture.disabled = False
        router.page.update()

    async def take_photo(_) -> None:
        capture.disabled = True
        message.value = "Taking photo..."
        router.page.update()
        try:
            image = await camera.take_picture()
        except Exception as error:
            logger.warning("Camera capture failed: %s", type(error).__name__)
            image = None
        if not image:
            message.value = CAPTURE_ERROR
            capture.disabled = False
            router.page.update()
            return
        state.pending_photo = bytes(image)
        router.go("/snap")

    capture.on_click = take_photo
    router.page.run_task(start_camera)
    return ft.View(
        route="/camera",
        bgcolor=ft.Colors.BLACK,
        padding=0,
        spacing=12,
        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        appbar=ft.AppBar(
            title=ft.Text("Take photo", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLACK,
            color=ft.Colors.WHITE,
            automatically_imply_leading=False,
            leading=ft.IconButton(
                icon=ft.Icons.ARROW_BACK,
                icon_color=ft.Colors.WHITE,
                tooltip="Back",
                on_click=lambda _: router.go("/snap"),
            ),
        ),
        controls=[
            ft.Container(expand=True, alignment=ft.Alignment.CENTER, content=camera),
            ft.Container(padding=ft.Padding.symmetric(horizontal=20), content=message),
            ft.Container(padding=ft.Padding.only(bottom=24), content=capture),
        ],
    )
