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
            r'([^(/]|^)#(?P<hashid>[a-zA-Z0-9.-]+)')
        self.add_inline(md, 'user', User,
            r'([^(/]|^)@(?P<userid>[a-zA-Z0-9.-]+)')
        self.add_inline(md, 'steemitimage', SteemitImage,
            r'([^(/]|^)https?://(www.|)steemitimages\.com/(?P<steemitimageid>[a-zA-Z0-9.-/%:_]+)')
        self.add_inline(md, 'giphy', Giphy,
            r'([^(/]|^)https?://(www.|)media\.giphy\.com/media/(?P<giphyid>[a-zA-Z0-9.-/%]+)')        


class Hashtag(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = '/trending/%s' % m.group('hashid')
        text = ' #%s' % m.group('hashid')
        return render_url(url, text)


class SteemitImage(markdown.inlinepatterns.Pattern):
    def handleMatch(self, m):
        url = 'https://images.hive.blog/0x0/https://cdn.steemitimages.com/%s' % m.group('steemitimageid')
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
