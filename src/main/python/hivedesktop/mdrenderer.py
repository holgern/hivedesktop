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
import pymdownx.smartsymbols
import pymdownx.striphtml
import jinja2
from hivedesktop.mdx_video import VideoExtension
from hivedesktop.mdx_url import UrlExtension
from hivedesktop.mdx_dash import DashExtension
from hivedesktop.mdx_md_in_html import MarkdownInHtmlExtension

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
        with open(path, 'r', encoding='utf-8') as f:
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
            #'markdown.smarty',
            DashExtension(),
            'markdown.extensions.nl2br',
            'markdown.extensions.codehilite',
            'pymdownx.extra',
            'pymdownx.betterem',
            'pymdownx.inlinehilite',
            'pymdownx.smartsymbols',
            # 'markdown_checklist.extension',
            UrlExtension(),
            VideoExtension(),
            'pymdownx.striphtml'
        ]

        md = markdown.Markdown(extensions=extensions, output_format="html5")
        contents = self._add_markdown_tag(contents)
        
        md_html = Markup(md.convert(contents))
        html = jinja2.Template(TEMPLATE).render(content=md_html)
        # html = theme_contents.replace('{{{ contents }}}', md_html)

        return html

    def _add_markdown_tag(self, contents):
        contents = "![]()\n" + contents
        contents = contents.replace('<div class=\\"text-justify\\">', '<div class="text-justify" markdown="block" name="justifiy">')
        contents = contents.replace('<div class=\\"pull-left\\">', '<div class="pull-left" markdown="block" name="pull-left">')
        contents = contents.replace('<div class=\\"pull-right\\">', '<div class="pull-right" markdown="block" name="pull-right">')
        contents = contents.replace('<div class=\\"phishy\\">', '<div class="phishy" markdown="block" name="phishy>')
        
        contents = contents.replace('<div class="text-justify">', '<div class="text-justify" markdown="block" name="justifiy">')
        contents = contents.replace('<div class="pull-left">', '<div class="pull-left" markdown="block" name="pull-left">')
        contents = contents.replace('<div class="pull-right">', '<div class="pull-right" markdown="block" name="pull-right">')
        contents = contents.replace('<div class="phishy">', '<div class="phishy" markdown="block" name="phishy>')
        
        contents = contents.replace("<center>", '<center markdown="block" name="center">')
        contents = contents.replace("<H1>", '<H1 markdown="block">')
        contents = contents.replace("<H2>", '<H2 markdown="block">')
        contents = contents.replace("<H3>", '<H3 markdown="block">')
        contents = contents.replace("<H4>", '<H4 markdown="block">')
        contents = contents.replace("<H5>", '<H5 markdown="block">')
        contents = contents.replace("<H6>", '<H6 markdown="block">')
        contents = contents.replace("<h1>", '<h1 markdown="block">')
        contents = contents.replace("<h2>", '<h2 markdown="block">')
        contents = contents.replace("<h3>", '<h3 markdown="block">')
        contents = contents.replace("<h4>", '<h4 markdown="block">')
        contents = contents.replace("<h5>", '<h5 markdown="block">')
        contents = contents.replace("<h6>", '<h6 markdown="block">')        
        contents = contents.replace('\\"', '"')
        return contents

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
    md = MDRenderer(Path.joinpath(Path.cwd(), 'themes'))
    md_tests_path = Path.joinpath(Path.cwd(), '../../../../md_tests/')
    print(md_tests_path)
    for index in range(1, 10):
        if index < 10:
            md_file1 = Path.joinpath(md_tests_path, 'test0%d.md' % index)
            html_file1 = Path.joinpath(md_tests_path, 'test0%d.html' % index)
        else:
            md_file1 = Path.joinpath(md_tests_path, 'test%d.md' % index)
            html_file1 = Path.joinpath(md_tests_path, 'test%d.html' % index)
            
        
        with open(md_file1, 'r', encoding='utf-8') as f:
            contents = f.read()
        #with open(md2_file1, 'w+', encoding='utf-8') as f:
        #    f.write(md._add_markdown_tag(contents))     
        
        with open(html_file1, 'w+', encoding='utf-8') as f:
            f.write(md.render_path(md_file1)) 


if __name__ == '__main__':
    main()
