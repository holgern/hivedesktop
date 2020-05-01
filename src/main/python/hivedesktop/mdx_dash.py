from markdown import Extension
from markdown.inlinepatterns import Pattern
from markdown.inlinepatterns import SimpleTagPattern
from markdown import util

DASH_RE = r'(?<!\| )(?![^| ]*(?: \|))(\-{3})'

class DashExtension(Extension):
    """Adds cite extension to Markdown class"""

    def extendMarkdown(self, md, md_globals):
        """Modifies inline patterns"""
        md.inlinePatterns.add('hr', SimpleTagPattern(DASH_RE, 'hr'), '<not_strong')


def makeExtension(configs={}):
    return DashExtension(configs=dict(configs))


def makeExtension(**kwargs):
    return EmDashExtension(**kwargs)