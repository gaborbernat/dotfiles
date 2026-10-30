function _wt_pick_url -d "Pick the clone URL whose protocol matches a reference URL" -a reference https_url ssh_url
    # Following the protocol already in use keeps a new remote on the same authentication.
    if string match -q 'git@*' -- "$reference"
        string join \n -- $ssh_url
    else
        string join \n -- $https_url
    end
end
