import os
import os.path
import json
import socket
import glob
import subprocess

from talon import Context, actions, Module, ui, app, fs

mod = Module()
mod.list("kitty_window_title", desc="titles of open kitty windows")
mod.list(
    "kitty_subdir",
    desc="list of subdirs inside cwd of focused kitty window",
)
mod.list(
    "kitty_file",
    desc="list of files inside cwd of focused kitty window",
)
mod.list(
    "kitty_go_file",
    desc="list of go files inside cwd of focused kitty window",
)
mod.list("kitty_signal", desc="kitty unix signals")
mod.list("kitty_match", desc="kitty matchers")
mod.list("kitty_extent", desc="kitty get-text extents")
mod.list("kitty_session", desc="kitty session files")

ctx = Context()
ctx.matches = r"""
app: kitty
"""

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")
global KITTY_SOCKET
KITTY_SOCKET = ""  # set in register_events


@mod.action_class
class UserActions:
    def kitty_set_window_title(phrase: str):
        """Sets the window title"""
        print("kitty_set_window_title", phrase)
        """Sets the window title"""
        kitty_send_rpc("set-window-title", {"title": phrase})
        # todo: match, temporary?

    def kitty_focus_window(phrase: str):
        """Focuses a window"""
        print("kitty_focus_window", phrase)
        match = f'title:"{phrase}"'
        print("match", match)
        kitty_send_rpc("focus-window", {"match": match})
        # todo: match, temporary

    def kitty_send_signal(signal: str, phrase: str):
        """Sends a signal to a window"""
        print("kitty_send_signal", phrase)
        payload = {"signals": [signal]}
        if phrase:
            match = f'title:"{phrase}"'
            print("match", match)
            payload["match"] = match
        kitty_send_rpc("signal-child", payload)
        # todo: match, temporary

    def kitty_run_session(session: str):
        """Runs a session"""
        print("kitty_run_session", session)
        apps_by_name = ui.apps(name="kitty")
        if len(apps_by_name) == 0:
            print("kitty_run_session error: no kitty apps found")
            return
        if len(apps_by_name) > 1:
            print("kitty_run_session error: multiple kitty apps found", apps_by_name)
            return
        app = apps_by_name[0]
        subprocess.run(
            [
                app.path + "/Contents/MacOS/kitty",  # TODO: linux
                "--single-instance",
                "--session",
                f"{SESSIONS_DIR}/{session}.session",
            ],
        )

    def kitty_copy(extent: str, match: str):
        """Copies text from the terminal"""
        print("kitty_copy", extent)
        text = kitty_get_text(extent, match)
        if text is None:
            return
        actions.clip.set_text(text)

    def kitty_cd(subdir: str):
        """Changes directory in the focused kitty window"""
        actions.insert(f"cd {subdir}\n")
        update_kitty_subdirs_and_files()

    def update_kitty_subdirs_and_files():
        """Updates the lists of subdirs and files in the focused kitty window"""
        # ask kitty for the current working directory of the focused window
        cwd = kitty_cwd()
        all = []
        if cwd is not None:
            all = os.listdir(cwd)
        for cull in [".DS_Store", "."]:
            if cull in all:
                all.remove(cull)
        subdirs = [f for f in all if os.path.isdir(os.path.join(cwd, f))]
        files = [f for f in all if os.path.isfile(os.path.join(cwd, f))]
        ctx.lists["user.kitty_subdir"] = {
            clean_spoken_form(subdir): subdir for subdir in subdirs
        }
        ctx.lists["user.kitty_file"] = {clean_spoken_form(file): file for file in files}
        ctx.lists["user.kitty_go_file"] = {
            clean_spoken_form(file): file for file in files if file.endswith(".go")
        }


def clean_spoken_form(s: str):
    """Cleans the spoken form of a string"""
    # TODO: expand this, and potentially expand to multiple spoken forms,
    # e.g. "x.go" -> both "x dot go" and "x go"
    return s.replace(".", " ").replace("-", " ").replace("_", " ").lower()


def kitty_get_text(extent: str, title: str):
    payload = {"extent": extent}
    if title:
        match = f'title:"{title}"'
        payload["match"] = match
    out = kitty_send_rpc("get-text", payload)
    if out is None or not out.get("ok"):
        print("kitty_get_text error", out)
        return None
    return out.get("data")


def kitty_ls(match: str = ""):
    """Lists the windows"""
    payload = {}
    if match:
        payload["match"] = match
    resp = kitty_send_rpc("ls", payload)
    if resp is None or not resp.get("ok"):
        print("kitty_ls error", resp)
        return None
    return json.loads(resp.get("data"))


def kitty_titles():
    """Lists the window titles"""
    data = kitty_ls()
    if data is None:
        return []
    titles = []
    for oswin in data:
        for tab in oswin["tabs"]:
            for win in tab["windows"]:
                titles.append(win["title"])
    return titles


def kitty_cwd():
    """Lists the cwd of the focused window"""
    data = kitty_ls(make_match(focused=True))
    if data is None:
        return []
    # print("data", data)
    for oswin in data:
        for tab in oswin["tabs"]:
            for win in tab["windows"]:
                if win.get("is_focused"):
                    return win.get("cwd")
    return None


def make_match(title: str = "", focused: bool = False):
    """Makes a kitty match object"""
    matchers = []
    if title != "":
        matchers.append(f'title:"{title}"')
    if focused:
        matchers.append("state:focused")
    return " and ".join(matchers)


def kitty_send_rpc(cmd_name: str, payload: dict = None, no_response: bool = False):
    """Sends a kitty RPC command to the kitty terminal"""
    if KITTY_SOCKET == "":
        print("kitty_send_rpc error: socket not set yet")
        return
    blob = {
        "cmd": cmd_name,
        "version": [0, 14, 2],
    }
    if payload:
        blob["payload"] = payload
    if no_response:
        blob["no_response"] = True
    j = json.dumps(blob)
    print("kitty_send_rpc", j)
    msg = f"\x1bP@kitty-cmd{j}\x1b\\"
    # socket is of the form $TALON_HOME/.kitty.sock-PID
    # find the socket by globbing
    all = glob.glob(KITTY_SOCKET + "-*")
    if len(all) == 0:
        print("kitty_send_rpc error: no sockets found")
        return
    if len(all) > 1:
        print("kitty_send_rpc error: multiple sockets found", all)
        return
    resp = None
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.connect(all[0])
        client.send(bytes(msg, "utf-8"))
        if not no_response:
            client.settimeout(1)
            resp = kitty_read_response(client)
            if resp is None or not resp.get("ok"):
                print("kitty_send_rpc error", resp)
                return
            # print("response", resp)
    # TODO: does this belong inside the with?
    client.close()
    return resp


def kitty_read_response(client: socket.socket):
    """Reads the response from the kitty socket"""
    data = ""
    while not data.endswith("\x1b\\"):
        # print("kitty_read_response")
        try:
            buf = client.recv(1024)
        except socket.timeout:
            buf = None
        if not buf:
            break
        data += buf.decode("utf-8")
    # print("raw data", data)
    if not data.endswith("\x1b\\") or not data.startswith("\x1bP@kitty-cmd"):
        print("kitty_read_response error: invalid data", data)
        return None
    data = data[len("\x1bP@kitty-cmd") : -len("\x1b\\")]
    data = json.loads(data)
    return data


def win_event_handler(window):
    if window.app.name != "kitty":
        return
    # ask kitty for a list of titles, because there are window
    # titles inside tabs inside os windows that we cannot see
    titles = kitty_titles()
    if titles is None:
        return
    ctx.lists["user.kitty_window_title"] = {
        clean_spoken_form(title): title for title in titles
    }


def win_focus_handler(window):
    if window.app.name != "kitty":
        return
    update_kitty_subdirs_and_files()


def update_kitty_subdirs_and_files():
    actions.user.update_kitty_subdirs_and_files()


def update_sessions():
    files = glob.glob(f"{SESSIONS_DIR}/*.session")
    file_names_without_extension = [
        f[len(SESSIONS_DIR) + 1 : -len(".session")] for f in files
    ]
    ctx.lists["user.kitty_session"] = {
        name: name for name in file_names_without_extension
    }


def register_events():
    ui.register("win_title", win_event_handler)
    ui.register("win_focus", win_focus_handler)
    fs.watch(str(SESSIONS_DIR), lambda _1, _2: update_sessions())
    update_sessions()
    global KITTY_SOCKET
    KITTY_SOCKET = actions.path.talon_home() + "/.kitty.sock"


# prevent scary errors in the log by waiting for talon to be fully loaded
# before registering the events
app.register("ready", register_events)
