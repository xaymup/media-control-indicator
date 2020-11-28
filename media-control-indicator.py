#!/usr/bin/python
# Author: Mohamed Alaa <m-alaa8@ubuntu.com>
import gc
import io
import threading
import urllib.request

from colorthief import ColorThief
from gi.repository import AppIndicator3, Gdk, Gio, GLib, Gtk, Playerctl
from gi.repository.GdkPixbuf import InterpType, Pixbuf


class media_control_indicator (Gtk.Application):
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new(
            'media_control_indicator',
            '/usr/share/icons/Adwaita/32x32/actions/media-playback-stop.png',
            AppIndicator3.IndicatorCategory.SYSTEM_SERVICES,
        )
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)

        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)

        self.albumartItem = Gtk.MenuItem()
        self.npItem = Gtk.MenuItem()
        self.playButton = Gtk.ImageMenuItem(
            'Play',
            image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        self.previousButton = Gtk.ImageMenuItem(
            'Previous',
            image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PREVIOUS),
        )
        self.nextButton = Gtk.ImageMenuItem(
            'Next',
            image=Gtk.Image(stock=Gtk.STOCK_MEDIA_NEXT),
        )

        self.playButton.connect('activate', self.mediaPlay)
        self.previousButton.connect('activate', self.mediaPrevious)
        self.nextButton.connect('activate', self.mediaNext)

        self.albumArt = Gtk.Image()
        self.albumartItem.add(self.albumArt)

        self.player = Playerctl.Player()

        self.menu.append(self.albumartItem)
        self.menu.append(self.npItem)
        self.menu.append(self.playButton)
        self.menu.append(self.previousButton)
        self.menu.append(self.nextButton)

        GLib.timeout_add_seconds(1, self.set_np)
        GLib.timeout_add_seconds(1, self.set_icon)
        GLib.timeout_add_seconds(1, self.set_buttons)
        GLib.timeout_add_seconds(1, self.player_handler)
        GLib.timeout_add_seconds(30, self.collect_garbage)

        self.update_album_art(None, None)

        self.menu.show_all()
        Gtk.main()

    def collect_garbage(self):
        gc.collect()
        return GLib.SOURCE_CONTINUE

    def player_handler(self):
        try:
            self.player.on('metadata', self.update_album_art)
        except GLib.Error:
            self.menu.set_size_request(0, 0)
            self.menu.reposition()
            pass
        return GLib.SOURCE_CONTINUE

    def set_icon(self):
        self.status = self.player.get_property('status')
        if self.status == 'Playing':
            self.indicator.set_icon('/usr/share/icons/Adwaita/32x32/actions/media-playback-start.png')
        elif self.status == 'Paused':
            self.indicator.set_icon('/usr/share/icons/Adwaita/32x32/actions/media-playback-pause.png')
        else:
            self.indicator.set_icon('/usr/share/icons/Adwaita/32x32/actions/media-playback-stop.png')
        return GLib.SOURCE_CONTINUE

    def update_album_art(self, args, widget):
        self.getalbumartThread = threading.Thread(target=self.get_album_art)
        self.getalbumartThread.start()

    def get_album_art(self):
        try:
            self.albumartData = urllib \
                .request.urlopen(self.player.props.metadata['mpris:artUrl']).read()
            self.setbgThread = threading.Thread(target=self.set_bg)
            self.setalbumartThread = threading.Thread(target=self.set_albumart)
            self.setbgThread.start()
            self.setalbumartThread.start()
            self.albumartItem.show()
        except (TypeError, KeyError, urllib.request.URLError) as e:
            self.albumartItem.hide()

    def set_albumart(self):
        inputStream = Gio.MemoryInputStream \
            .new_from_data(self.albumartData, None)
        pixbuf = Pixbuf.new_from_stream(inputStream, None)
        pixbuf = pixbuf.scale_simple(180, 180, InterpType.BILINEAR)
        GLib.idle_add(self.apply_albumart, pixbuf)

    def apply_albumart(self, pixbuf):
        self.albumArt.set_from_pixbuf(pixbuf)
        self.menu.set_size_request(0, 320)
        self.menu.reposition()
        return False

    def set_bg(self):
        self.albumartStream = io.BytesIO(self.albumartData)
        dominantColor = ColorThief(self.albumartStream).get_color(quality=1)
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
        self.npItem.override_background_color(Gtk.StateFlags.NORMAL, color)
        self.albumartItem.override_background_color(
            Gtk.StateFlags.NORMAL,
            color2,
        )

    def set_np(self):
        try:
            self.npItem.set_label('%s\n%s\n%s' % (
                self.player.get_title(),
                self.player.get_album(),
                self.player.get_artist(),
            ))
            if self.npItem.get_label().isspace() == False:
                self.npItem.show()
            else:
                self.npItem.hide()
                self.menu.set_size_request(0, 0)
                self.menu.reposition()
        except GLib.Error:
            pass
        return GLib.SOURCE_CONTINUE

    def set_buttons(self):
        self.player = Playerctl.Player()
        self.status = self.player.get_property('status')
        if self.status == 'Playing':
            self.playButton.set_sensitive(True)
            self.nextButton.set_sensitive(True)
            self.previousButton.set_sensitive(True)
            self.playButton.set_label('Pause')
            self.playButton.set_image(image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PAUSE))
        elif self.status == 'Paused':
            self.playButton.set_sensitive(True)
            self.nextButton.set_sensitive(True)
            self.previousButton.set_sensitive(True)
            self.playButton.set_label('Play')
            self.playButton.set_image(image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        else:
            self.playButton.set_sensitive(False)
            self.nextButton.set_sensitive(False)
            self.previousButton.set_sensitive(False)
            self.npItem.hide()
            self.albumartItem.hide()
        return GLib.SOURCE_CONTINUE

    def mediaPlay(self, Widget):
        self.player.play_pause()

    def mediaPrevious(self, Widget):
        self.player.previous()

    def mediaNext(self, Widget):
        self.player.next()

if __name__ == '__main__':
    imc = media_control_indicator()
    imc.main()
