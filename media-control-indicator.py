#!/usr/bin/python
import gi
gi.require_version('Gtk', '3.0')
gi.require_version('AppIndicator3', '0.1')
gi.require_version('Playerctl', '1.0')
gi.require_version('GdkPixbuf', '2.0') 
from gi.repository import Gtk
from colorthief import ColorThief
import io
from gi.repository import AppIndicator3, Gdk, Gio, GLib, GObject, Playerctl
from gi.repository.GdkPixbuf import Pixbuf 
from urllib.request import urlopen
import threading


class media_control_indicator:
    def __init__ (self):
        self.indicator = AppIndicator3.Indicator.new("media_control_indicator", "/usr/share/icons/Adwaita/32x32/actions/media-playback-stop.png", AppIndicator3.IndicatorCategory.SYSTEM_SERVICES)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        
        self.menu = Gtk.Menu()
        self.indicator.set_menu(self.menu)
        
        self.albumartItem = Gtk.MenuItem()
        self.npItem = Gtk.MenuItem("Media control indicator")
        self.playButton = Gtk.ImageMenuItem("Play",image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        self.previousButton = Gtk.ImageMenuItem("Previous",image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PREVIOUS))
        self.nextButton = Gtk.ImageMenuItem("Next",image=Gtk.Image(stock=Gtk.STOCK_MEDIA_NEXT))
        
        self.playButton.connect('activate',self.mediaPlay)
        self.previousButton.connect('activate',self.mediaPrevious)
        self.nextButton.connect('activate',self.mediaNext)
        
        self.albumArt = Gtk.Image()
        self.albumartItem.add(self.albumArt)
        
        self.player = Playerctl.Player()
        
        self.menu.append(self.albumartItem)
        self.menu.append(self.npItem)
        self.menu.append(self.playButton)
        self.menu.append(self.previousButton)
        self.menu.append(self.nextButton)
        
        GLib.timeout_add_seconds(1,self.set_np)
        GLib.timeout_add_seconds(2,self.set_albumArt)
        GLib.timeout_add_seconds(1,self.set_icon)
        GLib.timeout_add_seconds(1,self.set_buttons)
        

    
        self.menu.show_all()
        
        Gtk.main()

    def set_icon(self):
        self.status = self.player.get_property("status")
        if self.status == "Playing":
            self.indicator.set_icon("/usr/share/icons/Adwaita/32x32/actions/media-playback-start.png")
        elif self.status == "Paused":
            self.indicator.set_icon("/usr/share/icons/Adwaita/32x32/actions/media-playback-pause.png")
        else: 
            self.indicator.set_icon("/usr/share/icons/Adwaita/32x32/actions/media-playback-stop.png")
        return GLib.SOURCE_CONTINUE
    
    def set_albumArt(self):
        
        self.albumartThread = threading.Thread(target=self.get_albumArt)
        self.backgroundThread = threading.Thread(target=self.setbg)
        self.albumartThread.start()
        self.backgroundThread.start()
        
        
        return GLib.SOURCE_CONTINUE
        
    def get_albumArt(self):
        try:
            self.albumartData = urlopen(self.player.props.metadata["mpris:artUrl"])
                     
            input_stream = Gio.MemoryInputStream.new_from_data(self.albumartData.read(), None) 
            pixbuf = Pixbuf.new_from_stream(input_stream, None)
            GObject.idle_add(self.updateaImage, pixbuf)
            #self.albumArt.set_from_pixbuf(pixbuf)

        except TypeError or URLError:
            #self.albumArt.clear()
            GObject.idle_add(self.clearImage)
            pass
        return
            
    def updateaImage(self, pix):
        self.albumArt.set_from_pixbuf(pix)
        self.menu.reposition()
        
    def clearImage(self):
        self.albumArt.clear()

            
    def setbg(self):
        try:
            self.albumartData = urlopen(self.player.props.metadata["mpris:artUrl"])   
            self.albumartStream=io.BytesIO(self.albumartData.read())
            color_thief = ColorThief(self.albumartStream)
            dominant_color = color_thief.get_color(quality=1)
            color2 = Gdk.RGBA(red = (dominant_color[0])/255*1, green = (dominant_color[1])/255*1, blue = (dominant_color[2])/255*1, alpha =1)
            color = Gdk.RGBA(red = (dominant_color[0])/255*1, green = (dominant_color[1])/255*1, blue = (dominant_color[2])/255*1, alpha =0.5)
            GObject.idle_add(self.updateBG(color, color2))
            

            #self.playButton.override_background_color(Gtk.StateFlags.NORMAL, color)
            #self.previousButton.override_background_color(Gtk.StateFlags.NORMAL, color)
            #self.nextButton.override_background_color(Gtk.StateFlags.NORMAL, color)
        except TypeError or URLError:
            pass
        return
        
    def updateBG(self, color, color2):
        self.npItem.override_background_color(Gtk.StateFlags.NORMAL, color)
        self.albumartItem.override_background_color(Gtk.StateFlags.NORMAL, color2)

    def set_np(self):
        self.status = self.player.get_property("status")
        try:
            self.npItem.set_label("%s\n%s\n%s" % (self.player.get_title(),self.player.get_album(),self.player.get_artist()))
        except GLib.Error:
            self.npItem.set_label("Media Control Indicator")
        return GLib.SOURCE_CONTINUE
        
    def set_buttons(self):
        self.player = Playerctl.Player()
        self.status = self.player.get_property("status")
        
        if self.status == "Playing":
            self.playButton.set_sensitive(True)
            self.nextButton.set_sensitive(True)
            self.previousButton.set_sensitive(True)
            self.playButton.set_label("Pause")
            self.playButton.set_image(image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PAUSE))
        elif self.status == "Paused":
            self.playButton.set_sensitive(True)
            self.nextButton.set_sensitive(True)
            self.previousButton.set_sensitive(True)
            self.playButton.set_label("Play")
            self.playButton.set_image(image=Gtk.Image(stock=Gtk.STOCK_MEDIA_PLAY))
        else: 
            self.playButton.set_sensitive(False)
            self.nextButton.set_sensitive(False)
            self.previousButton.set_sensitive(False)
        return GLib.SOURCE_CONTINUE

        
    def mediaPlay(self, Widget):
        self.player.play_pause()
        
    def mediaPrevious(self, Widget):
        self.player.previous()
    def mediaNext(self, Widget):
        self.player.next()
        
if __name__ == "__main__":
    imc = media_control_indicator()
    imc.main()
