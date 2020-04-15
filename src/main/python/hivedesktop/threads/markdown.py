#!/usr/bin/env python
# -*- coding: utf-8 -*-
# L. Penaud (https://github.com/lpenaud/markdown-editor-qt/)

from .thread import Thread
import markdown

class MDThread(Thread):
    def __init__(self, parent):
        super(MDThread, self).__init__(parent)
        self.sig.connect(parent.cbMDThread)

    def run(self):
        html_text = self.parent().mdrenderer._render_md(self.parent().post["body"])
        self.sig.emit(html_text)
