function codex -d "Run Codex inline in et sessions so Cmd+click opens links on the client"
    # Fullscreen Codex captures the mouse and opens clicked links itself, on this machine.
    if set -q ET_VERSION
        command codex --no-alt-screen $argv
    else
        command codex $argv
    end
end
