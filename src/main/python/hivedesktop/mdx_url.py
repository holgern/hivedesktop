#!/usr/bin/env python

import markdown
from markdown.util import etree


class UrlExtension(markdown.Extension):

    def add_inline(self, md, name, klass, re):
        pattern = klass(re)
        pattern.md = md
        pattern.ext = self
        md.inlinePatterns.add(name, pattern, "<reference")

    def extendMarkdown(self, md, md_globals):
        self.add_inline(md, 'hashtag', Hashtag,
            r'(?<!\/)#(?P<hashid>(?=.*[a-zA-Z]+.*)[a-zA-Z0-9.-]+)')
        self.add_inline(md, 'user', User,
            r'(?<!\/)@(?P<userid>(?=.*[a-zA-Z]+.*)[a-zA-Z0-9.-]+)')
        self.add_inline(md, 'link', Link,
            r'(?<!\]\()(?<!")(?<!\/)https?:\/\/(?![^" ]*(?:jpg|png|gif))(?P<linkid>[^"\'\(\)]*)')
        #self.add_inline(md, 'permlink', PeakdPermlink,
        #    r'(?<!\]\()(?<!")(?<!\/)https?://(www.|)peakd\.com/(?P<peakdpermlinkid1>[a-zA-Z0-9.\-/%:_]+)/@(?P<peakdpermlinkid2>[a-zA-Z0-9\-/\<]+)')        
        #self.add_inline(md, 'steemitimage', SteemitImage,
        #    r'(?<!\]\()(?<!")(?<!\/)https?://(www.|)steemitimages\.com/(?P<steemitimageid>[a-zA-Z0-9.\-/%:_\<]+)')
        #self.add_inline(md, 'hiveimage', HiveImage,
        #    r'(?<!\]\()(?<!")(?<!\/)https?://(www.|)images\.hive\.blog/(?P<hiveimageid>[a-zA-Z0-9.\-/%:_\<]+)')
        self.add_inline(md, 'image', Image,
            r'(?<!\]\()(?<!")(?<!\/)https?:\/\/(?P<imageid>[^"\'@]*\.(?:png|jpg|jpeg|gif|png|svg))')
        self.add_inline(md, 'giphy', Giphy,
            r'(?<!\]\()(?<!")(?<!\/)https?://(www.|)media\.giphy\.com/media/(?P<giphyid>[a-zA-Z0-9.\-/%\<]+)')        


class Hashtag(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = '/trending/%s' % m.group('hashid')
        text = ' #%s' % m.group('hashid')
        return render_url(url, text)


class PeakdPermlink(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://peakd.com/%s/@%s' % (m.group('peakdpermlinkid1'), m.group('peakdpermlinkid2'))
        text = ' %s' % url
        return render_url(url, text)


class Link(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://%s' % m.group('linkid')
        text = ' https://%s' % m.group('linkid')
        return render_url(url, text)


class SteemitImage(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        if m.group('steemitimageid').find("0x0/") > -1:
            url = 'https://images.hive.blog/0x0/%s' % m.group('steemitimageid').split("0x0/")[1]
        else:
            url = 'https://images.hive.blog/0x0/https://cdn.steemitimages.com/%s' % m.group('steemitimageid')
        return render_image(url)


class HiveImage(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        if m.group('hiveimageid').find("0x0/") > -1:
            url = 'https://images.hive.blog/0x0/%s' % m.group('hiveimageid').split("0x0/")[1]
        else:
            url = 'https://images.hive.blog/0x0/https://images.hive.blog/%s' % m.group('hiveimageid')
        return render_image(url)


class Image(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        if m.group('imageid').find("0x0/") > -1:
            url = 'https://%s' % m.group('imageid')
        else:
            url = 'https://images.hive.blog/0x0/https://%s' % m.group('imageid')
        return render_image(url)


class Giphy(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://images.hive.blog/0x0/https://media.giphy.com/media/%s' % m.group('giphyid')
        return render_image(url)


class User(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = '/@%s' % m.group('userid')
        text = ' @%s' % m.group('userid')
        return render_url(url, text)

def render_url(url, text):
    el = etree.Element("a")
    el.set('href', '%s' % (url))
    el.text = text
    return el

def render_image(url):
    el = etree.Element("img")
    el.set('src', '%s' % (url))
    return el

def makeExtension(**kwargs):
    return UrlExtension(**kwargs)


if __name__ == "__main__":
    import doctest
    doctest.testmod()
