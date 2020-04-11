#!/usr/bin/env python
# -*- coding: utf-8 -*-
# L. Penaud (https://github.com/lpenaud/markdown-editor-qt/)

from .thread import Thread

class MDThread(Thread):
    def __init__(self, parent, pathname):
        super(MDThread, self).__init__(parent)
        self.pathname = str(pathname)
        self.sig.connect(parent.cbMDThread)

    def run(self):
        html_text = self.parent().mdrenderer._render_md(self.parent().post["body"])
        file1 = open(self.pathname,"w", encoding='utf-8')     
        file1.write(html_text["html"])
        file1.close()
        self.sig.emit('conversion-end')
