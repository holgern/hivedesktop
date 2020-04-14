#!/usr/bin/env python

import markdown
from markdown.util import etree


class VideoExtension(markdown.Extension):
    def __init__(self, **kwargs):
        self.config = {
            'dailymotion_width': ['480', 'Width for Dailymotion videos'],
            'dailymotion_height': ['270', 'Height for Dailymotion videos'],
            'metacafe_width': ['440', 'Width for Metacafe videos'],
            'metacafe_height': ['248', 'Height for Metacafe videos'],
            'vimeo_width': ['500', 'Width for Vimeo videos'],
            'vimeo_height': ['281', 'Height for Vimeo videos'],
            'twitch_width': ['640', 'Width for Twitch videos'],
            'twitch_height': ['480', 'Height for Twitch videos'],
            'threespeak_width': ['640', 'Width for ThreeSpeak videos'],
            'threespeak_height': ['480', 'Height for ThreeSpeak videos'],            
            'yahoo_width': ['624', 'Width for Yahoo! videos'],
            'yahoo_height': ['351', 'Height for Yahoo! videos'],
            'youtube_width': ['560', 'Width for Youtube videos'],
            'youtube_height': ['315', 'Height for Youtube videos'],
        }

        # Override defaults with user settings
        for key, value in kwargs.items():
            self.setConfig(key, str(value))

    def add_inline(self, md, name, klass, re):
        pattern = klass(re)
        pattern.md = md
        pattern.ext = self
        md.inlinePatterns.add(name, pattern, "<reference")

    def extendMarkdown(self, md, md_globals):
        self.add_inline(md, 'dailymotion', Dailymotion,
            r'([^(]|^)https?://www\.dailymotion\.com/video/(?P<dailymotionid>[a-zA-Z0-9]+)(_[\w\-]*)?')
        self.add_inline(md, 'metacafe', Metacafe,
            r'([^(]|^)http://www\.metacafe\.com/watch/(?P<metacafeid>\d+)/?(:?.+/?)')
        self.add_inline(md, 'vimeo', Vimeo,
            r'([^(]|^)https?://(www.|)vimeo\.com/(?P<vimeoid>\d+)\S*')
        self.add_inline(md, 'twitch', Twitch,
            r'([^(]|^)https?://(www.|)twitch\.tv/(?P<twitchid>\d+)\S*') 
        self.add_inline(md, 'threespeak', ThreeSpeak,
            r'([^(]|^)https?://(www.|)3speak\.online/watch\?\S*v=(?P<threespeakid>\S[^&/]+)')    
        self.add_inline(md, 'yahoo', Yahoo,
            r'([^(]|^)http://screen\.yahoo\.com/.+/?')
        self.add_inline(md, 'youtube', Youtube,
            r'([^(]|^)https?://www\.youtube\.com/watch\?\S*v=(?P<youtubeid>\S[^&/]+)')
        self.add_inline(md, 'youtube_short', Youtube,
            r'([^(]|^)https?://youtu\.be/(?P<youtubeid>\S[^?&/]+)?')


class Dailymotion(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://www.dailymotion.com/embed/video/%s' % m.group('dailymotionid')
        width = self.ext.config['dailymotion_width'][0]
        height = self.ext.config['dailymotion_height'][0]
        return render_iframe(url, width, height)


class Metacafe(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://www.metacafe.com/embed/%s/' % m.group('metacafeid')
        width = self.ext.config['metacafe_width'][0]
        height = self.ext.config['metacafe_height'][0]
        return render_iframe(url, width, height)



class Vimeo(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://player.vimeo.com/video/%s' % m.group('vimeoid')
        width = self.ext.config['vimeo_width'][0]
        height = self.ext.config['vimeo_height'][0]
        return render_iframe(url, width, height)


class Twitch(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://player.twitch.tv/video/%s' % m.group('twitchid')
        width = self.ext.config['twitch_width'][0]
        height = self.ext.config['twitch_height'][0]
        return render_iframe(url, width, height)


class ThreeSpeak(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://3speak.online/embed?v=%s' % m.group('threespeakid')
        width = self.ext.config['threespeak_width'][0]
        height = self.ext.config['threespeak_height'][0]
        return render_iframe(url, width, height)


class Yahoo(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = m.string + '?format=embed&player_autoplay=false'
        width = self.ext.config['yahoo_width'][0]
        height = self.ext.config['yahoo_height'][0]
        return render_iframe(url, width, height)


class Youtube(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://www.youtube.com/embed/%s' % m.group('youtubeid')
        width = self.ext.config['youtube_width'][0]
        height = self.ext.config['youtube_height'][0]
        return render_iframe(url, width, height)


def render_iframe(url, width, height):
    iframe = etree.Element('iframe')
    iframe.set('width', width)
    iframe.set('height', height)
    iframe.set('src', url)
    iframe.set('allowfullscreen', 'true')
    iframe.set('frameborder', '0')
    return iframe


def makeExtension(**kwargs):
    return VideoExtension(**kwargs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
