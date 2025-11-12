# rpi_login_page.py
from __future__ import annotations
from datetime import timezone
from typing import Optional
import bcrypt
from nicegui import ui, app
from db_connector_pg import PostgresConnector


class RpiLoginPage:
    """Offline login against local Postgres replica of 'users'."""

    def __init__(self, repo: PostgresConnector):
        self.repo = repo
        ui.page_title('RPi Login (Users)')

        # Header
        with ui.header().classes('bg-slate-800 text-white'):
            ui.label('RPi Login').classes('text-lg font-semibold')
            ui.space()
            self.last_sync = ui.label('Last sync: …').classes('text-white/80')
            self.status = ui.badge('●').props('color=grey text-color=white')
            ui.button('DB health', on_click=self._show_health).props('flat').classes('text-white/90')

        self.content = ui.column().classes('items-center justify-center w-full p-6')
        self._render()

def _render(self):
    self._refresh_header()
    if app.storage.user.get('user_id'):
        self._show_welcome()
    else:
        self._show_login()

def _show_health(self):
    try:
        ui.notify(self.repo.db_health())
    except Exception as e:
        ui.notify(f'DB error: {e}', type='negative')

# ----- small helpers -----
def _refresh_header(self):
    try:
        m = self.repo.get_users_last_updated_at()
        if m:
            self.last_sync.text = f"Last DB change: {m.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
        else:
            self.last_sync.text = "Last DB change: -"
        self.status.props('color=green')
    except Exception:
        self.last_sync.text = "Last DB change: (DB unavailable)"
        self.status.props('color=red')
    self.last_sync.update()
    self.status.update()

# ----- views -----
def _show_login(self):
    self.content.clear()
    with self.content:
        with ui.card().classes('w-[360px] max-w-full'):
            ui.label('Sign in').classes('text-xl font-medium mb-2')
            inp_user = ui.input('Username').classes('w-full')
            inp_pass = ui.input('Password').props('type=password').classes('w-full')

            def do_login():
                u = self.repo.authenticate_user(inp_user.value or '', inp_pass.value or '')
                if u:
                    app.storage.user['user_id'] = str(u.id)
                    ui.notify(f'Welcome! {u.username}')
                    self._render()
                    # ...continue...
                else:
                    ui.notify('Invalid credentials', type='negative')
                self._refresh_header()

            with ui.row().classes('justify-end gap-2 mt-2'):
                ui.button('Login', on_click=do_login).props('color=primary')

def _show_welcome(self):
    self.content.clear()
    with self.content:
        uid = app.storage.user.get('user_id')
        user = self.repo.get_user_by_id(uid) if uid else None
        with ui.card().classes('w-[360px] max-w-full'):
            ui.label(f"Logged in as: {user.username}").classes('text-lg font-medium')
            ui.label(f'Roles: {", ".join(user.roles) if user.roles else "(no roles)"}').classes('text-sm text-gray-600')
            with ui.row().classes('justify-end gap-2 mt-2'):
                ui.button(
                    'Logout',
                    on_click=lambda: (app.storage.user.pop('user_id', None), self._render())
                )
