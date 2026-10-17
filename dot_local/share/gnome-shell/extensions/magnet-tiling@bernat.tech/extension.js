import Meta from 'gi://Meta';
import Shell from 'gi://Shell';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const BINDINGS = {
    'toggle-tiled-left': window => tileToward(window, Meta.DisplayDirection.LEFT),
    'toggle-tiled-right': window => tileToward(window, Meta.DisplayDirection.RIGHT),
    'maximize': window => window.maximize(),
    'unmaximize': window => restore(window),
};
// Terminals resize in cell steps, so a tiled window rarely matches the half-screen rectangle exactly.
const SLACK = 64;

const states = new WeakMap();

function tileToward(window, direction) {
    const monitor = window.get_monitor();
    const state = states.get(window);
    if (state?.direction === direction && fills(window, monitor, direction)) {
        const neighbor = global.display.get_monitor_neighbor_index(monitor, direction);
        if (neighbor >= 0) {
            window.move_to_monitor(neighbor);
            tile(window, neighbor, direction === Meta.DisplayDirection.LEFT
                ? Meta.DisplayDirection.RIGHT
                : Meta.DisplayDirection.LEFT);
        }
        return;
    }
    tile(window, monitor, direction);
}

function tile(window, monitor, side) {
    if (window.is_fullscreen()) {
        const signal = window.connect('notify::fullscreen', () => {
            if (window.is_fullscreen())
                return;
            window.disconnect(signal);
            tile(window, monitor, side);
        });
        window.unmake_fullscreen();
        return;
    }
    if (window.is_maximized())
        window.unmaximize();
    if (!states.has(window))
        states.set(window, {restore: window.get_frame_rect()});
    const {x, y, width, height} = halfOf(window, monitor, side);
    window.move_resize_frame(true, x, y, width, height);
    states.get(window).direction = side;
}

function restore(window) {
    if (window.is_fullscreen()) {
        window.unmake_fullscreen();
        return;
    }
    if (window.is_maximized()) {
        window.unmaximize();
        return;
    }
    const state = states.get(window);
    if (!state?.restore)
        return;
    states.delete(window);
    const {x, y, width, height} = state.restore;
    window.move_resize_frame(true, x, y, width, height);
}

function halfOf(window, monitor, side) {
    const area = window.get_work_area_for_monitor(monitor);
    const left = Math.floor(area.width / 2);
    return side === Meta.DisplayDirection.LEFT
        ? {x: area.x, y: area.y, width: left, height: area.height}
        : {x: area.x + left, y: area.y, width: area.width - left, height: area.height};
}

function fills(window, monitor, side) {
    const frame = window.get_frame_rect();
    const half = halfOf(window, monitor, side);
    return Math.abs(frame.x - half.x) <= SLACK && Math.abs(frame.y - half.y) <= SLACK &&
        Math.abs(frame.width - half.width) <= SLACK && Math.abs(frame.height - half.height) <= SLACK;
}

export default class MagnetTilingExtension extends Extension {
    enable() {
        for (const [name, action] of Object.entries(BINDINGS)) {
            Main.wm.setCustomKeybindingHandler(name, Shell.ActionMode.NORMAL, (_display, window) => {
                const target = window ?? global.display.focus_window;
                if (target?.get_window_type() === Meta.WindowType.NORMAL &&
                    (target.is_fullscreen() || target.allows_resize()))
                    action(target);
            });
        }
    }

    disable() {
        for (const name of Object.keys(BINDINGS))
            Meta.keybindings_set_custom_handler(name, null);
    }
}
