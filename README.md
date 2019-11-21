# Renoir

Renoir – */ˈrɛnwɑːr/* – is a Python templating engine designed with simplicity in mind.

## In a nutshell

```html
{{ extend "layout.html" }}
{{ block title }}Members{{ end }}
{{ block content }}
<ul>
  {{ for user in users: }}
  <li><a href="{{ =user.url }}">{{ =user.username }}</a></li>
  {{ pass }}
</ul>
{{ end }}
```

## Documentation

*The documentation will be soon available under the docs folder.*

## License

Renoir is released under the BSD License.
