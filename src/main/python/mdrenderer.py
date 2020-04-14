#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Taken partly from https://github.com/fboender/mdpreview/blob/master/mdpreview

from pathlib import Path
import markdown
import requests
import logging
import os
from markdown import Extension
from markdown.util import etree
from markdown.inlinepatterns import Pattern
from markupsafe import Markup
import pymdownx
import pymdownx.extra
import pymdownx.magiclink
import pymdownx.betterem
import pymdownx.inlinehilite
import pymdownx.snippets
import pymdownx.superfences
import pymdownx.highlight
import jinja2
from mdx_video import VideoExtension

TEMPLATE = """<!DOCTYPE html>
<html>
<head>
    <link href="http://netdna.bootstrapcdn.com/twitter-bootstrap/2.3.0/css/bootstrap-combined.min.css" rel="stylesheet">
    <style>
        body {
            font-family: sans-serif;
        }
        code, pre {
            font-family: monospace;
        }
        h1 code,
        h2 code,
        h3 code,
        h4 code,
        h5 code,
        h6 code {
            font-size: inherit;
        }
    </style>
</head>
<body>
<div class="container">
{{content}}
</div>
</body>
</html>
"""

# Setup logging
level = logging.WARNING
log = logging.getLogger("hivedesktop")
log.setLevel(level)
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s %(levelname)8s %(name)s | %(message)s')
ch.setFormatter(formatter)
log.addHandler(ch)


# Urlize markdown extensions taken from https://github.com/r0wb0t/markdown-urlize
# Copyright: 2-clause BSD license.
# Covers all Urlize* classes.

# Global Vars
URLIZE_RE = '(%s)' % '|'.join([
    r'<(?:f|ht)tps?://[^>]*>',
    r'\b(?:f|ht)tps?://[^)<>\s]+[^.,)<>\s]',
    r'\bwww\.[^)<>\s]+[^.,)<>\s]',
    r'[^(<\s]+\.(?:com|net|org)\b',
])

class UrlizePattern(markdown.inlinepatterns.Pattern):
    """ Return a link Element given an autolink (`http://example/com`). """
    def handleMatch(self, m):
        url = m.group(2)

        if url.startswith('<'):
            url = url[1:-1]

        text = url

        if not url.split('://')[0] in ('http','https','ftp'):
            if '@' in url and not '/' in url:
                url = 'mailto:' + url
            else:
                url = 'http://' + url

        el = markdown.util.etree.Element("a")
        el.set('href', url)
        el.text = markdown.util.AtomicString(text)
        return el


class UrlizeExtension(markdown.Extension):
    """ Urlize Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Replace autolink with UrlizePattern """
        md.inlinePatterns['autolink'] = UrlizePattern(URLIZE_RE, md)



class MDRenderer(object):
    """
    Render Markdown to HTML according to a theme.
    """
    def __init__(self, theme_dir, default_theme="github"):
        self.theme_dir = theme_dir
        self.default_theme = default_theme

    def get_theme_path(self, theme):
        """
        Return the full path to the theme `theme`. This is either a relative or
        absolute path if `theme` points to an existing file, or the path to oen
        of the built-in themes.
        """
        if os.path.isfile(theme):
            # Theme points to an existing file
            theme_path = theme
        else:
            theme_fname = theme + '.html'
            theme_path = os.path.join(self.theme_dir, theme_fname)
        if not os.path.isfile(theme_path):
            raise IOError("Not a valid theme file: '{}'".format(theme_path))
        return theme_path

    def render_path(self, path, theme=None):
        """
        Render the contents of local file `path` according to `theme` (or the
        default theme). If you need to render a URI ('file://' or
        'http(s);//'), use MDRenderer.render_url() instead.
        """
        log.info("Rendering path '{}' with theme '{}'".format(path, theme))
        with open(path, 'r') as f:
            md_contents = f.read()
        return(self._render_md(md_contents, theme))

    def render_url(self, url, theme=None):
        """
        Render the contents of url `url` according to `theme` (or the default
        theme). If you need to render a local path (not 'file://' or
        'http(s);//'), use MDRenderer.render_path() instead.
        """
        log.info("Rendering url '{}'".format(url))
        r = requests.get(url)
        md_contents = r.text
        return(self._render_md(md_contents, theme))

    def _render_md(self, contents, theme=None):
        # theme_contents = self._read_theme(theme)
        extensions = [
            #'toc',
            #'tables',
            #'extra',
            #'footnotes',
            #'md_in_html',
            #'fenced_code',
            #'smarty',
            'markdown.extensions.nl2br',
            'markdown.extensions.codehilite',
            'pymdownx.extra',
            'pymdownx.magiclink',
            'pymdownx.betterem',
            'pymdownx.inlinehilite',
            'pymdownx.snippets',
            # 'markdown_checklist.extension',
            # UrlizeExtension(),
            VideoExtension(),
        ]
        md = markdown.Markdown(extensions=extensions, output_format="html5")
        contents = contents.replace("<center>", "").replace("</center>", "")
        
        md_html = Markup(md.convert(contents))
        html = jinja2.Template(TEMPLATE).render(content=md_html)
        # html = theme_contents.replace('{{{ contents }}}', md_html)

        return html

    def _read_theme(self, theme):
        """
        Load theme from disk.
        """
        if theme is None:
            theme = self.default_theme
        theme_path = self.get_theme_path(theme)
        theme_contents = open(theme_path, 'r').read()
        return theme_contents


def main():
    src = '# This is a h1\nhttps://youtu.be/abc\n\nhttps://3speak.online/watch?v=taskmaster4450/mhggbzju'
    md = MDRenderer(Path.joinpath(Path.cwd(), 'themes'))
    print(md._render_md(src))


if __name__ == '__main__':
    main()
