"""Small stdlib DOM reader for FilmFreeway's server-rendered metadata."""
from html.parser import HTMLParser


class Element:
    def __init__(self, tag='', attrs=()):
        self.tag = tag
        self.attrs = dict(attrs)
        self.children = []

    def text(self):
        return ' '.join(c.text() if isinstance(c, Element) else c for c in self.children).strip()

    def all(self, tag=None, cls=None, attr=None):
        for child in self.children:
            if not isinstance(child, Element):
                continue
            if ((tag is None or child.tag == tag)
                and (cls is None or cls in child.attrs.get('class', '').split())
                and (attr is None or attr in child.attrs)):
                yield child
            yield from child.all(tag, cls, attr)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element()
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Element(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
                       'link', 'meta', 'param', 'source', 'track', 'wbr'}:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)
