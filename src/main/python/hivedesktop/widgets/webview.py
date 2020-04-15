#!/usr/bin/env python
# -*- coding: utf-8 -*-


from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEnginePage, QWebEngineSettings
from PyQt5.Qt import QSizePolicy, QUrl
from PyQt5.QtGui import QDesktopServices


class WebEnginePage(QWebEnginePage):
    def acceptNavigationRequest(self, url,  _type, isMainFrame):
        if _type == QWebEnginePage.NavigationTypeLinkClicked:
            QDesktopServices.openUrl(url);
            return False
        return True


class WebView(QWebEngineView):
    """docstring for WebView."""
    def __init__(self, parent = None):
        super(WebView, self).__init__(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setPage(WebEnginePage(self))
        self.page().settings().setAttribute(QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
        self.page().settings().setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        # self.page().settings().setAttribute(QWebEngineSettings.AllowRunningInsecureContent, True)
        self.page().settings().setAttribute(QWebEngineSettings.PluginsEnabled, True)
        self.page().fullScreenRequested.connect(lambda request: request.accept())
        self.__html = ''

    @property
    def html(self):
        return self.__html

    @html.setter
    def html(self, html):
        self.__html = html
        self.setHtml(html)

    @property
    def url(self):
        return super(WebView, self).url().toString()

    @url.setter
    def url(self, url):
        self.setUrl(QUrl(url))


