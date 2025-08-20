# py-sri

py-sri is a Python module to generate [Subresource Integrity](https://developer.mozilla.org/en-US/docs/Web/Security/Subresource_Integrity) hashes on the fly. It supports Python 3.10+, including [free threading](https://py-free-threading.github.io/), and has **zero dependencies**

## Quickstart

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install py-sri.

```bash
pip install py_sri
```

Then import, setup and hash!

```python
from py_sri import SRI

# Creating an instance, providing your site's domain name and some config
sri = SRI('https://example.com', static={'directory': 'static', 'url_path': '/static'})

@sri.html_uses_sri('/')
def index() -> str:
    return '''
		...
        <link rel="stylesheet" href="static/main.css" integrity></link>
		...
	'''
# -> ...
#    <link rel="stylesheet" href="static/main.css" integrity="sha384-HASH"></link>
#    ...

sri.hash_html('/', '<script src="/static/main.js" integrity></script>')
# -> <script src="/static/main.js" integrity="sha384-HASH"></script>
```

## Usage

#### py_sri.SRI(*domain*, \*, *static*=None, *hash_alg*='sha384', *in_dev*=False)
Creates the main instance for generating hashes

domain: The domain for the site py-sri is being used for

static: An optional dictionary with a directory for static content to be found from and a url_path that refers to the path in the URL where static content is loaded from

hash_alg: The hashing algorithm to use, out of 'sha256', 'sha384' and 'sha512'

in_dev: Whether this is a development site, which will create new hashes for each request if True

#### py_sri.SRI.domain
Read only. The domain of the site

#### py_sri.SRI.hash_alg
Read only. The hashing algorithm chosen

#### py_sri.SRI.in_dev
Read only. Whether the site is in development or production

#### py_sri.SRI.clear_cache()
Clear the instance's caches

#### @py_sri.SRI.html_uses_sri(*route*, *clear*=None)
Wrapper around py_sri.SRI.hash_html() to simplify using py_sri

route: The URL path that this function responds to, like "/" or "/index.html"

clear: Whether to run py_sri.SRI.clear_cache() after finishing. By default, this inherits the value of py_sri.SRI.in_dev

#### py_sri.SRI.hash_html(*route*, *html*, *clear*=None) -> str
Parses and returns some HTML, adding in a SRI hash where an ```integrity``` attribute is found. If an error occurs, this function will remove the ```integrity``` attribute and put the error message in ```data-sri-error``` instead

Will not add SRI hashes to absolute URLs, and is unlikely to ever do

route: The URL path that the calling function responds to, like "/" or "/index.html"

html: The html document or fragment to add SRI hashes to

clear: Whether to run py_sri.SRI.clear_cache() after finishing. By default, this inherits the value of py_sri.SRI.in_dev

#### py_sri.SRI.hash_file_path(*path*, *clear*=None) -> str
Creates a SRI hash for the file at ```path```, else returns an error message **but does not raise an Exception for most failures**.

path: A path-like object to the file to hash

clear: Whether to run py_sri.SRI.clear_cache() after finishing. By default, this inherits the value of py_sri.SRI.in_dev

#### py_sri.SRI.hash_file_object(*file*, *clear*=None) -> str
Creates a SRI hash for the file object passed in the ```file``` argument. This file must be created in binary/buffered mode, ie ```open(path, "rb")```. Attempts to do so otherwise will raise exceptions. In Python 3.10, this is just a wrapper around py_sri.SRI.hash_data(). Will return a hash or an error like py_sri.SRI.hash_file_path()

file: A file-like object for hashing

clear: Whether to run py_sri.SRI.clear_cache() after finishing. By default, this inherits the value of py_sri.SRI.in_dev

#### py_sri.SRI.hash_url(*url*, \**args*, *clear*=None, \*\**kwargs*) -> str
**Not Implemented Yet**. Create a SRI hash for the given URL. **Not reccomended for absolute URLs outside of your control**. Errors returned instead of raised

url: The URL of the resource to hash

\*args: Various positional arguments to pass to requests.get()

clear: Whether to run py_sri.SRI.clear_cache() after finishing. By default, this inherits the value of py_sri.SRI.in_dev

\*\*kwargs: Various keyword arguements to pass to requests.get()

#### py_sri.SRI.hash_data(*data*) -> str
Creates a SRI hash for the data in ```data```

data: A bytes-like object containing the data to hash. If attempting to give a string or textual data that is not already bytes-like, use methods like [```str.encode```](https://docs.python.org/3/library/stdtypes.html#str.encode)

## Contributing

Pull requests are welcome. For major changes, please open an issue first
to discuss what you would like to change.

Please make sure to update tests as appropriate.

## License

[MIT](https://choosealicense.com/licenses/mit/)
