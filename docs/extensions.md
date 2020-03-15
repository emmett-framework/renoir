Extensions
==========

Renoir extensions extend the functionality of Renoir in various different ways.

Extensions are Python packages that can be downloaded with `pip`. When adding extensions to your application, it is a good habit to declare them as dependencies in your *requirements.txt* or *setup.py* file: this way, they can be installed with a simple command or when your application installs.

Using extensions
----------------

An extension typically has accompanying documentation that shows how to use it correctly. In general, Renoir extensions should be named with the format `renoir-foo` and have a package-name like `renoir_foo`, replacing foo with the desired name. If the extension is written according to the suggested pattern, using it in your  application will be quite easy:

```python
from renoir import Renoir
from renoir_foo import Foo

renoir = Renoir()

# add the extension to our renoir instance
foo = renoir.use_extension(Foo, some_config_param="something")
```

That's all.


Building extensions
-------------------

The first step in creating a new extension for Renoir is writing an `Extension` subclass:

```python
from renoir.extensions import Extension

class Awesomeness(Extension):
    default_config = {}

    def on_load(self):
        # pass
```

As you can see, the `Extension` class in actually quite simple, since you just have to write down the default configuration (if needed) and override the `on_load` method, that will be called by the framework when the extension will be initialised.

You can access three attributes of the extension instance, that are injected by Renoir before calling the `on_load` method, in particular you will have:

| attribute | description |
| --- | --- |
| templater | the Renoir instance on which the extension is loaded |
| config | an `adict` containing the configuration |
| env | an `adict` reserved to the extension where data can be stored |

The `config` attribute will contain the configuration defined by the developer using the extension, with the default attributes you defined in the `default_config` if not specified differently.

Renoir uses the name of your class as namespace for the configuration and environment objects. If you want to specify a different namespace, you can use the relevant attribute:

```python
class Awesomeness(Extension):
    namespace = "Foobar"
```

Now, let's see how to build an extension with an example: in particular, we want to build an extension that adds [Haml](http://weppy.org/extensions/haml) support to Renoir. Then we need to write a template extension that interact with templates with an *.haml* file extension and that provides the compiled html source in order to let Renoir understand the templates. We can start by writing:

```python
from renoir import Extension

class Haml(Extension):
    file_extension = '.haml' 
```

Then we can use three different methods provided by the `Extension` class:

- the `load` method, that should accept a path and a filename and return the same tuple, useful to alter the standard template names Renoir looks for;
- the `render` method, that should accept the source code and file name variables and return the source code that should be used by Renoir;
- the `context` method, that should accept a context dictionary and can add methods and variable to it.

Let's say we want to compile the haml templates in html ones when Renoir looks for them, so we can just tell Renoir to use the generated html files one. The simplest way to do that is to override the `preload` method in order to change the extension of the file:

```python
from renoir import Extension

class Haml(Extension):
    file_extension = '.haml'
    
    def preload(self, path, file_name):
        # file_name will be like "somefile.haml"
        self.compile(path, file_name)
        return path, file_name + ".html" 
```

where the `compile` method will be the one responsible to parse the haml code and produce compatible html for Renoir.

### Lexers

Template extensions can also register *lexers*, which are the keyword used by Renoir in templates to render specific contents. 

<!-- For example, the standard `include_static` keyword is a lexer that produce the appropriate `<link>` or `<script>` html objects. -->

In order to create a new lexer, you have to use the `Lexer` class provided by Renoir. Let's say we want to create a shortcut to include images from some folder using this notation:

```html
<div>
    {{ img 'foo.png' }}
</div>
```

To do this, we first need a method that produce the final html code and add it to the template context so we can invoke it:

```python
class ImgExtension(Extension):
    base_path = 'https://mydomain.tld/myimages'

    def gen_img_string(self, name):
        return '<img src="{}" />'.format(
            '/'.join([self.base_path, name])
        )
    
    def context(self, context):
        context['_img_lexer_'] = self.gen_img_string
```

then we should write a lexer that converts the *img* notation to a call to our method and add it as a *python node* to the template tree:

```python
from renoir import Lexer

class ImgLexer(Lexer):
    def process(self, ctx, value):
        ctx.python_node(f'_img_lexer_("{value}")'))
```

The above code tells the template parser to add a python node to the current template tree, so that the `_img_lexer_` method will be invoked. The `ctx` object is responsible to handle the injection of the node in the current level of the template tree.

The last thing we need to do is to register the lexer, so the final code will look like this:

```python
from renoir import Extension, Lexer

class ImgLexer(Lexer):
    def process(self, ctx, value):
        ctx.python_node(f'_img_lexer_("{value}")'))

class ImgExtension(Extension):
    lexers = {'img': ImgLexer}
    base_path = 'https://mydomain.tld/myimages'

    def gen_img_string(self, name):
        return '<img src="{}" />'.format(
            '/'.join([self.base_path, name])
        )
    
    def context(self, context):
        context['_img_lexer_'] = self.gen_img_string
```
