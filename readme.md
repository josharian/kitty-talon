This is integration between Talon and the kitty terminal.

It is under development. I expect it to be unusable for the general public.

If you are interested in using it or helping out, please ping me on the Talon slack.

## Setup

Talon, obviously. Kitty, also.

Then:

* Enable [shell integration](https://sw.kovidgoyal.net/kitty/shell-integration/).
* In your `kitty.conf`, [enable socket-based remote control](https://sw.kovidgoyal.net/kitty/conf/#opt-kitty.allow_remote_control).
  - `allow_remote_control socket-only`
* In your `kitty.conf`, set [listen_on](https://sw.kovidgoyal.net/kitty/conf/#opt-kitty.listen_on) to `$TALON_HOME/.kitty.sock`.
  - `listen_on unix:~/.talon/.kitty.sock`
* Configure kitty to run with `--single-instance`. On Linux, just pass that flag when starting kitty. On macOS, see [the FAQ entry](https://sw.kovidgoyal.net/kitty/faq/#how-do-i-specify-command-line-options-for-kitty-on-macos).
* Pending [dynamic list](https://github.com/talonvoice/talon/issues/625) support in Talon, set up a callback in your zsh chpwd function (or however your preferred shell does it) to alert Talon when your directory changes. Mine reads like this, in `.zshrc`:
  -
```sh
function chpwd {
    echo '{"cmd": "input", "text": "actions.user.update_kitty_subdirs_and_files()"}' | socat - UNIX-CONNECT:~/.talon/.sys/repl.sock >/dev/null 2>&1
}
```

## Customization

Put your [kitty sessions](https://sw.kovidgoyal.net/kitty/overview/#startup-sessions) in the sessions subdirectory. The name of the file (without the extension) is the spoken form for the session file.

## TODOs

* Flesh out the grammar
* Organize and structure command destination matching. Window titles, all, what else?
* Makes sessions work on Linux, see the todos in the code
* Docs, of course
* Marks
* Confetti
* Draw the owl
