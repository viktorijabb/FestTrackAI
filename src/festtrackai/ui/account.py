"""Account pricing controls for a single-user, localhost Streamlit installation."""
import os
from pathlib import Path
import subprocess
import sys
import streamlit as st
from festtrackai.filmfreeway.account import load_session, disconnect, fetch_prices, SessionRequired


def account_panel():
    st.subheader('FilmFreeway account & submission prices')
    st.caption('Sign in directly on FilmFreeway. Your browser session stays on this computer.')
    try:
        session = load_session()
    except SessionRequired:
        session = None
    generation = session['generation'] if session else None
    if st.session_state.get('ff_generation') != generation:
        st.session_state.pop('ff_prices', None)
        st.session_state['ff_generation'] = generation

    if session:
        st.success('Local session saved — checked again whenever prices are refreshed.')
        st.caption('Membership: ' + session['membership'].title() + ' (confirmed by you, not automatically verified).')
        if st.button('Disconnect FilmFreeway'):
            process = st.session_state.get('ff_login_process')
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=5)
            disconnect()
            st.session_state.pop('ff_prices', None)
            st.rerun()

    with st.expander('Connect or change FilmFreeway account', expanded=session is None):
        membership = st.radio('Your current FilmFreeway membership', ['Standard', 'Gold'],
            help='Choose Gold only if your account has an active Gold membership. This is your confirmation, not automatic detection.')
        command = 'uv run python -m festtrackai.filmfreeway.account login --membership ' + membership.lower()
        is_container = Path('/.dockerenv').exists() or os.environ.get('FESTTRACKAI_IN_DOCKER') == '1'
        if is_container:
            st.info('Run this once in your project terminal on your desktop (outside Docker). It opens FilmFreeway for you to sign in. Then click Check connection.')
            st.code(command, language='bash')
        elif st.button('Sign in to FilmFreeway'):
            process = st.session_state.get('ff_login_process')
            if process is not None and process.poll() is None:
                st.info('A login window is already open. Complete sign-in there.')
            else:
                st.session_state['ff_login_process'] = subprocess.Popen(
                    [sys.executable, '-m', 'festtrackai.filmfreeway.account', 'login',
                     '--membership', membership.lower()],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                st.info('Complete sign-in in the opened browser, then click Check connection.')
        st.caption('First-time desktop setup: uv run playwright install chromium. Login can take up to five minutes; closing the browser cancels it.')
        if st.button('Check connection'):
            process = st.session_state.get('ff_login_process')
            if process is not None and process.poll() not in (None, 0):
                st.error('Login did not finish. Install Chromium and try again on your desktop.')
            else:
                st.rerun()

    if not session:
        st.info('Connect your account to load submission prices.')
        return

    url = st.text_input('FilmFreeway festival profile URL',
                       placeholder='https://filmfreeway.com/TorontoShortFilmFestival')
    if st.button('Refresh account prices', disabled=not url.strip()):
        st.session_state.pop('ff_prices', None)
        try:
            with st.spinner('Checking your session and reading category fees…'):
                st.session_state['ff_prices'] = fetch_prices(url)
        except SessionRequired as exc:
            st.warning(str(exc))
        except ValueError as exc:
            st.error(str(exc))
        except Exception:
            st.error('Could not read FilmFreeway. Check your connection, installed Chromium browser, and local login session.')

    result = st.session_state.get('ff_prices')
    if result and result['generation'] == generation:
        st.link_button('View source on FilmFreeway', result['url'])
        st.caption('Checked ' + result['checked_at'] + '. Current submission tiers only. Verify project eligibility and checkout pricing on FilmFreeway.')
        budget = st.number_input('Maximum submission fee (USD)', min_value=0.0, value=10.0)
        affordable_only = st.checkbox('Only show fees within budget', value=False)
        rows = result['prices']
        if affordable_only:
            rows = [row for row in rows if row['fee'] is not None and row['fee'] <= budget]
        if rows:
            st.dataframe(rows, hide_index=True, use_container_width=True)
        else:
            st.info('No verified USD category fees match this budget.')
        st.caption('Gold uses the published Gold fee when available; otherwise the Standard fee. Unknown currencies are not included in USD budget results. Account prices are kept separate from the shared festival records.')
