Getting started
===============

Ready to get started with Renoir? This guide gives a good introduction to the engine.

Rendering a simple template
---------------------------

A Renoir template is simply a text file. Renoir can generate any text-based format (HTML, XML, CSV, etc.); it doesn't matter which extension your file have, any extension is just fine.

First thing to do is initializing a Renoir instance:

```python
from renoir import Renoir

templates = Renoir()
```

By default, Renoir it will look at the current working path for the template files. So, let's add our *example.html* file in the same directory:

```html
<html lang="en">
<head>
    <title>My Webpage</title>
</head>
<body>
    {{ =message }}
</body>
</html>
```

As you can see we added the `message` variable in the body, that will be rendered using the *context* we pass to Renoir during the rendering process:

```python
templates.render('example.html', {'message': 'Hello world!'})
```

Using Python in your templates
------------------------------

Renoir doesn't implement any proprietary syntax in templates: you won't need to leard about *filters* or other tools since everything inside the curly braces is evaluated as normal Python code.

This means you can use anything from the standard library or the context you pass to the engine inside your templates:

```html
<div class="posts">
    {{ for idx, post in enumerate(posts): }}
    {{ cssclass = 'white' if idx % 0 else 'gray' }}
    <div class="post {{ =cssclass }}">
        <p>{{ =post['text'] }}</p>
    </div>
    {{ pass }}
</div>
```

As you can see the two notable differences we get comparing the code to a standard Python script are the `=` notation to tell Renoir to render the variable and the `pass` instruction at the end of the `for` block.  Normally, Python uses indentation to get where code blocks end, but the template is not structured the same way and just undoing the indentation would be ambiguous: so we need write `pass` to tell Renoir where the block ends.

Template inheritance
---------------------

Renoir provides template inheritance, allowing you to build skeletons and blocks that child templates can override. Let's say we build our skeleton in *layour.html* file:

```html
<!DOCTYPE html>
<html lang="en">
<head>
    {{ block head }}
    <link rel="stylesheet" href="style.css" />
    <title>{{ block title }}{{ end }} - My Webpage</title>
    {{ end }}
</head>
<body>
    <div id="content">
        {{ block main }}
        {{ include }}
        {{ end }}
    </div>
    <div id="footer">
        {{ block footer }}
        Copyright 2020 by you.
        {{ end }}
    </div>
</body>
</html>
```

Then we can build a child template in *index.html* file:

```html
{{ extend "layout.html" }}

{{ block title }}Index{{ end }}
{{ block head }}
    {{ super }}
    <style type="text/css">
        .title { color: #336699; }
    </style>
{{ end }}

<h1>Index</h1>
<p class="title">
    Welcome to my awesome homepage.
</p>
```

Template context
----------------

Since context get shared across all the templates you might include or extend, you can also change it directly inside the templates. For instance, we can rewrite the inheritance example like this:

```html
{{ title = locals().get('title')}}
{{ hide_footer = locals().get('hide_footer', False) }}

<!DOCTYPE html>
<html lang="en">
<head>
    {{ block head }}
    <link rel="stylesheet" href="style.css" />
    <title>{{ =title }} - My Webpage</title>
    {{ end }}
</head>
<body>
    <div id="content">
        {{ block main }}
        {{ include }}
        {{ end }}
    </div>
    {{ if not hide_footer: }}
    <div id="footer">
        {{ block footer }}
        Copyright 2020 by you.
        {{ end }}
    </div>
    {{ pass }}
</body>
</html>
```

Then your pages can define the variables before extending:

```html
{{ title = 'Index' }}
{{ hide_footer = True }}

{{ extend "layout.html" }}

{{ block head }}
    {{ super }}
    <style type="text/css">
        .title { color: #336699; }
    </style>
{{ end }}

<h1>Index</h1>
<p class="title">
    Welcome to my awesome homepage.
</p>
```

Escaping
--------

It is sometimes desirable – even necessary – to have Renoir ignore parts it would otherwise handle as Python code. For example, if, with the default syntax, you want to use curly braces as a raw string in a template and not start Python evaluation, you can use the `raw` block:

```html
<!-- this gets processed -->
{{ =message }}
<!-- this not -->
{{ raw }}
{{ =message }}
{{ end }}
```
