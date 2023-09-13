app: kitty
-
tag(): terminal
tag(): user.readline
tag(): user.generic_unix_shell
tag(): user.git
tag(): user.tabs

window rename <user.text>:
    user.kitty_set_window_title(text)
window {user.kitty_window_title}:
    user.kitty_focus_window(kitty_window_title)
^signal {user.kitty_signal} [in {user.kitty_window_title}]$:
    user.kitty_send_signal(kitty_signal, kitty_window_title or "")

session {user.kitty_session}:
    user.kitty_run_session(kitty_session)

katie {user.kitty_subdir}: user.kitty_cd(kitty_subdir)
katie root: user.kitty_cd("/")
katie up: user.kitty_cd("..")
katia: user.kitty_cd("..")

go run {user.kitty_go_file}:
    insert("go run "+kitty_go_file)

# TODO: the kitty extent "all" conflicts with the community command "copy all"
# I have added scrollback, but that is rather wordy.
copy {user.kitty_extent} [in {user.kitty_window_title}]:
    user.kitty_copy(kitty_extent, kitty_window_title or "")
