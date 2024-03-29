# Renoir

Renoir – */ˈrɛnwɑːr/* – is a Python templating engine designed with simplicity in mind.

[![pip version](https://img.shields.io/pypi/v/renoir.svg?style=flat)](https://pypi.python.org/pypi/Renoir)
[![tests status](https://github.com/emmett-framework/renoir/actions/workflows/tests.yml/badge.svg)](https://github.com/emmett-framework/renoir/actions/workflows/tests.yml)

## In a nutshell

```html
{{ extend "layout.html" }}
{{ block title }}Members{{ end }}
{{ block content }}
<ul>
  {{ for user in users: }}
  <li><a href="{{ =user['url'] }}">{{ =user['name'] }}</a></li>
  {{ pass }}
</ul>
{{ end }}
```

## Documentation

The documentation is available under the [docs folder](https://github.com/emmett-framework/renoir/tree/master/docs).

## License

Renoir is released under the BSD License.
