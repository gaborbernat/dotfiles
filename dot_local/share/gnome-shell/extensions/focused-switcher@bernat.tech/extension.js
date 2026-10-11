import Clutter from 'gi://Clutter';
import GObject from 'gi://GObject';
import Shell from 'gi://Shell';
import St from 'gi://St';

import * as AltTab from 'resource:///org/gnome/shell/ui/altTab.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

const APP_BINDINGS = [
    'switch-applications',
    'switch-applications-backward',
    'switch-group',
    'switch-group-backward',
];

const FocusedAppSwitcherPopup = GObject.registerClass(
class FocusedAppSwitcherPopup extends AltTab.AppSwitcherPopup {
    _init() {
        super._init();
        this._monitorIndex = global.display.focus_window?.get_monitor() ?? global.display.get_current_monitor();
    }

    vfunc_allocate(box) {
        // GNOME 50 uses the primary monitor for both icon and thumbnail allocation.
        this.set_allocation(box);

        const monitor = Main.layoutManager.monitors[this._monitorIndex] ?? Main.layoutManager.primaryMonitor;
        const themeNode = this.get_theme_node();
        const leftPadding = themeNode.get_padding(St.Side.LEFT);
        const rightPadding = themeNode.get_padding(St.Side.RIGHT);
        const hPadding = leftPadding + rightPadding;
        const childBox = new Clutter.ActorBox();
        const [, height] = this._switcherList.get_preferred_height(monitor.width - hPadding);
        const [, width] = this._switcherList.get_preferred_width(height);

        childBox.x1 = Math.max(monitor.x + leftPadding, monitor.x + Math.floor((monitor.width - width) / 2));
        childBox.x2 = Math.min(monitor.x + monitor.width - rightPadding, childBox.x1 + width);
        childBox.y1 = monitor.y + Math.floor((monitor.height - height) / 2);
        childBox.y2 = childBox.y1 + height;
        this._switcherList.allocate(childBox);

        if (!this._thumbnails)
            return;

        const icon = this._items[this._selectedIndex];
        const [iconX] = icon.get_transformed_position();
        const thumbnailCenter = iconX + icon.width / 2;
        const [, thumbnailWidth] = this._thumbnails.get_preferred_width(-1);
        childBox.x1 = Math.max(monitor.x + leftPadding, Math.floor(thumbnailCenter - thumbnailWidth / 2));
        if (childBox.x1 + thumbnailWidth > monitor.x + monitor.width - hPadding) {
            const offset = childBox.x1 + thumbnailWidth - monitor.width + hPadding;
            childBox.x1 = Math.max(monitor.x + leftPadding, childBox.x1 - offset - hPadding);
        }

        childBox.x2 = Math.min(childBox.x1 + thumbnailWidth, monitor.x + monitor.width - rightPadding);
        childBox.y1 = this._switcherList.allocation.y2 + themeNode.get_length('spacing');
        this._thumbnails.addClones(monitor.y + monitor.height - themeNode.get_padding(St.Side.BOTTOM) - childBox.y1);
        const [, thumbnailHeight] = this._thumbnails.get_preferred_height(-1);
        childBox.y2 = childBox.y1 + thumbnailHeight;
        this._thumbnails.allocate(childBox);
    }
});

export default class FocusedSwitcherExtension extends Extension {
    enable() {
        for (const name of APP_BINDINGS) {
            Main.wm.setCustomKeybindingHandler(name, Shell.ActionMode.NORMAL, (_display, _window, _event, binding) => {
                Main.wm._workspaceSwitcherPopup?.destroy();
                const popup = new FocusedAppSwitcherPopup();
                if (!popup.show(binding.is_reversed(), binding.get_name(), binding.get_mask()))
                    popup.destroy();
            });
        }
    }

    disable() {
        for (const name of APP_BINDINGS)
            Main.wm.setCustomKeybindingHandler(name, Shell.ActionMode.NORMAL, Main.wm._startSwitcher.bind(Main.wm));
    }
}
