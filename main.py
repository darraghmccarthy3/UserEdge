
from nicegui import ui
from dotenv import load_dotenv
from db_connector_pg import PostgresConnector
from user_page import UsersPage
import os

load_dotenv()

# --- read .env (with sensible fallbacks) ---
profile = os.getenv('APP_PROFILE', 'admin').lower()
host = os.getenv('HOST', '0.0.0.0')
port = int(os.getenv('PORT', '8080'))
title = os.getenv('APP_TITLE', 'Users Admin')
favicon = os.getenv('APP_FAVICON', ' ')
secret = os.getenv('STORAGE_SECRET', 'change-me-in-prod')
dark = os.getenv('APP_DARK', 'False')
repo = PostgresConnector()


@ui.page('/')
def main():
    if profile == 'pi':
        ui.timer(0.01, lambda: ui.navigate.to('/rpi-login'), once=True)
    else:
        UsersPage(repo)


#@ui.page('/rpi-login')
#def rpi_login():
   #from rpi_login_page import RpiLoginPage
   # RpiLoginPage(repo)


if __name__ in {'__main__', '__mp_main__'}:
    ui.run( host=host,port=port,title=title,favicon=favicon,dark=False,storage_secret=secret,reload=False)
