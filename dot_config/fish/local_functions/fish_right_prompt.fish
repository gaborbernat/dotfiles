function fish_right_prompt
    # Don't show right prompt in transient mode
    set --query _bgp_transient_pending && return

    set --local parts

    # Context-aware versions with icons (async result)
    # Format: "node:22.0.0 python:3.12.0 rust:1.75.0"
    if test -n "$$_bgp_context"
        for ctx in (string split ' ' $$_bgp_context)
            set --local ctx_type (string split ':' $ctx)[1]
            set --local ctx_ver (string split ':' $ctx)[2]
            set --local icon ""

            switch $ctx_type
                case node
                    set icon "⬢ "
                case python
                    set icon "🐍"
                case go
                    set icon "🐹"
                case rust
                    set icon "🦀"
            end

            if test -n "$icon" -a -n "$ctx_ver"
                set --append parts "$_bgp_color_context$icon$ctx_ver$bgp_color_normal"
            end
        end
    end

    echo -n (string join " " $parts)
end
