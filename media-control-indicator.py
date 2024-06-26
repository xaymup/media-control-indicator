#!/usr/bin/python
# Author: Mohamed Alaa <m-alaa8@ubuntu.com>
import gc
import io
import threading
import urllib.request

import gi
from colorthief import ColorThief

from PIL import Image

gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Playerctl', '2.0')

from gi.repository import AppIndicator3, Gdk, Gio, GLib, Gtk, Playerctl
from gi.repository.GdkPixbuf import InterpType, Pixbuf


class MediaControlIndicator(Gtk.Application):
    def __init__(self):
        self.status = None
        self.albumart_data = None

        self.indicator = AppIndicator3.Indicator.new(
            'media_control_indicator',
            'media-playback-stop',
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)

        self.albumart_item = Gtk.MenuItem()
        self.np_item = Gtk.MenuItem()
        self.play_button = Gtk.ImageMenuItem(
            label='Play',
            image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        self.next_button = Gtk.ImageMenuItem(
            label='Next',
            image=Gtk.Image(stock=Gtk.STOCK_MEDIA_NEXT),
        )
        self.previous_button = Gtk.ImageMenuItem(
            label='Previous',
            image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PREVIOUS),
        )
        self.quit_button = Gtk.ImageMenuItem(
            label='Quit',
            image=Gtk.Image(stock=Gtk.STOCK_QUIT),
        )

        self.play_button.connect('activate', self.media_play)
        self.next_button.connect('activate', self.media_next)
        self.previous_button.connect('activate', self.media_previous)
        self.quit_button.connect('activate', self.quit)  # connect quit button

        # toggle play / pause on middle click
        self.indicator.set_secondary_activate_target(self.play_button)

        self.album_art = Gtk.Image()
        self.albumart_item.add(self.album_art)

        self.player = Playerctl.Player()

        self.menu.append(self.albumart_item)
        self.menu.append(self.np_item)
        self.menu.append(self.play_button)
        self.menu.append(self.next_button)
        self.menu.append(self.previous_button)
        self.menu.append(self.quit_button)

        GLib.timeout_add_seconds(1, self.set_np)
        GLib.timeout_add_seconds(1, self.set_icon)
        GLib.timeout_add_seconds(1, self.set_buttons)
        GLib.timeout_add_seconds(1, self.player_handler)
        GLib.timeout_add_seconds(30, self.collect_garbage)

        self.update_album_art(None, None)

        self.menu.show_all()
        Gtk.main()

    @staticmethod
    def collect_garbage():
        gc.collect()
        return GLib.SOURCE_CONTINUE

    def player_handler(self):
        try:
            self.player.connect('metadata', self.update_album_art)
        except GLib.Error:
            self.menu.set_size_request(0, 0)
            self.menu.reposition()
        return GLib.SOURCE_CONTINUE

    def set_icon(self):
        self.status = self.player.get_property('status')
        if self.status == 'Playing':
            self.indicator.set_icon_full('media-playback-start', 'Playing')
        elif self.status == 'Paused':
            self.indicator.set_icon_full('media-playback-pause', 'Paused')
        else:
            self.indicator.set_icon_full('media-playback-stop', 'Stopped')
        return GLib.SOURCE_CONTINUE

    def update_album_art(self, *args, **kwargs):
        threading.Thread(target=self.get_album_art).start()

    def get_album_art(self):
        try:
            self.status = self.player.get_property('status')
#            print(self.player.props)
            if(self.status):
#            print(self.player.props.metadata['mpris:artUrl'])
                self.albumart_data = urllib \
                    .request.urlopen(self.player.props.metadata['mpris:artUrl']) \
                    .read()
                threading.Thread(target=self.set_bg).start()
                threading.Thread(target=self.set_albumart).start()
                self.albumart_item.show()
            else:
                self.albumart_item.hide()
        except (TypeError, KeyError, urllib.request.URLError):
            self.albumart_item.hide()

    def set_albumart(self):
        inputStream = Gio.MemoryInputStream \
            .new_from_data(self.albumart_data, None)
        pixbuf = Pixbuf.new_from_stream(inputStream, None)

        file = self.player.props.metadata['mpris:artUrl'][7:]
        w, h = Image.open(file).size
        pixbuf = pixbuf.scale_simple(180 * w / h, 180, InterpType.BILINEAR)
        GLib.idle_add(self.apply_albumart, pixbuf)

    def apply_albumart(self, pixbuf):
        self.album_art.set_from_pixbuf(pixbuf)
        self.menu.set_size_request(0, 320)
        self.menu.reposition()
        return False

    def set_bg(self):
        albumartStream = io.BytesIO(self.albumart_data)
        dominantColor = ColorThief(albumartStream).get_color(quality=1)
        color2 = Gdk.RGBA(
            red=(dominantColor[0]) / 255 * 1,
            green=(dominantColor[1]) / 255 * 1,
            blue=(dominantColor[2]) / 255 * 1,
            alpha=1,
        )
        color = Gdk.RGBA(
            red=(dominantColor[0]) / 255 * 1,
            green=(dominantColor[1]) / 255 * 1,
            blue=(dominantColor[2]) / 255 * 1,
            alpha=0.5,
        )
        GLib.idle_add(self.apply_bg, color, color2)

    def apply_bg(self, color, color2):
        self.np_item.override_background_color(Gtk.StateFlags.NORMAL, color)
        self.albumart_item.override_background_color(
            Gtk.StateFlags.NORMAL,
            color2,
        )

    def set_np(self):
        try:
            self.np_item.set_label('%s\n%s\n%s' % (
                self.player.get_title(),
                self.player.get_album(),
                self.player.get_artist(),
            ))
            if not self.np_item.get_label().isspace():
                self.np_item.show()
            else:
                self.np_item.hide()
                self.menu.set_size_request(0, 0)
                self.menu.reposition()
        except GLib.Error:
            pass
        return GLib.SOURCE_CONTINUE

    def set_buttons(self):
        self.player = Playerctl.Player()
        self.status = self.player.get_property('status')
        if self.status == 'Playing':
            self.play_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.previous_button.set_sensitive(True)
            self.play_button.set_label('Pause')
            self.play_button \
                .set_image(image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PAUSE))
        elif self.status == 'Paused':
            self.play_button.set_sensitive(True)
            self.next_button.set_sensitive(True)
            self.previous_button.set_sensitive(True)
            self.play_button.set_label('Play')
            self.play_button \
                .set_image(image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        else:
            self.play_button.set_sensitive(False)
            self.next_button.set_sensitive(False)
            self.previous_button.set_sensitive(False)
            self.np_item.hide()
            self.albumart_item.hide()
        return GLib.SOURCE_CONTINUE

    def media_play(self, *args, **kwargs):
        self.player.play_pause()

    def media_previous(self, *args, **kwargs):
        self.player.previous()

    def media_next(self, *args, **kwargs):
        self.player.next()

    def quit(self, *args, **kwargs):  # quit method
        Gtk.main_quit()


if __name__ == '__main__':
    MediaControlIndicator()
