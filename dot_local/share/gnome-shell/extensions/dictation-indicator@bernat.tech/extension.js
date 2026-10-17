import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';

import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

export default class DictationIndicatorExtension extends Extension {
    enable() {
        this._recording = Gio.File.new_for_path(`${GLib.get_user_runtime_dir()}/dictate.pid`);
        this._badge = new St.BoxLayout({style_class: 'dictation-recording-badge', width: 162, height: 48});
        this._badge.add_child(new St.Icon({icon_name: 'media-record-symbolic', icon_size: 20,
            style_class: 'dictation-recording-icon'}));
        this._badge.add_child(new St.Label({text: 'Recording'}));
        this._badge.hide();
        Main.layoutManager.addChrome(this._badge, {affectsStruts: false, trackFullscreen: true});

        this._monitor = this._recording.get_parent().monitor_directory(Gio.FileMonitorFlags.NONE, null);
        this._monitorId = this._monitor.connect('changed', (_monitor, file) => {
            if (file.get_basename() === 'dictate.pid')
                this._update();
        });
        this._focusId = global.display.connect('notify::focus-window', () => this._update());
        this._layoutId = Main.layoutManager.connect('monitors-changed', () => this._update());
        this._update();
    }

    _update() {
        if (!this._recording.query_exists(null)) {
            this._badge.hide();
            return;
        }

        const index = global.display.focus_window?.get_monitor() ?? Main.layoutManager.primaryIndex;
        const monitor = Main.layoutManager.monitors[index] ?? Main.layoutManager.primaryMonitor;
        if (!monitor)
            return;
        this._badge.set_position(Math.round(monitor.x + (monitor.width - this._badge.width) / 2),
            Math.round(monitor.y + (monitor.height - this._badge.height) / 2));
        this._badge.show();
    }

    disable() {
        this._monitor.disconnect(this._monitorId);
        this._monitor.cancel();
        global.display.disconnect(this._focusId);
        Main.layoutManager.disconnect(this._layoutId);
        Main.layoutManager.removeChrome(this._badge);
        this._badge.destroy();
        this._badge = null;
        this._monitor = null;
        this._recording = null;
    }
}
